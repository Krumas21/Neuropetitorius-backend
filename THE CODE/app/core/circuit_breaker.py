"""Circuit breaker for external API calls."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 10
    recovery_timeout: int = 60
    half_open_max_calls: int = 3
    excluded_exceptions: tuple = ()


@dataclass
class CircuitBreaker:
    """Circuit breaker for external API calls."""

    name: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0, init=False)
    _half_open_calls: int = field(default=0, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    @property
    def state(self) -> CircuitState:
        now = time.time()
        if self._state == CircuitState.OPEN:
            if now - self._last_failure_time >= self.config.recovery_timeout:
                logger.info(f"Circuit {self.name}: transitioning to HALF_OPEN")
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            current_state = self.state

            if current_state == CircuitState.OPEN:
                raise CircuitOpenError(
                    f"Circuit {self.name} is OPEN. Retry after {self.config.recovery_timeout}s"
                )

            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitOpenError(
                        f"Circuit {self.name} is in HALF_OPEN, max calls reached"
                    )
                self._half_open_calls += 1

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            if self._is_excluded_exception(e):
                raise
            await self._on_failure()
            raise

    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info(f"Circuit {self.name}: CLOSING after successful HALF_OPEN call")
                self._state = CircuitState.CLOSED
                self._failure_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    async def _on_failure(self):
        """Handle failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit {self.name}: OPENING after HALF_OPEN failure")
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.config.failure_threshold:
                logger.warning(f"Circuit {self.name}: OPENING after {self._failure_count} failures")
                self._state = CircuitState.OPEN

    def _is_excluded_exception(self, exc: Exception) -> bool:
        """Check if exception should not count toward failure."""
        return isinstance(exc, self.config.excluded_exceptions)

    def get_status(self) -> dict:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "last_failure": self._last_failure_time,
        }

    async def reset(self):
        """Manually reset the circuit breaker."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_calls = 0
            logger.info(f"Circuit {self.name}: manually reset")


class CircuitOpenError(Exception):
    """Raised when circuit is open."""

    pass


gemini_circuit_breaker = CircuitBreaker(
    name="gemini",
    config=CircuitBreakerConfig(
        failure_threshold=10,
        recovery_timeout=60,
        half_open_max_calls=3,
    ),
)
