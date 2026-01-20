"""
Configuration management for adversarial fact checker
Centralizes thresholds, limits, and environment-specific settings
"""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class ValidationConfig:
    """Configuration for validation thresholds and behavior"""
    
    # Confidence thresholds (security-focused - higher bar)
    CONFIDENCE_PUBLISH: float = 85.0  # High confidence required for auto-publish
    CONFIDENCE_REVIEW: float = 75.0   # Medium confidence triggers manual review (below this = reject)
    
    # API behavior
    MAX_RETRIES: int = 3
    RETRY_MIN_WAIT: int = 1  # seconds
    RETRY_MAX_WAIT: int = 10  # seconds
    TIMEOUT: float = 30.0  # seconds
    
    # Cost limits
    MAX_DAILY_COST_USD: float = 100.0
    MAX_COST_PER_VALIDATION_USD: float = 0.50
    
    # Token limits
    MAX_INPUT_TOKENS: int = 4000
    MAX_OUTPUT_TOKENS: int = 1000
    
    # Rate limiting
    MAX_REQUESTS_PER_MINUTE: int = 50
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def from_env(cls, env: str = "production") -> "ValidationConfig":
        """
        Load configuration from environment
        
        Args:
            env: Environment name (development, staging, production)
        """
        config = cls()
        
        if env == "development":
            config.MAX_RETRIES = 2
            config.TIMEOUT = 60.0
            config.LOG_LEVEL = "DEBUG"
            config.MAX_DAILY_COST_USD = 10.0
        elif env == "staging":
            config.MAX_RETRIES = 3
            config.TIMEOUT = 30.0
            config.LOG_LEVEL = "INFO"
            config.MAX_DAILY_COST_USD = 50.0
        elif env == "production":
            config.MAX_RETRIES = 3
            config.TIMEOUT = 30.0
            config.LOG_LEVEL = "WARNING"
            config.MAX_DAILY_COST_USD = 100.0
        
        # Allow environment variable overrides
        config._apply_env_overrides()
        
        return config
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        if val := os.getenv("FACT_CHECKER_CONFIDENCE_PUBLISH"):
            self.CONFIDENCE_PUBLISH = float(val)
        if val := os.getenv("FACT_CHECKER_CONFIDENCE_REVIEW"):
            self.CONFIDENCE_REVIEW = float(val)
        if val := os.getenv("FACT_CHECKER_MAX_RETRIES"):
            self.MAX_RETRIES = int(val)
        if val := os.getenv("FACT_CHECKER_TIMEOUT"):
            self.TIMEOUT = float(val)
        if val := os.getenv("FACT_CHECKER_MAX_DAILY_COST"):
            self.MAX_DAILY_COST_USD = float(val)


@dataclass
class LLMProviderConfig:
    """Configuration for LLM provider"""
    
    provider_name: str
    model: str
    api_key: Optional[str] = None
    
    # Pricing (per 1K tokens)
    input_cost_per_1k: float = 0.01
    output_cost_per_1k: float = 0.03
    
    # Provider-specific settings
    temperature: float = 0.3
    max_tokens: int = 1000
    
    @classmethod
    def openai_gpt4(cls, api_key: Optional[str] = None) -> "LLMProviderConfig":
        """OpenAI GPT-4 configuration"""
        return cls(
            provider_name="openai",
            model="gpt-4",
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            input_cost_per_1k=0.01,
            output_cost_per_1k=0.03,
            temperature=0.3,
            max_tokens=1000
        )
    
    @classmethod
    def openai_gpt4_turbo(cls, api_key: Optional[str] = None) -> "LLMProviderConfig":
        """OpenAI GPT-4 Turbo configuration"""
        return cls(
            provider_name="openai",
            model="gpt-4-turbo-preview",
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            input_cost_per_1k=0.01,
            output_cost_per_1k=0.03,
            temperature=0.3,
            max_tokens=1000
        )
    
    @classmethod
    def anthropic_claude(cls, api_key: Optional[str] = None) -> "LLMProviderConfig":
        """Anthropic Claude 3.5 Sonnet configuration"""
        return cls(
            provider_name="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.015,
            temperature=0.3,
            max_tokens=1000
        )
    
    @classmethod
    def google_gemini(cls, api_key: Optional[str] = None) -> "LLMProviderConfig":
        """Google Gemini 1.5 Pro configuration"""
        return cls(
            provider_name="google",
            model="gemini-1.5-pro",
            api_key=api_key or os.getenv("GOOGLE_API_KEY"),
            input_cost_per_1k=0.00125,
            output_cost_per_1k=0.005,
            temperature=0.3,
            max_tokens=1000
        )
