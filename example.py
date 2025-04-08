from bucketflow import TokenBucket, rate_limit
import time
import threading
import random


def example_token_bucket():
    # Create a token bucket with capacity of 10 tokens, filling at 2 tokens per second
    bucket = TokenBucket(capacity=10, fill_rate=2)
    
    print("Token Bucket Example")
    print(f"Initial tokens: {bucket.tokens}")
    
    # Consume tokens
    print(f"Consuming 5 tokens: {bucket.consume(5)}")
    print(f"Remaining tokens: {bucket.tokens}")
    
    # Try to consume more than available
    print(f"Consuming 10 tokens: {bucket.consume(10, block=False)}")
    
    # Wait for tokens to refill
    print("Waiting 3 seconds for tokens to refill...")
    time.sleep(3)
    print(f"Tokens after waiting: {bucket.tokens}")
    
    # Consume with blocking
    print("Consuming 10 tokens with blocking...")
    start = time.time()
    bucket.consume(10, block=True)
    end = time.time()
    print(f"Blocked for {end - start:.2f} seconds")


# Example using the rate limit decorator
@rate_limit(tokens_per_second=2, capacity=5)
def rate_limited_function(iteration):
    print(f"Function executed: #{iteration} at {time.time():.2f}")


def example_rate_limit_decorator():
    print("\nRate Limit Decorator Example")
    print("This function is limited to 2 calls per second with bursts up to 5 calls")
    
    for i in range(10):
        rate_limited_function(i)


def threaded_example():
    print("\nThreaded Example")
    bucket = TokenBucket(capacity=5, fill_rate=1)
    
    def worker(thread_id):
        for i in range(3):
            tokens_to_consume = random.randint(1, 3)
            print(f"Thread {thread_id} trying to consume {tokens_to_consume} tokens")
            success = bucket.consume(tokens_to_consume, block=True)
            print(f"Thread {thread_id} {'succeeded' if success else 'failed'} at {time.time():.2f}")
            time.sleep(random.random())
    
    threads = []
    for i in range(3):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()


if __name__ == "__main__":
    example_token_bucket()
    example_rate_limit_decorator()
    threaded_example()