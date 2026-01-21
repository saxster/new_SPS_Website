"""
ADVERSARIAL FACT CHECKER - Production-Hardened V2
Multi-LLM validation with adversarial prompting, retry logic, and robust error handling

Key improvements from MVP:
- Input validation with Pydantic schemas
- Retry logic with exponential backoff
- Timeout handling
- Robust JSON parsing with fallback strategies
- Structured logging with correlation IDs
- Cost tracking and budget enforcement
- Provider abstraction for ensemble support
"""

import os
import json
import logging
import uuid
import hashlib
import re
from typing import Dict, List, Optional
from datetime import datetime

import structlog
from openai import OpenAI
from pydantic import ValidationError as PydanticValidationError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from dotenv import load_dotenv

from .validators import ArticleInput, ValidationResult, ValidationAction, LLMResponse
from .config import ValidationConfig, LLMProviderConfig

load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger(__name__)


class ValidationError(Exception):
    """Base exception for validation errors"""
    pass


class BudgetExceededError(ValidationError):
    """Raised when API budget is exceeded"""
    pass


class JSONParsingError(ValidationError):
    """Raised when LLM response cannot be parsed"""
    pass


class AdversarialFactChecker:
    """
    Production-grade fact checker using adversarial prompting
    
    Features:
    - Automatic retry with exponential backoff
    - Timeout handling
    - Input validation
    - Robust JSON parsing
    - Cost tracking and budget enforcement
    - Structured logging with correlation IDs
    """
    
    def __init__(
        self,
        config: Optional[ValidationConfig] = None,
        provider_config: Optional[LLMProviderConfig] = None,
        daily_budget_usd: Optional[float] = None
    ):
        """
        Initialize fact checker
        
        Args:
            config: Validation configuration (uses defaults if not provided)
            provider_config: LLM provider configuration (defaults to GPT-4)
            daily_budget_usd: Daily API budget limit in USD
        """
        self.config = config or ValidationConfig.from_env(
            env=os.getenv("ENVIRONMENT", "production")
        )
        self.provider_config = provider_config or LLMProviderConfig.openai_gpt4()
        self.daily_budget_usd = daily_budget_usd or self.config.MAX_DAILY_COST_USD
        
        if not self.provider_config.api_key:
            raise ValueError(
                f"{self.provider_config.provider_name.upper()} API key required. "
                f"Set {self.provider_config.provider_name.upper()}_API_KEY environment variable."
            )
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.provider_config.api_key)
        
        # Track daily spend (in production, use Redis/DB)
        self._daily_spend = 0.0
        self._validation_count = 0
        
        logger.info(
            "fact_checker_initialized",
            provider=self.provider_config.provider_name,
            model=self.provider_config.model,
            daily_budget=self.daily_budget_usd
        )
    
    def validate_article(
        self,
        article_title: str,
        article_summary: str,
        proposed_regulations: List[str],
        proposed_costs: str,
        topic: str
    ) -> ValidationResult:
        """
        Validate an article using adversarial prompting
        
        Args:
            article_title: Original article title
            article_summary: Article summary/content
            proposed_regulations: List of Indian regulations we think apply
            proposed_costs: Cost estimate string (e.g., "₹5-50L")
            topic: Article topic category
        
        Returns:
            ValidationResult with LLM's critical assessment
            
        Raises:
            ValidationError: If input validation fails
            BudgetExceededError: If daily budget is exceeded
        """
        # Generate correlation ID for request tracing
        correlation_id = str(uuid.uuid4())
        
        logger.info(
            "validation_started",
            correlation_id=correlation_id,
            title=article_title[:50] + "..." if len(article_title) > 50 else article_title
        )
        
        try:
            # 1. Validate input using Pydantic
            article_input = ArticleInput(
                article_title=article_title,
                article_summary=article_summary,
                proposed_regulations=proposed_regulations,
                proposed_costs=proposed_costs,
                topic=topic
            )
            
            # 2. Check token limits
            estimated_tokens = article_input.estimate_tokens()
            if estimated_tokens > self.config.MAX_INPUT_TOKENS:
                raise ValidationError(
                    f"Input too large: {estimated_tokens} tokens exceeds limit of {self.config.MAX_INPUT_TOKENS}"
                )
            
            # 3. Check daily budget
            self._check_budget()
            
            # 4. Build adversarial prompt
            prompt = self._build_adversarial_prompt(article_input)
            
            # 5. Call LLM with retry logic
            llm_response, prompt_tokens, response_tokens = self._call_llm_with_retry(
                prompt=prompt,
                correlation_id=correlation_id
            )
            
            # 6. Parse response into ValidationResult
            validation = self._parse_llm_response(
                llm_response=llm_response,
                original_regulations=proposed_regulations,
                prompt_tokens=prompt_tokens,
                response_tokens=response_tokens,
                correlation_id=correlation_id
            )
            
            # 7. Update cost tracking
            cost = validation.estimate_cost(
                input_cost_per_1k=self.provider_config.input_cost_per_1k,
                output_cost_per_1k=self.provider_config.output_cost_per_1k
            )
            self._daily_spend += cost
            self._validation_count += 1
            
            logger.info(
                "validation_complete",
                correlation_id=correlation_id,
                confidence=validation.confidence,
                action=validation.recommended_action.value,
                cost_usd=cost,
                daily_spend=self._daily_spend,
                validation_count=self._validation_count
            )
            
            return validation
            
        except ValidationError as e:
            logger.error(
                "validation_error",
                correlation_id=correlation_id,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return self._create_error_result(str(e), correlation_id)
            
        except Exception as e:
            logger.error(
                "validation_failed",
                correlation_id=correlation_id,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            return self._create_error_result(f"Unexpected error: {str(e)}", correlation_id)
    
    def _check_budget(self):
        """Check if we're within daily budget"""
        if self._daily_spend >= self.daily_budget_usd:
            raise BudgetExceededError(
                f"Daily budget of ${self.daily_budget_usd} exceeded. "
                f"Current spend: ${self._daily_spend:.2f}"
            )
    
    @retry(
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def _call_llm_with_retry(
        self,
        prompt: str,
        correlation_id: str
    ) -> tuple[str, int, int]:
        """
        Call LLM API with automatic retry and timeout handling
        
        Returns:
            Tuple of (response_text, prompt_tokens, response_tokens)
        """
        try:
            response = self.client.chat.completions.create(
                model=self.provider_config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a SKEPTICAL Indian legal and security compliance expert. Your job is to FIND ERRORS, not confirm correctness. Be harsh and thorough."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.provider_config.temperature,
                max_tokens=self.provider_config.max_tokens,
                timeout=self.config.TIMEOUT
            )
            
            return (
                response.choices[0].message.content,
                response.usage.prompt_tokens,
                response.usage.completion_tokens
            )
            
        except Exception as e:
            logger.warning(
                "llm_call_failed",
                correlation_id=correlation_id,
                error=str(e)
            )
            raise
    
    def _build_adversarial_prompt(self, article: ArticleInput) -> str:
        """Build adversarial validation prompt"""
        
        regs_formatted = "\n".join([f"- {reg}" for reg in article.proposed_regulations])
        
        prompt = f"""
You are conducting a CRITICAL REVIEW of an article for the "Bloomberg of Indian Security" platform.
Your reputation depends on catching errors. Be adversarial and thorough.

ARTICLE TO REVIEW:
------------------
Title: {article.article_title}
Topic: {article.topic}
Summary: {article.article_summary}

PROPOSED INDIAN REGULATIONS:
---------------------------
{regs_formatted if regs_formatted else "(None proposed)"}

PROPOSED COST ESTIMATE (India):
-------------------------------
{article.proposed_costs}

YOUR CRITICAL ASSESSMENT:
-------------------------

Please provide a HARSH, SKEPTICAL evaluation. Answer in JSON format:

{{
  "regulations_approved": ["List regulations that ARE clearly applicable"],
  "regulations_disputed": ["List regulations that might NOT apply - explain why"],
  "regulations_missing": ["Critical regulations we MISSED - suggest additions"],
  "factual_errors": ["Any FACTUAL INACCURACIES in the article itself"],
  "factual_warnings": ["Potential issues or unverified claims"],
  "cost_valid": true/false,
  "cost_feedback": "Is the cost estimate realistic for India? Why/why not?",
  "confidence": 0-100,
  "critique": "Overall assessment - be honest about weaknesses"
}}

CRITICAL CHECKS:
1. Are regulations INCORRECTLY applied? (e.g., POCSO Act to college when it's for minors <18)
2. Are regulations MISSING? (e.g., forgot DPDP Act for data breach)
3. Are cost estimates HALLUCINATED or realistic?
4. Are factual claims VERIFIABLE?
5. Is Indian context FORCED or genuinely relevant?

BE HARSH. Find the errors. This is adversarial peer review.
"""
        return prompt
    
    def _parse_llm_response(
        self,
        llm_response: str,
        original_regulations: List[str],
        prompt_tokens: int,
        response_tokens: int,
        correlation_id: str
    ) -> ValidationResult:
        """Parse LLM JSON response into ValidationResult with robust fallback"""
        
        try:
            # Extract JSON with multiple fallback strategies
            json_data = self._extract_json_robust(llm_response)
            
            # Validate against schema
            llm_data = LLMResponse(**json_data)
            
            # Determine action based on confidence
            confidence = llm_data.confidence
            if confidence >= self.config.CONFIDENCE_PUBLISH:
                action = ValidationAction.PUBLISH
            elif confidence >= self.config.CONFIDENCE_REVIEW:
                action = ValidationAction.REVIEW
            else:
                action = ValidationAction.REJECT
            
            return ValidationResult(
                regulations_approved=llm_data.regulations_approved,
                regulations_disputed=llm_data.regulations_disputed,
                regulations_missing=llm_data.regulations_missing,
                factual_errors=llm_data.factual_errors,
                factual_warnings=llm_data.factual_warnings,
                cost_estimate_valid=llm_data.cost_valid,
                cost_feedback=llm_data.cost_feedback,
                confidence=confidence,
                critique=llm_data.critique,
                recommended_action=action,
                llm_provider=self.provider_config.model,
                prompt_tokens=prompt_tokens,
                response_tokens=response_tokens,
                correlation_id=correlation_id
            )
            
        except Exception as e:
            logger.error(
                "parse_error",
                correlation_id=correlation_id,
                error=str(e),
                response_preview=llm_response[:200]
            )
            raise JSONParsingError(f"Failed to parse LLM response: {e}")
    
    def _extract_json_robust(self, text: str) -> dict:
        """
        Extract JSON from LLM response with multiple fallback strategies
        
        Strategies:
        1. Standard markdown fence extraction (```json...```)
        2. Generic fence extraction (```...```)
        3. Regex-based {...} block extraction
        4. Attempt to repair common JSON errors
        
        Returns:
            Parsed JSON dict
            
        Raises:
            JSONParsingError if all strategies fail
        """
        strategies = [
            self._extract_from_markdown_fence,
            self._extract_from_generic_fence,
            self._extract_from_braces,
            self._extract_with_repair
        ]
        
        for i, strategy in enumerate(strategies):
            try:
                json_str = strategy(text)
                return json.loads(json_str)
            except Exception as e:
                logger.debug(
                    "extraction_strategy_failed",
                    strategy=i+1,
                    error=str(e)
                )
                continue
        
        raise JSONParsingError("All JSON extraction strategies failed")
    
    def _extract_from_markdown_fence(self, text: str) -> str:
        """Extract JSON from ```json fence"""
        if "```json" in text:
            return text.split("```json")[1].split("```")[0].strip()
        raise ValueError("No ```json fence found")
    
    def _extract_from_generic_fence(self, text: str) -> str:
        """Extract JSON from ``` fence"""
        if "```" in text:
            parts = text.split("```")
            if len(parts) >= 3:
                return parts[1].strip()
        raise ValueError("No ``` fence found")
    
    def _extract_from_braces(self, text: str) -> str:
        """Extract first {...} block using regex"""
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        raise ValueError("No {...} block found")
    
    def _extract_with_repair(self, text: str) -> str:
        """Attempt to repair common JSON errors"""
        # Try extracting with braces first
        try:
            json_str = self._extract_from_braces(text)
        except:
            json_str = text
        
        # Common repairs
        json_str = json_str.replace("'", '"')  # Single to double quotes
        json_str = json_str.replace("True", "true")  # Python bools
        json_str = json_str.replace("False", "false")
        json_str = json_str.replace("None", "null")
        
        return json_str
    
    def _create_error_result(self, error_message: str, correlation_id: str) -> ValidationResult:
        """Create a safe ValidationResult when validation fails"""
        return ValidationResult(
            regulations_approved=[],
            regulations_disputed=[],
            regulations_missing=[],
            factual_errors=[f"Validation failed: {error_message}"],
            factual_warnings=["Manual review required due to validation error"],
            cost_estimate_valid=False,
            cost_feedback="Could not validate due to error",
            confidence=0.0,
            critique=f"Validation error: {error_message}",
            recommended_action=ValidationAction.REVIEW,  # ALWAYS flag errors for manual review
            llm_provider=self.provider_config.model,
            prompt_tokens=0,
            response_tokens=0,
            correlation_id=correlation_id
        )
    
    def get_stats(self) -> dict:
        """Get current usage statistics"""
        return {
            "validations_count": self._validation_count,
            "daily_spend_usd": round(self._daily_spend, 4),
            "budget_remaining_usd": round(self.daily_budget_usd - self._daily_spend, 4),
            "budget_utilization_pct": round((self._daily_spend / self.daily_budget_usd) * 100, 2)
        }


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize fact checker with custom config
    config = ValidationConfig.from_env("development")
    checker = AdversarialFactChecker(config=config)
    
    # Example article to validate
    result = checker.validate_article(
        article_title="Punjab Govt to deploy 200 security staff in district hospitals",
        article_summary="The Punjab government has decided to deploy 200 security personnel in district hospitals across the state to ensure safety of medical staff and patients.",
        proposed_regulations=[
            "NBC 2016 Part 4 (Healthcare)",
            "Biomedical Waste Rules 2016",
            "Clinical Establishments Act"
        ],
        proposed_costs="₹5-50L depending on facility size",
        topic="healthcare_security"
    )
    
    # Display results
    print("\n" + "="*70)
    print("ADVERSARIAL FACT-CHECK RESULTS")
    print("="*70)
    print(f"\nConfidence: {result.confidence}%")
    print(f"Action: {result.recommended_action.value.upper()}")
    print(f"\nApproved Regulations ({len(result.regulations_approved)}):")
    for reg in result.regulations_approved:
        print(f"  ✓ {reg}")
    print(f"\nDisputed Regulations ({len(result.regulations_disputed)}):")
    for reg in result.regulations_disputed:
        print(f"  ⚠ {reg}")
    print(f"\nMissing Regulations ({len(result.regulations_missing)}):")
    for reg in result.regulations_missing:
        print(f"  + {reg}")
    print(f"\nFactual Errors ({len(result.factual_errors)}):")
    for error in result.factual_errors:
        print(f"  ❌ {error}")
    print(f"\nCost Validation:")
    print(f"  Valid: {result.cost_estimate_valid}")
    print(f"  Feedback: {result.cost_feedback}")
    print(f"\nCritique:")
    print(f"  {result.critique}")
    
    # Cost tracking
    cost = result.estimate_cost(
        input_cost_per_1k=checker.provider_config.input_cost_per_1k,
        output_cost_per_1k=checker.provider_config.output_cost_per_1k
    )
    print(f"\nAPI Cost: ${cost:.4f}")
    print(f"Correlation ID: {result.correlation_id}")
    
    # Stats
    stats = checker.get_stats()
    print(f"\n📊 Session Stats:")
    print(f"  Validations: {stats['validations_count']}")
    print(f"  Daily Spend: ${stats['daily_spend_usd']}")
    print(f"  Budget Remaining: ${stats['budget_remaining_usd']}")
    print(f"  Budget Used: {stats['budget_utilization_pct']}%")
    print("="*70 + "\n")
