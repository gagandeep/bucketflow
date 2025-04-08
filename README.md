# BucketFlow

A Python library for rate limiting using the Token Bucket algorithm, with support for hierarchical rate limiting.

## Installation

```bash
pip install bucketflow
```

For distributed rate limiting with Redis:

```bash
pip install bucketflow[distributed]
```

## What is Token Bucket?

The Token Bucket algorithm works by having a bucket that is filled with tokens at a constant rate. Each request consumes one or more tokens. If there are enough tokens, the request is allowed; otherwise, it's either blocked or rejected.

Key features:
- Controls the average rate of requests
- Allows for bursts of traffic up to a configurable limit
- Simple to understand and implement

## Basic Usage

```python
from bucketflow import TokenBucket

# Create a token bucket with capacity of 10 tokens, filling at 2 tokens per second
bucket = TokenBucket(capacity=10, fill_rate=2)

# Consume a token (returns True if successful, False if not enough tokens)
if bucket.consume():
    # Perform rate-limited operation
    process_request()
else:
    # Handle rate limit exceeded
    return_rate_limit_error()

# Consume multiple tokens
bucket.consume(5)

# Block until tokens are available
bucket.consume(3, block=True)
```

## Decorator Usage

```python
from bucketflow import rate_limit
import time

# Allow 2 calls per second with a burst capacity of 5
@rate_limit(tokens_per_second=2, capacity=5)
def api_request():
    # This function can only be called at the specified rate
    return fetch_data_from_api()

# Non-blocking behavior (raises RateLimitExceeded if exceeded)
@rate_limit(tokens_per_second=1, block=False)
def limited_function():
    pass
```

## Async Support

```python
from bucketflow.async_token_bucket import AsyncTokenBucket, async_rate_limit
import asyncio

async def example():
    # Create an async token bucket
    bucket = AsyncTokenBucket(capacity=10, fill_rate=2)
    
    # Consume tokens asynchronously
    if await bucket.consume(5):
        await process_request()

# Decorate async functions
@async_rate_limit(tokens_per_second=2)
async def rate_limited_api_call():
    response = await make_http_request()
    return response
```

## Hierarchical Rate Limiting

BucketFlow supports hierarchical rate limiting, where tokens must be consumed from multiple buckets in a parent-child relationship:

```python
from bucketflow.hierarchical import HierarchicalTokenBucket

# Create a root bucket with 100 tokens, filling at 10 tokens per second
root = HierarchicalTokenBucket(capacity=100, fill_rate=10, name="root")

# Create child buckets
user1 = HierarchicalTokenBucket(capacity=20, fill_rate=2, parent=root, name="user1")
user2 = HierarchicalTokenBucket(capacity=30, fill_rate=3, parent=root, name="user2")

# Create a nested child bucket
api1 = HierarchicalTokenBucket(capacity=10, fill_rate=1, parent=user2, name="api1")

# When consuming from api1, tokens are also consumed from user2 and root
api1.consume(5)  # Takes 5 tokens from api1, user2, and root
```

### Creating a Bucket Hierarchy from Configuration

You can define and create an entire hierarchy from a dictionary configuration:

```python
from bucketflow.hierarchical import create_bucket_hierarchy

# Define the hierarchy
config = {
    "name": "global",
    "capacity": 100,
    "fill_rate": 10,
    "children": [
        {
            "name": "service1",
            "capacity": 40,
            "fill_rate": 4,
            "children": [
                {
                    "name": "endpoint1",
                    "capacity": 15,
                    "fill_rate": 1.5
                }
            ]
        }
    ]
}

# Create all buckets
buckets = create_bucket_hierarchy(config)

# Access buckets by name
buckets["endpoint1"].consume(5)
```

### Benefits of Hierarchical Rate Limiting

- **Multi-level rate limiting**: Enforce limits at multiple levels of granularity
- **Resource allocation**: Divide resources among users, services, or endpoints
- **Priority-based access**: Allocate more resources to critical services
- **Easy configuration**: Create complex hierarchies from dictionary configurations
- **Organizational structure mapping**: Model company → department → team → user hierarchies

## Distributed Rate Limiting

For rate limiting across multiple processes or servers, use the Redis-backed implementation:

```python
import redis
from bucketflow.distributed import RedisTokenBucket

# Connect to Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Create a distributed token bucket
bucket = RedisTokenBucket(
    redis_client=redis_client,
    key="api-rate-limit",  # Unique key for this rate limiter
    capacity=10,
    fill_rate=2
)

# Use it just like a regular token bucket
if bucket.consume():
    # Process the request
    pass
```

## License

MIT