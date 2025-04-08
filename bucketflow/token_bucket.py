import time
from threading import Lock
from typing import Optional


class TokenBucket:
    """
    A Token Bucket implementation for rate limiting.
    
    The Token Bucket algorithm works by having a bucket that is filled with tokens at a
    constant rate. Each request consumes one or more tokens. If there are enough tokens,
    the request is allowed; otherwise, it's either blocked or delayed.
    
    Attributes:
        capacity (float): Maximum number of tokens the bucket can hold
        fill_rate (float): Rate at which tokens are added to the bucket (tokens per second)
        current_tokens (float): Current number of tokens in the bucket
        last_update (float): Timestamp of the last token update
        lock (Lock): Thread lock for thread safety
    """

    def __init__(self, capacity: float, fill_rate: float, initial_tokens: Optional[float] = None):
        """
        Initialize the TokenBucket.
        
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

    def consume(self, tokens: float = 1.0, block: bool = False) -> bool:
        """
        Consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            block: If True, block until enough tokens are available
            
        Returns:
            bool: True if tokens were consumed, False otherwise
        """
        if tokens > self.capacity:
            raise ValueError(f"Cannot consume more tokens than capacity: {tokens} > {self.capacity}")
        
        with self.lock:
            self._add_tokens()
            
            if self.current_tokens >= tokens:
                self.current_tokens -= tokens
                return True
                
            if not block:
                return False
                
            # If blocking is requested, calculate the wait time
            deficit = tokens - self.current_tokens
            wait_time = deficit / self.fill_rate
            
            time.sleep(wait_time)
            self.current_tokens = 0.0
            self.last_update = time.time()
            return True
            
    @property
    def tokens(self) -> float:
        """Get current token count (updates tokens before returning)."""
        with self.lock:
            self._add_tokens()
            return self.current_tokens