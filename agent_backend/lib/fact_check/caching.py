"""
Caching and rate limiting utilities for production deployment
Reduces API costs and prevents rate limit errors
"""

import hashlib
import json
import time
from typing import Optional, Dict
from dataclasses import dataclass, asdict
import asyncio
from collections import deque

import structlog

from .validators import ValidationResult

logger = structlog.get_logger(__name__)


# ============================================================================
# CACHING LAYER
# ============================================================================

@dataclass
class CachedValidation:
    """Cached validation result with metadata"""
    result: ValidationResult
    cached_at: float
    ttl_seconds: int
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return (time.time() - self.cached_at) > self.ttl_seconds


class ValidationCache:
    """
    In-memory cache for validation results
    
    In production, replace with Redis for distributed caching
    """
    
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        """
        Initialize cache
        
        Args:
            ttl_seconds: Time-to-live for cache entries (default: 1 hour)
            max_size: Maximum cache size (LRU eviction)
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, CachedValidation] = {}
        self._access_order: deque = deque()  # For LRU
        
        logger.info("cache_initialized", ttl_seconds=ttl_seconds, max_size=max_size)
    
    def _generate_cache_key(
        self,
        article_title: str,
        article_summary: str,
        proposed_regulations: list,
        proposed_costs: str
    ) -> str:
        """Generate cache key from article content"""
        # Create deterministic hash of article content
        content = json.dumps({
            "title": article_title,
            "summary": article_summary,
            "regulations": sorted(proposed_regulations),  # Sort for consistency
            "costs": proposed_costs
        }, sort_keys=True)
        
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(
        self,
        article_title: str,
        article_summary: str,
        proposed_regulations: list,
        proposed_costs: str
    ) -> Optional[ValidationResult]:
        """
        Get cached validation result if exists and not expired
        
        Returns:
            ValidationResult if cache hit, None otherwise
        """
        cache_key = self._generate_cache_key(
            article_title, article_summary, proposed_regulations, proposed_costs
        )
        
        if cache_key not in self._cache:
            logger.debug("cache_miss", cache_key=cache_key[:16])
            return None
        
        cached = self._cache[cache_key]
        
        # Check expiration
        if cached.is_expired():
            logger.debug("cache_expired", cache_key=cache_key[:16])
            del self._cache[cache_key]
            self._access_order.remove(cache_key)
            return None
        
        # Update access order (LRU)
        self._access_order.remove(cache_key)
        self._access_order.append(cache_key)
        
        logger.info("cache_hit", cache_key=cache_key[:16])
        return cached.result
    
    def set(
        self,
        article_title: str,
        article_summary: str,
        proposed_regulations: list,
        proposed_costs: str,
        result: ValidationResult
    ):
        """Cache validation result"""
        cache_key = self._generate_cache_key(
            article_title, article_summary, proposed_regulations, proposed_costs
        )
        
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size:
            oldest_key = self._access_order.popleft()
            del self._cache[oldest_key]
            logger.debug("cache_eviction", evicted_key=oldest_key[:16])
        
        # Store
        self._cache[cache_key] = CachedValidation(
            result=result,
            cached_at=time.time(),
            ttl_seconds=self.ttl_seconds
        )
        self._access_order.append(cache_key)
        
        logger.debug("cache_set", cache_key=cache_key[:16])
    
    def clear(self):
        """Clear entire cache"""
        self._cache.clear()
        self._access_order.clear()
        logger.info("cache_cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds
        }


# ============================================================================
# RATE LIMITING
# ============================================================================

class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for API requests
    
    Prevents 429 rate limit errors from LLM providers
    """
    
    def __init__(
        self,
        max_requests_per_minute: int = 50,
        burst_size: int = 10
    ):
        """
        Initialize rate limiter
        
        Args:
            max_requests_per_minute: Sustained request rate
            burst_size: Maximum burst capacity
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.burst_size = burst_size
        
        # Token bucket state
        self._tokens = float(burst_size)
        self._last_refill = time.time()
        self._lock = asyncio.Lock()
        
        # Metrics
        self._total_requests = 0
        self._total_waits = 0
        
        logger.info(
            "rate_limiter_initialized",
            max_rpm=max_requests_per_minute,
            burst_size=burst_size
        )
    
    async def acquire(self):
        """
        Acquire permission to make a request
        
        Blocks until a token is available
        """
        async with self._lock:
            # Refill tokens based on elapsed time
            now = time.time()
            elapsed = now - self._last_refill
            refill_amount = elapsed * (self.max_requests_per_minute / 60.0)
            self._tokens = min(self.burst_size, self._tokens + refill_amount)
            self._last_refill = now
            
            # Wait if no tokens available
            if self._tokens < 1:
                wait_time = (1 - self._tokens) / (self.max_requests_per_minute / 60.0)
                logger.warning(
                    "rate_limit_wait",
                    wait_seconds=round(wait_time, 2),
                    tokens=self._tokens
                )
                await asyncio.sleep(wait_time)
                self._tokens = 1
                self._total_waits += 1
            
            # Consume token
            self._tokens -= 1
            self._total_requests += 1
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        return {
            "total_requests": self._total_requests,
            "total_waits": self._total_waits,
            "current_tokens": round(self._tokens, 2),
            "max_rpm": self.max_requests_per_minute
        }


# ============================================================================
# CIRCUIT BREAKER
# ============================================================================

class CircuitState:
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """
    Circuit breaker pattern for LLM provider resilience
    
    Prevents cascading failures when a provider is down
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            success_threshold: Successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        # State
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0
        self._lock = asyncio.Lock()
        
        logger.info(
            "circuit_breaker_initialized",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
    
    async def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        async with self._lock:
            # Check circuit state
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout elapsed
                if time.time() - self._last_failure_time > self.recovery_timeout:
                    logger.info("circuit_half_open", trying_recovery=True)
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                else:
                    raise Exception("Circuit breaker OPEN - service unavailable")
        
        # Execute function
        try:
            result = await func(*args, **kwargs)
            
            async with self._lock:
                # Success
                if self._state == CircuitState.HALF_OPEN:
                    self._success_count += 1
                    if self._success_count >= self.success_threshold:
                        logger.info("circuit_closed", recovered=True)
                        self._state = CircuitState.CLOSED
                        self._failure_count = 0
                
                return result
                
        except Exception as e:
            async with self._lock:
                # Failure
                self._failure_count += 1
                self._last_failure_time = time.time()
                
                if self._failure_count >= self.failure_threshold:
                    logger.error(
                        "circuit_opened",
                        failure_count=self._failure_count,
                        error=str(e)
                    )
                    self._state = CircuitState.OPEN
                
                raise
    
    def get_state(self) -> str:
        """Get current circuit state"""
        return self._state
    
    def reset(self):
        """Manually reset circuit breaker"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        logger.info("circuit_reset")
