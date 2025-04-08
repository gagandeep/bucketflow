import time
import redis
from typing import Optional

class RedisTokenBucket:
    """
    A distributed Token Bucket implementation using Redis.
    
    This implementation allows rate limiting across multiple processes or servers
    by storing the token bucket state in Redis.
    """

    def __init__(self, 
                 redis_client: redis.Redis,
                 key: str,
                 capacity: float, 
                 fill_rate: float, 
                 initial_tokens: Optional[float] = None):
        """
        Initialize the RedisTokenBucket.
        
        Args:
            redis_client: Redis client instance
            key: Redis key to use for this bucket
            capacity: Maximum number of tokens the bucket can hold
            fill_rate: Rate at which tokens are added to the bucket (tokens per second)
            initial_tokens: Initial number of tokens in the bucket, defaults to capacity
        """
        self.redis = redis_client
        self.key = f"token_bucket:{key}"
        self.capacity = float(capacity)
        self.fill_rate = float(fill_rate)
        
        # Initialize the bucket in Redis if it doesn't exist
        initial_tokens = float(initial_tokens if initial_tokens is not None else capacity)
        self.redis.hsetnx(self.key, "tokens", initial_tokens)
        self.redis.hsetnx(self.key, "last_update", time.time())

    def _add_tokens(self) -> None:
        """
        Add tokens based on the time elapsed since the last update.
        
        This function needs to be executed in a Redis transaction to ensure atomicity.
        """
        # This Lua script implements the token update logic atomically within Redis
        script = """
        local tokens = tonumber(redis.call('hget', KEYS[1], 'tokens'))
        local last_update = tonumber(redis.call('hget', KEYS[1], 'last_update'))
        local now = tonumber(ARGV[1])
        local capacity = tonumber(ARGV[2])
        local fill_rate = tonumber(ARGV[3])
        
        local elapsed = now - last_update
        local new_tokens = math.min(capacity, tokens + (elapsed * fill_rate))
        
        redis.call('hset', KEYS[1], 'tokens', new_tokens)
        redis.call('hset', KEYS[1], 'last_update', now)
        
        return new_tokens
        """
        
        now = time.time()
        self.redis.eval(script, 1, self.key, now, self.capacity, self.fill_rate)

    def consume(self, tokens: float = 1.0, block: bool = False) -> bool:
        """
        Consume tokens from the distributed bucket.
        
        Args:
            tokens: Number of tokens to consume
            block: If True, block until enough tokens are available
            
        Returns:
            bool: True if tokens were consumed, False otherwise
        """
        if tokens > self.capacity:
            raise ValueError(f"Cannot consume more tokens than capacity: {tokens} > {self.capacity}")
        
        # This Lua script handles the token consumption atomically within Redis
        consume_script = """
        local tokens = tonumber(redis.call('hget', KEYS[1], 'tokens'))
        local last_update = tonumber(redis.call('hget', KEYS[1], 'last_update'))
        local now = tonumber(ARGV[1])
        local capacity = tonumber(ARGV[2])
        local fill_rate = tonumber(ARGV[3])
        local requested = tonumber(ARGV[4])
        
        local elapsed = now - last_update
        local current = math.min(capacity, tokens + (elapsed * fill_rate))
        
        if current >= requested then
            current = current - requested
            redis.call('hset', KEYS[1], 'tokens', current)
            redis.call('hset', KEYS[1], 'last_update', now)
            return 1
        else
            redis.call('hset', KEYS[1], 'tokens', current)
            redis.call('hset', KEYS[1], 'last_update', now)
            return 0
        end
        """
        
        now = time.time()
        result = self.redis.eval(consume_script, 1, self.key, now, self.capacity, self.fill_rate, tokens)
        
        if result:
            return True
            
        if not block:
            return False
            
        # If blocking is requested, calculate the wait time and sleep
        with self.redis.pipeline() as pipe:
            pipe.hget(self.key, "tokens")
            pipe.hget(self.key, "last_update")
            current_tokens, last_update = pipe.execute()
        
        current_tokens = float(current_tokens)
        last_update = float(last_update)
        
        elapsed = time.time() - last_update
        current_tokens = min(self.capacity, current_tokens + elapsed * self.fill_rate)
        
        deficit = tokens - current_tokens
        wait_time = deficit / self.fill_rate
        
        time.sleep(wait_time)
        
        # Try again after waiting
        return self.consume(tokens, block=False)