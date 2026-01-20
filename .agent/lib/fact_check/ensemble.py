"""
Ensemble orchestration for multi-model adversarial fact-checking
Implements consensus detection, tiered validation, and synthesis logic
"""

import asyncio
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics

import structlog

from .providers import LLMProvider, LLMProviderResponse
from .validators import ValidationResult, ValidationAction, ArticleInput, LLMResponse
from .config import ValidationConfig

logger = structlog.get_logger(__name__)


class ConsensusLevel(Enum):
    """Consensus tiers based on model agreement"""
    AUTHORITATIVE = "authoritative"  # 90-100% agreement
    HIGH = "high"                     # 70-89% agreement
    DISPUTED = "disputed"             # 40-69% agreement
    UNTRUSTED = "untrusted"           # <40% agreement


@dataclass
class EnsembleValidationResult:
    """Result from ensemble validation with consensus metrics"""
    
    # Individual model results
    model_results: List[ValidationResult]
    
    # Consensus metrics
    consensus_level: ConsensusLevel
    consensus_score: float  # 0-100
    confidence_mean: float
    confidence_std: float
    
    # Synthesized result
    synthesized_result: ValidationResult
    
    # Metadata
    models_used: List[str]
    total_cost_usd: float
    total_latency_ms: float
    
    def get_dissenting_views(self) -> Dict[str, List[str]]:
        """Get items where models disagreed"""
        dissent = {
            "regulations": [],
            "costs": [],
            "factual": []
        }
        
        # Check regulation disputes
        all_approved = set()
        all_disputed = set()
        for result in self.model_results:
            all_approved.update(result.regulations_approved)
            all_disputed.update(result.regulations_disputed)
        
        # Items that some models approved but others disputed
        dissent["regulations"] = list(all_approved.intersection(all_disputed))
        
        # Check cost validity disagreement
        cost_votes = [r.cost_estimate_valid for r in self.model_results]
        if not all(v == cost_votes[0] for v in cost_votes):
            dissent["costs"].append("Models disagree on cost validity")
        
        return dissent


