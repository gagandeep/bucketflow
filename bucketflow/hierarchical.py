import time
from threading import Lock
from typing import Optional, List
from .token_bucket import TokenBucket


class HierarchicalTokenBucket:
    """
    A hierarchical token bucket implementation that enforces rate limits at multiple levels.
    
    This allows for complex rate limiting strategies such as:
    - Global rate limits with per-user or per-resource sublimits
    - Tiered API access with different priorities
    - Organization → Team → User hierarchical limits
    
    When consuming tokens, the request must obtain tokens from all buckets in the hierarchy.
    """

    def __init__(self, 
                 capacity: float, 
                 fill_rate: float, 
                 parent: Optional['HierarchicalTokenBucket'] = None,
                 initial_tokens: Optional[float] = None,
                 name: Optional[str] = None):
        """
        Initialize a HierarchicalTokenBucket.
        
        Args:
            capacity: Maximum number of tokens this bucket can hold
            fill_rate: Rate at which tokens are added to this bucket (tokens per second)
            parent: Optional parent bucket in the hierarchy
            initial_tokens: Initial number of tokens in the bucket, defaults to capacity
            name: Optional name for this bucket for debugging
        """
        self.token_bucket = TokenBucket(capacity, fill_rate, initial_tokens)
        self.parent = parent
        self.children: List[HierarchicalTokenBucket] = []
        self.name = name or id(self)
        self.lock = Lock()
        
        # Register with parent if provided
        if parent:
            parent._add_child(self)
    
    def _add_child(self, child: 'HierarchicalTokenBucket') -> None:
        """Add a child bucket to this bucket."""
        with self.lock:
            self.children.append(child)
    
    def consume(self, tokens: float = 1.0, block: bool = False) -> bool:
        """
        Consume tokens from this bucket and all parent buckets.
        
        The operation succeeds only if tokens can be consumed from all buckets
        in the hierarchy chain up to the root.
        
        Args:
            tokens: Number of tokens to consume
            block: If True, block until enough tokens are available
            
        Returns:
            bool: True if tokens were consumed, False otherwise
        """
        # First, check if we can consume from all buckets without blocking
        # This is done as a pre-check to avoid partial consumption
        can_consume = self._can_consume_from_hierarchy(tokens)
        
        if not can_consume and not block:
            return False
        
        # If we need to block, we'll do the actual consumption with blocking
        if block:
            return self._blocking_consume_from_hierarchy(tokens)
        else:
            # If we can consume without blocking, do the actual consumption
            return self._perform_consume_from_hierarchy(tokens)
    
    def _can_consume_from_hierarchy(self, tokens: float) -> bool:
        """Check if tokens can be consumed from all buckets in the hierarchy."""
        # Start from the root of the hierarchy
        current = self
        while current.parent:
            current = current.parent
        
        # Work down the hierarchy checking each bucket
        return current._check_bucket_chain(tokens, self)
    
    def _check_bucket_chain(self, tokens: float, target: 'HierarchicalTokenBucket') -> bool:
        """
        Recursively check if tokens can be consumed from this bucket and its children
        down to the target bucket.
        """
        # Check if we have enough tokens in this bucket
        if self.token_bucket.tokens < tokens:
            return False
        
        # If we've reached the target, we're done
        if self == target:
            return True
        
        # Otherwise, check children that lead to the target
        for child in self.children:
            if child == target or child._contains_descendant(target):
                return child._check_bucket_chain(tokens, target)
        
        # Target is not in this branch
        return False
    
    def _contains_descendant(self, bucket: 'HierarchicalTokenBucket') -> bool:
        """Check if the given bucket is a descendant of this bucket."""
        if bucket in self.children:
            return True
        
        for child in self.children:
            if child._contains_descendant(bucket):
                return True
        
        return False
    
    def _blocking_consume_from_hierarchy(self, tokens: float) -> bool:
        """Consume tokens from all buckets in the hierarchy, blocking if necessary."""
        # Start from the root of the hierarchy
        current = self
        while current.parent:
            current = current.parent
        
        # Get all buckets in the path from root to this bucket
        path = []
        current._find_path_to(self, path)
        
        # Try to consume from all buckets, starting from the root
        # If any bucket can't provide tokens immediately, we'll need to calculate wait time
        while True:
            wait_time = 0
            all_can_consume = True
            
            for bucket in path:
                with bucket.token_bucket.lock:
                    bucket.token_bucket._add_tokens()
                    
                    if bucket.token_bucket.current_tokens < tokens:
                        all_can_consume = False
                        deficit = tokens - bucket.token_bucket.current_tokens
                        this_wait_time = deficit / bucket.token_bucket.fill_rate
                        wait_time = max(wait_time, this_wait_time)
            
            if all_can_consume:
                # All buckets have enough tokens, perform the consumption
                return self._perform_consume_from_hierarchy(tokens)
            
            # Wait for the calculated amount of time
            time.sleep(wait_time)
    
    def _perform_consume_from_hierarchy(self, tokens: float) -> bool:
        """Perform the actual consumption from all buckets in the hierarchy."""
        # Start from the root of the hierarchy
        current = self
        while current.parent:
            current = current.parent
        
        # Get all buckets in the path from root to this bucket
        path = []
        current._find_path_to(self, path)
        
        # Consume from all buckets
        for bucket in path:
            if not bucket.token_bucket.consume(tokens, block=False):
                # This shouldn't happen if checks were done properly
                # Rollback consumption from previous buckets
                for prev_bucket in path:
                    if prev_bucket == bucket:
                        break
                    prev_bucket.token_bucket.current_tokens += tokens
                return False
        
        return True
    
    def _find_path_to(self, target: 'HierarchicalTokenBucket', path: List['HierarchicalTokenBucket']) -> bool:
        """Find the path from this bucket to the target bucket."""
        path.append(self)
        
        if self == target:
            return True
        
        for child in self.children:
            if child._find_path_to(target, path):
                return True
        
        path.pop()
        return False
    
    @property
    def tokens(self) -> float:
        """Get the current number of tokens in this bucket."""
        return self.token_bucket.tokens


# Factory function to create a tree of hierarchical buckets
def create_bucket_hierarchy(config):
    """
    Create a hierarchical token bucket from a configuration dictionary.
    
    Example config:
    {
        "name": "root",
        "capacity": 100,
        "fill_rate": 10,
        "children": [
            {
                "name": "user1",
                "capacity": 20,
                "fill_rate": 2
            },
            {
                "name": "user2",
                "capacity": 30,
                "fill_rate": 3,
                "children": [
                    {
                        "name": "user2-api1",
                        "capacity": 10,
                        "fill_rate": 1
                    }
                ]
            }
        ]
    }
    
    Returns:
        dict: Map of bucket names to HierarchicalTokenBucket objects
    """
    bucket_map = {}
    
    def create_bucket(config_item, parent=None):
        bucket = HierarchicalTokenBucket(
            capacity=config_item["capacity"],
            fill_rate=config_item["fill_rate"],
            parent=parent,
            name=config_item["name"],
            initial_tokens=config_item.get("initial_tokens")
        )
        
        bucket_map[config_item["name"]] = bucket
        
        for child_config in config_item.get("children", []):
            create_bucket(child_config, parent=bucket)
        
        return bucket
    
    root_bucket = create_bucket(config)
    return bucket_map