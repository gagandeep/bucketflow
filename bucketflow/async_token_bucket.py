import time
import asyncio
from typing import Optional, Union
from asyncio import Lock


class AsyncTokenBucket:
    """
    An asynchronous Token Bucket implementation for rate limiting.
    
    Similar to TokenBucket but designed for use with asyncio.
    """

    def __init__(self, capacity: float, fill_rate: float, initial_tokens: Optional[float] = None):
        """
        Initialize the AsyncTokenBucket.
        
        Args:
            capacity: Maximum number of tokens the bucket can hold
            fill_rate: Rate at which tokens are added to the bucket (tokens per second)
            initial_tokens: Initial number of tokens in the bucket, defaults to capacity
        """
        self.capacity = float(capacity)
        self.fill_rate = float(fill_rate)
        self.current_tokens = float(initial_tokens if initial_tokens is not None else capacity)
        self.last_update = time.time()
        self.lock = Lock()

    def _add_tokens(self) -> None:
        """Add tokens based on the time elapsed since the last update."""
        now = time.time()
        elapsed = now - self.last_update
        new_tokens = elapsed * self.fill_rate
        
        self.current_tokens = min(self.capacity, self.current_tokens + new_tokens)
        self.last_update = now

    async def consume(self, tokens: float = 1.0, block: bool = False) -> bool:
        """
        Consume tokens from the bucket asynchronously.
        
        Args:
            tokens: Number of tokens to consume
            block: If True, block until enough tokens are available
            
        Returns:
            bool: True if tokens were consumed, False otherwise
        """
        if tokens > self.capacity:
            raise ValueError(f"Cannot consume more tokens than capacity: {tokens} > {self.capacity}")
        
        async with self.lock:
            self._add_tokens()
            
            if self.current_tokens >= tokens:
                self.current_tokens -= tokens
                return True
                
            if not block:
                return False
                
            # If blocking is requested, calculate the wait time
            deficit = tokens - self.current_tokens
            wait_time = deficit / self.fill_rate
            
            await asyncio.sleep(wait_time)
            self.current_tokens = 0.0
            self.last_update = time.time()
            return True
            
    async def get_tokens(self) -> float:
        """Get current token count (updates tokens before returning)."""
        async with self.lock:
            self._add_tokens()
            return self.current_tokens


def async_rate_limit(tokens_per_second: Union[float, int], 
                    capacity: Optional[Union[float, int]] = None,
                    block: bool = True):
    """
    Decorator for rate limiting an async function using the token bucket algorithm.
    
    Args:
        tokens_per_second: Rate at which tokens are added (requests allowed per second)
        capacity: Maximum burst capacity (defaults to tokens_per_second if None)
        block: If True, wait until enough tokens are available; if False, raise exception
        
    Returns:
        Decorated async function that is rate limited
    """
    capacity = capacity if capacity is not None else tokens_per_second
    bucket = AsyncTokenBucket(capacity=capacity, fill_rate=tokens_per_second)
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not await bucket.consume(1, block=block):
                raise RateLimitExceeded(f"Rate limit exceeded: {tokens_per_second} per second")
            return await func(*args, **kwargs)
        return wrapper
    return decorator