"""
Tests for caching module.

Bug #2: Typo in CircuitBreaker.__init__ logger call
Line 284 has `failure_threshold=failure threshold` (missing underscore)
which would cause a NameError at runtime.
"""

import pytest
import ast
import os
import re


class TestCircuitBreakerLoggerTypo:
    """Test that the logger call typo is fixed."""

    def test_no_typo_in_circuit_breaker_init(self):
        """
        Verify that CircuitBreaker.__init__ doesn't have the typo
        `failure threshold` (with space instead of underscore).

        The bug: Line 284 has `failure_threshold=failure threshold`
        (space instead of underscore) which causes NameError.

        Expected fix: `failure_threshold=failure_threshold`
        """
        source_file = os.path.join(
            os.path.dirname(__file__),
            '..', 'lib', 'fact_check', 'caching.py'
        )

        with open(source_file, 'r') as f:
            source = f.read()

        # Check for the specific typo pattern
        # The bug is: failure_threshold=failure threshold
        # (note: 'failure threshold' is two words, which is a NameError)
        typo_pattern = r'failure_threshold\s*=\s*failure\s+threshold\b'
        matches = re.findall(typo_pattern, source)

        assert len(matches) == 0, (
            f"Found typo 'failure_threshold=failure threshold' in caching.py. "
            f"Should be 'failure_threshold=failure_threshold' (underscore, not space). "
            f"This would cause a NameError at runtime."
        )

    def test_logger_info_call_has_valid_syntax(self):
        """
        Verify the logger.info call in CircuitBreaker.__init__ has valid Python syntax.
        """
        source_file = os.path.join(
            os.path.dirname(__file__),
            '..', 'lib', 'fact_check', 'caching.py'
        )

        with open(source_file, 'r') as f:
            source = f.read()

        # This should not raise SyntaxError if the file is valid Python
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"caching.py has syntax error: {e}")


class TestCircuitBreakerImport:
    """Test that CircuitBreaker can be imported and instantiated."""

    def test_circuit_breaker_can_be_imported(self):
        """Verify CircuitBreaker can be imported without errors."""
        import sys
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__),
            '..', 'lib', 'fact_check'
        ))

        # This should not raise ImportError or SyntaxError
        from caching import CircuitBreaker

        assert CircuitBreaker is not None

    def test_circuit_breaker_can_be_instantiated(self):
        """
        Verify CircuitBreaker can be instantiated without NameError.

        The bug causes NameError when __init__ tries to log
        `failure_threshold=failure threshold` (two separate names).
        """
        import sys
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__),
            '..', 'lib', 'fact_check'
        ))

        from caching import CircuitBreaker

        # This should not raise NameError
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60

    def test_circuit_breaker_default_instantiation(self):
        """Verify CircuitBreaker with default values works."""
        import sys
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__),
            '..', 'lib', 'fact_check'
        ))

        from caching import CircuitBreaker

        cb = CircuitBreaker()

        assert cb.failure_threshold == 5  # default
        assert cb.recovery_timeout == 60  # default
        assert cb.success_threshold == 2  # default


class TestCircuitState:
    """Test CircuitState enum."""

    def test_circuit_states_exist(self):
        """Verify all expected circuit states are defined."""
        import sys
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__),
            '..', 'lib', 'fact_check'
        ))

        from caching import CircuitState

        assert hasattr(CircuitState, 'CLOSED')
        assert hasattr(CircuitState, 'OPEN')
        assert hasattr(CircuitState, 'HALF_OPEN')


class TestValidationCacheImport:
    """Test that ValidationCache can be imported."""

    def test_validation_cache_can_be_imported(self):
        """Verify ValidationCache can be imported."""
        import sys
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__),
            '..', 'lib', 'fact_check'
        ))

        from caching import ValidationCache

        cache = ValidationCache(ttl_seconds=3600, max_size=1000)
        assert cache.ttl_seconds == 3600
        assert cache.max_size == 1000


class TestTokenBucketRateLimiterImport:
    """Test that TokenBucketRateLimiter can be imported."""

    def test_rate_limiter_can_be_imported(self):
        """Verify TokenBucketRateLimiter can be imported."""
        import sys
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__),
            '..', 'lib', 'fact_check'
        ))

        from caching import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(
            max_requests_per_minute=50,
            burst_size=10
        )
        assert limiter.max_requests_per_minute == 50
        assert limiter.burst_size == 10
