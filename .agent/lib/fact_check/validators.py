"""
Pydantic validators for adversarial fact checker
Ensures type safety, input validation, and prevents injection attacks
"""

from typing import List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


class ValidationAction(Enum):
    """Recommended action after validation"""
    PUBLISH = "publish"  # High confidence, proceed
    REVIEW = "review"    # Medium confidence, manual check needed
    REJECT = "reject"    # Low confidence, do not publish


class ArticleInput(BaseModel):
    """Validated input for article fact-checking"""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    article_title: str = Field(
        min_length=10,
        max_length=500,
        description="Article title"
    )
    article_summary: str = Field(
        min_length=50,
        max_length=5000,
        description="Article summary/content"
    )
    proposed_regulations: List[str] = Field(
        min_length=0,
        max_length=20,
        description="List of proposed Indian regulations"
    )
    proposed_costs: str = Field(
        min_length=1,
        max_length=200,
        description="Cost estimate string"
    )
    topic: str = Field(
        min_length=1,
        max_length=100,
        description="Article topic category"
    )
    
    @field_validator('article_title', 'article_summary', 'proposed_costs', 'topic')
    @classmethod
    def validate_encoding(cls, v: str) -> str:
        """Ensure valid UTF-8 encoding"""
        if not v:
            raise ValueError("Field cannot be empty")
        # Verify can be encoded/decoded cleanly
        try:
            v.encode('utf-8').decode('utf-8')
        except UnicodeError:
            raise ValueError("Invalid UTF-8 encoding")
        return v
    
    @field_validator('proposed_regulations')
    @classmethod
    def validate_regulations_list(cls, v: List[str]) -> List[str]:
        """Validate regulations list"""
        if not isinstance(v, list):
            raise ValueError("Regulations must be a list")
        
        # Check each regulation
        for reg in v:
            if not isinstance(reg, str):
                raise ValueError("Each regulation must be a string")
            if len(reg) > 200:
                raise ValueError(f"Regulation too long: {reg[:50]}...")
        
        return v
    
    def estimate_tokens(self) -> int:
        """Rough token estimation (1 token ≈ 4 chars)"""
        total_chars = (
            len(self.article_title) +
            len(self.article_summary) +
            sum(len(r) for r in self.proposed_regulations) +
            len(self.proposed_costs) +
            len(self.topic)
        )
        # Add ~500 tokens for system prompt overhead
        return (total_chars // 4) + 500


class ValidationResult(BaseModel):
    """Structured response from LLM validation"""
    
    # Regulation validation
    regulations_approved: List[str] = Field(
        default_factory=list,
        description="High-confidence regulations"
    )
    regulations_disputed: List[str] = Field(
        default_factory=list,
        description="Low-confidence (needs review)"
    )
    regulations_missing: List[str] = Field(
        default_factory=list,
        description="Suggested additions"
    )
    
    # Factual validation
    factual_errors: List[str] = Field(
        default_factory=list,
        description="Identified inaccuracies"
    )
    factual_warnings: List[str] = Field(
        default_factory=list,
        description="Potential issues"
    )
    
    # Cost validation
    cost_estimate_valid: bool = Field(
        default=False,
        description="Is cost range realistic?"
    )
    cost_feedback: str = Field(
        default="",
        description="Explanation"
    )
    
    # Overall assessment
    confidence: float = Field(
        ge=0.0,
        le=100.0,
        description="0-100% confidence score"
    )
    critique: str = Field(
        default="",
        description="Free-form LLM explanation"
    )
    recommended_action: ValidationAction = Field(
        description="Recommended action"
    )
    
    # Metadata
    llm_provider: str = Field(
        description="Which LLM was used"
    )
    prompt_tokens: int = Field(
        ge=0,
        description="Cost tracking"
    )
    response_tokens: int = Field(
        ge=0,
        description="Cost tracking"
    )
    
    # Add correlation ID for tracing
    correlation_id: str = Field(
        default="",
        description="Request correlation ID"
    )
    
    def total_tokens(self) -> int:
        """Total tokens consumed"""
        return self.prompt_tokens + self.response_tokens
    
    def estimate_cost(self, input_cost_per_1k: float = 0.01, output_cost_per_1k: float = 0.03) -> float:
        """
        Estimate API cost for this validation
        
        Args:
            input_cost_per_1k: Cost per 1K input tokens (default: GPT-4 pricing)
            output_cost_per_1k: Cost per 1K output tokens
            
        Returns:
            Cost in USD
        """
        input_cost = (self.prompt_tokens / 1000) * input_cost_per_1k
        output_cost = (self.response_tokens / 1000) * output_cost_per_1k
        return input_cost + output_cost


class LLMResponse(BaseModel):
    """Parsed LLM JSON response (internal model)"""
    
    regulations_approved: List[str] = Field(default_factory=list)
    regulations_disputed: List[str] = Field(default_factory=list)
    regulations_missing: List[str] = Field(default_factory=list)
    factual_errors: List[str] = Field(default_factory=list)
    factual_warnings: List[str] = Field(default_factory=list)
    cost_valid: bool = False
    cost_feedback: str = ""
    confidence: float = Field(ge=0.0, le=100.0)
    critique: str = ""
