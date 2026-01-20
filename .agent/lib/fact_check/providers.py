"""
Abstract LLM provider interface for ensemble architecture
Enables swappable providers (OpenAI, Anthropic, Google) with consistent interface
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import asyncio

from .validators import ValidationResult, LLMResponse


@dataclass
class LLMProviderResponse:
    """Standardized response from any LLM provider"""
    raw_content: str
    prompt_tokens: int
    response_tokens: int
    provider_name: str
    model_name: str
    latency_ms: float


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier (e.g., 'openai', 'anthropic', 'google')"""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier (e.g., 'gpt-4', 'claude-3-5-sonnet')"""
        pass
    
    @abstractmethod
    async def validate_async(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> LLMProviderResponse:
        """
        Execute validation request asynchronously
        
        Args:
            prompt: Full adversarial prompt
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
            timeout: Request timeout in seconds
            
        Returns:
            LLMProviderResponse with raw content and metadata
            
        Raises:
            TimeoutError: If request exceeds timeout
            Exception: For API-specific errors
        """
        pass
    
    def validate_sync(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> LLMProviderResponse:
        """Synchronous wrapper for async validate"""
        return asyncio.run(self.validate_async(prompt, temperature, max_tokens, timeout))


class OpenAIProvider(LLMProvider):
    """OpenAI GPT-4 provider implementation"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
        self._model = model
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    @property
    def model_name(self) -> str:
        return self._model
    
    async def validate_async(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> LLMProviderResponse:
        import time
        start_time = time.perf_counter()
        
        response = await self.client.chat.completions.create(
            model=self._model,
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
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        return LLMProviderResponse(
            raw_content=response.choices[0].message.content,
            prompt_tokens=response.usage.prompt_tokens,
            response_tokens=response.usage.completion_tokens,
            provider_name=self.provider_name,
            model_name=self.model_name,
            latency_ms=latency_ms
        )


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation"""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=api_key)
            self._model = model
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    @property
    def model_name(self) -> str:
        return self._model
    
    async def validate_async(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> LLMProviderResponse:
        import time
        start_time = time.perf_counter()
        
        response = await self.client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            system="You are a SKEPTICAL Indian legal and security compliance expert. Your job is to FIND ERRORS, not confirm correctness. Be harsh and thorough.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        return LLMProviderResponse(
            raw_content=response.content[0].text,
            prompt_tokens=response.usage.input_tokens,
            response_tokens=response.usage.output_tokens,
            provider_name=self.provider_name,
            model_name=self.model_name,
            latency_ms=latency_ms
        )


class GoogleGeminiProvider(LLMProvider):
    """Google Gemini provider implementation"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            self._model = model
        except ImportError:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
    
    @property
    def provider_name(self) -> str:
        return "google"
    
    @property
    def model_name(self) -> str:
        return self._model
    
    async def validate_async(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout: float
    ) -> LLMProviderResponse:
        import time
        start_time = time.perf_counter()
        
        # Gemini doesn't have native async in genai library, use asyncio.to_thread
        system_instruction = "You are a SKEPTICAL Indian legal and security compliance expert. Your job is to FIND ERRORS, not confirm correctness. Be harsh and thorough."
        full_prompt = f"{system_instruction}\n\n{prompt}"
        
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        
        response = await asyncio.to_thread(
            self.client.generate_content,
            full_prompt,
            generation_config=generation_config
        )
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Estimate token counts (Gemini doesn't always provide exact counts)
        prompt_tokens = len(full_prompt) // 4  # Rough estimate
        response_tokens = len(response.text) // 4
        
        return LLMProviderResponse(
            raw_content=response.text,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
            provider_name=self.provider_name,
            model_name=self.model_name,
            latency_ms=latency_ms
        )


class ProviderFactory:
    """Factory for creating LLM providers"""
    
    @staticmethod
    def create_provider(
        provider_name: str,
        api_key: str,
        model: Optional[str] = None
    ) -> LLMProvider:
        """
        Create LLM provider instance
        
        Args:
            provider_name: 'openai', 'anthropic', or 'google'
            api_key: API key for the provider
            model: Optional model override
            
        Returns:
            Configured LLMProvider instance
        """
        providers = {
            "openai": (OpenAIProvider, "gpt-4"),
            "anthropic": (AnthropicProvider, "claude-3-5-sonnet-20241022"),
            "google": (GoogleGeminiProvider, "gemini-1.5-pro")
        }
        
        if provider_name not in providers:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Valid providers: {list(providers.keys())}"
            )
        
        provider_class, default_model = providers[provider_name]
        return provider_class(api_key=api_key, model=model or default_model)
