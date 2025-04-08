import functools
import time
from typing import Callable, Optional, Union
from .token_bucket import TokenBucket


def rate_limit(tokens_per_second: Union[float, int], 
              capacity: Optional[Union[float, int]] = None,
              block: bool = True):
    """
    Decorator for rate limiting a function using the token bucket algorithm.
    
    Args:
        tokens_per_second: Rate at which tokens are added (requests allowed per second)
        capacity: Maximum burst capacity (defaults to tokens_per_second if None)
        block: If True, wait until enough tokens are available; if False, raise exception
        
    Returns:
        Decorated function that is rate limited
        
    Examples:
        @rate_limit(10)  # Allow 10 requests per second
        def some_function():
            pass
            
        @rate_limit(5, capacity=10)  # Allow bursts of up to 10 requests, then 5 per second
        def another_function():
            pass
    """
    capacity = capacity if capacity is not None else tokens_per_second
    bucket = TokenBucket(capacity=capacity, fill_rate=tokens_per_second)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not bucket.consume(1, block=block):
                raise RateLimitExceeded(f"Rate limit exceeded: {tokens_per_second} per second")
            return func(*args, **kwargs)
        return wrapper
    return decorator


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded and block=False."""
    pass