class EnsembleOrchestrator:
    """
    Orchestrates multi-model validation with consensus detection
    
    Implements the Ensemble Adversarial Peer Review pattern:
    1. Independent parallel validation by multiple models
    2. Consensus detection and synthesis
    3. Tiered validation based on article value
    """
    
    def __init__(
        self,
        providers: List[LLMProvider],
        config: ValidationConfig,
        json_parser  # Reference to AdversarialFactChecker._extract_json_robust
    ):
        """
        Initialize ensemble orchestrator
        
        Args:
            providers: List of LLM provider instances
            config: Validation configuration
            json_parser: Function to parse LLM JSON responses
        """
        self.providers = providers
        self.config = config
        self.json_parser = json_parser
        
        logger.info(
            "ensemble_initialized",
            provider_count=len(providers),
            providers=[p.provider_name for p in providers]
        )
    
    async def validate_ensemble_async(
        self,
        prompt: str,
        article_input: ArticleInput,
        correlation_id: str,
        tier: str = "full"
    ) -> EnsembleValidationResult:
        """
        Execute ensemble validation asynchronously
        
        Args:
            prompt: Adversarial prompt
            article_input: Original article input
            correlation_id: Request correlation ID
            tier: Validation tier ('spot', 'standard', 'full')
            
        Returns:
            EnsembleValidationResult with consensus metrics
        """
        # Determine which providers to use based on tier
        active_providers = self._select_providers_by_tier(tier)
        
        logger.info(
            "ensemble_validation_started",
            correlation_id=correlation_id,
            tier=tier,
            provider_count=len(active_providers)
        )
        
        # Execute validations in parallel
        tasks = [
            self._validate_with_provider(
                provider=provider,
                prompt=prompt,
                correlation_id=correlation_id
            )
            for provider in active_providers
        ]
        
        # Gather results (capture exceptions)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out failed validations
        successful_results: List[Tuple[LLMProviderResponse, ValidationResult]] = []
        failed_providers: List[str] = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_providers.append(active_providers[i].provider_name)
                logger.error(
                    "provider_validation_failed",
                    correlation_id=correlation_id,
                    provider=active_providers[i].provider_name,
                    error=str(result)
                )
            else:
                successful_results.append(result)
        
        if not successful_results:
            raise ValueError("All ensemble validations failed")
        
        # Extract ValidationResults
        validation_results = [vr for _, vr in successful_results]
        
        # Calculate consensus metrics
        consensus_score = self._calculate_consensus(validation_results)
        consensus_level = self._determine_consensus_level(consensus_score)
        
        # Synthesize final result
        synthesized = self._synthesize_result(
            validation_results,
            article_input.proposed_regulations,
            correlation_id
        )
        
        # Calculate stats
        confidences = [r.confidence for r in validation_results]
        confidence_mean = statistics.mean(confidences)
        confidence_std = statistics.stdev(confidences) if len(confidences) > 1 else 0.0
        
        total_cost = sum(
            (r.prompt_tokens * 0.01 + r.response_tokens * 0.03) / 1000
            for r in validation_results
        )
        
        total_latency = sum(resp.latency_ms for resp, _ in successful_results)
        
        logger.info(
            "ensemble_validation_complete",
            correlation_id=correlation_id,
            consensus_level=consensus_level.value,
            consensus_score=consensus_score,
            confidence_mean=confidence_mean,
            total_cost_usd=total_cost
        )
        
        return EnsembleValidationResult(
            model_results=validation_results,
            consensus_level=consensus_level,
            consensus_score=consensus_score,
            confidence_mean=confidence_mean,
            confidence_std=confidence_std,
            synthesized_result=synthesized,
            models_used=[p.provider_name for p in active_providers if p.provider_name not in failed_providers],
            total_cost_usd=total_cost,
            total_latency_ms=total_latency
        )
    
    def _select_providers_by_tier(self, tier: str) -> List[LLMProvider]:
        """Select providers based on validation tier"""
        if tier == "spot":
            # Spot check: Use fastest/cheapest (Gemini)
            return [p for p in self.providers if p.provider_name == "google"][:1]
        elif tier == "standard":
            # Standard: Use 2 models (GPT-4 + Claude)
            selected = []
            for name in ["openai", "anthropic"]:
                selected.extend([p for p in self.providers if p.provider_name == name][:1])
            return selected
        else:  # full
            # Full ensemble: All 3 models
            return self.providers
    
    async def _validate_with_provider(
        self,
        provider: LLMProvider,
        prompt: str,
        correlation_id: str
    ) -> Tuple[LLMProviderResponse, ValidationResult]:
        """Execute validation with a single provider"""
        
        # Call provider
        response = await provider.validate_async(
            prompt=prompt,
            temperature=self.config.CONFIDENCE_PUBLISH / 100,  # Use config temp
            max_tokens=self.config.MAX_OUTPUT_TOKENS,
            timeout=self.config.TIMEOUT
        )
        
        # Parse response
        json_data = self.json_parser(response.raw_content)
        llm_data = LLMResponse(**json_data)
        
        # Determine action
        confidence = llm_data.confidence
        if confidence >= self.config.CONFIDENCE_PUBLISH:
            action = ValidationAction.PUBLISH
        elif confidence >= self.config.CONFIDENCE_REVIEW:
            action = ValidationAction.REVIEW
        else:
            action = ValidationAction.REJECT
        
        # Create ValidationResult
        validation_result = ValidationResult(
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
            llm_provider=provider.model_name,
            prompt_tokens=response.prompt_tokens,
            response_tokens=response.response_tokens,
            correlation_id=correlation_id
        )
        
        return (response, validation_result)
    
    def _calculate_consensus(self, results: List[ValidationResult]) -> float:
        """
        Calculate consensus score (0-100) based on model agreement
        
        Factors:
        - Confidence score variance
        - Regulation overlap
        - Cost validity agreement
        - Action agreement
        - Factual error penalties
        """
        if len(results) == 1:
            return results[0].confidence
        
        # 1. Confidence variance (lower variance = higher consensus)
        confidences = [r.confidence for r in results]
        confidence_var = statistics.variance(confidences)
        confidence_consensus = max(0, 100 - confidence_var)  # High variance reduces score
        
        # 2. Regulation overlap (Jaccard similarity)
        all_approved_sets = [set(r.regulations_approved) for r in results]
        if all_approved_sets:
            intersection = set.intersection(*all_approved_sets)
            union = set.union(*all_approved_sets)
            regulation_overlap = (len(intersection) / len(union) * 100) if union else 100
        else:
            regulation_overlap = 100
        
        # 3. Cost validity agreement
        cost_votes = [r.cost_estimate_valid for r in results]
        cost_agreement = (sum(cost_votes) / len(cost_votes)) * 100

        # 4. Action agreement
        actions = [r.recommended_action.value for r in results]
        action_agreement = (max(actions.count(a) for a in set(actions)) / len(actions)) * 100

        # 5. Factual error penalty (more errors -> lower consensus)
        factual_errors = set()
        for r in results:
            factual_errors.update(r.factual_errors)
        factual_penalty = min(30, len(factual_errors) * 5)
        
        # Weighted average
        consensus_score = (
            confidence_consensus * 0.3 +
            regulation_overlap * 0.3 +
            cost_agreement * 0.2 +
            action_agreement * 0.2
        )
        consensus_score = max(0, consensus_score - factual_penalty)
        
        return round(consensus_score, 2)
    
    def _determine_consensus_level(self, consensus_score: float) -> ConsensusLevel:
        """Map consensus score to tier"""
        if consensus_score >= 90:
            return ConsensusLevel.AUTHORITATIVE
        elif consensus_score >= 70:
            return ConsensusLevel.HIGH
        elif consensus_score >= 40:
            return ConsensusLevel.DISPUTED
        else:
            return ConsensusLevel.UNTRUSTED
    
    def _synthesize_result(
        self,
        results: List[ValidationResult],
        original_regulations: List[str],
        correlation_id: str
    ) -> ValidationResult:
        """
        Synthesize consensus result from multiple model outputs
        
        Strategy:
        - Approved regulations: Union of all approved (at least one model)
        - Disputed: Items that some approved, some disputed
        - Missing: Intersection of missing (all models suggest)
        - Confidence: Mean of all confidences
        - Action: Based on synthesized confidence
        """
        
        # Union of approved regulations
        approved_union = set()
        for r in results:
            approved_union.update(r.regulations_approved)
        
        # Union of missing regulations (conservative)
        missing_union = set()
        for r in results:
            missing_union.update(r.regulations_missing)
        
        # Items disputed by any model
        disputed_union = set()
        for r in results:
            disputed_union.update(r.regulations_disputed)
        
        # Factual errors: Union (conservative approach)
        factual_errors_union = set()
        for r in results:
            factual_errors_union.update(r.factual_errors)
        factual_warnings_union = set()
        for r in results:
            factual_warnings_union.update(r.factual_warnings)
        
        # Cost validity: Majority vote
        cost_votes = [r.cost_estimate_valid for r in results]
        cost_valid = sum(cost_votes) > len(cost_votes) / 2
        
        # Combine cost feedback
        cost_feedback = " | ".join([r.cost_feedback for r in results])
        
        # Mean confidence
        mean_confidence = statistics.mean([r.confidence for r in results])
        
        # Synthesized action
        if mean_confidence >= self.config.CONFIDENCE_PUBLISH:
            action = ValidationAction.PUBLISH
        elif mean_confidence >= self.config.CONFIDENCE_REVIEW:
            action = ValidationAction.REVIEW
        else:
            action = ValidationAction.REJECT
        
        # Synthesized critique
        critique = f"Ensemble consensus ({len(results)} models): " + "; ".join([
            f"{r.llm_provider} ({r.confidence}%): {r.critique[:100]}"
            for r in results
        ])
        
        # Total tokens
        total_prompt_tokens = sum(r.prompt_tokens for r in results)
        total_response_tokens = sum(r.response_tokens for r in results)
        
        return ValidationResult(
            regulations_approved=list(approved_union),
            regulations_disputed=list(disputed_union),
            regulations_missing=list(missing_union),
            factual_errors=list(factual_errors_union),
            factual_warnings=list(factual_warnings_union),
            cost_estimate_valid=cost_valid,
            cost_feedback=cost_feedback,
            confidence=round(mean_confidence, 2),
            critique=critique,
            recommended_action=action,
            llm_provider=f"Ensemble({len(results)} models)",
            prompt_tokens=total_prompt_tokens,
            response_tokens=total_response_tokens,
            correlation_id=correlation_id
        )
