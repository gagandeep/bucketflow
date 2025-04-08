import unittest
import time
from bucketflow import TokenBucket, rate_limit
from bucketflow.decorators import RateLimitExceeded


class TestTokenBucket(unittest.TestCase):
    def test_initial_tokens(self):
        bucket = TokenBucket(capacity=10, fill_rate=1)
        self.assertAlmostEqual(bucket.tokens, 10, places=2)
        
        bucket = TokenBucket(capacity=10, fill_rate=1, initial_tokens=5)
        self.assertAlmostEqual(bucket.tokens, 5, places=2)
    
    def test_consume(self):
        bucket = TokenBucket(capacity=10, fill_rate=1)
        
        # Should be able to consume up to capacity
        self.assertTrue(bucket.consume(5))
        self.assertAlmostEqual(bucket.tokens, 5, places=2)
        
        self.assertTrue(bucket.consume(5))
        self.assertAlmostEqual(bucket.tokens, 0, places=2)
        
        # Should not be able to consume more when empty
        self.assertFalse(bucket.consume(1, block=False))
        
    def test_refill(self):
        bucket = TokenBucket(capacity=10, fill_rate=5, initial_tokens=0)
        
        # Wait for tokens to refill
        time.sleep(1)
        
        # Should have ~5 tokens after 1 second
        self.assertAlmostEqual(bucket.tokens, 5, delta=0.5)
        
    def test_blocking_consume(self):
        bucket = TokenBucket(capacity=10, fill_rate=5, initial_tokens=2)
        
        start = time.time()
        # Should block for ~0.6 seconds (need 3 more tokens at 5 tokens/sec)
        self.assertTrue(bucket.consume(5, block=True))
        elapsed = time.time() - start
        
        self.assertGreaterEqual(elapsed, 0.5)
        self.assertLess(elapsed, 0.9)  # Allow some margin for test execution
        
    def test_capacity_limit(self):
        bucket = TokenBucket(capacity=10, fill_rate=100)
        
        # Wait to ensure we would exceed capacity if not limited
        time.sleep(0.2)  # Would add 20 tokens if not capped
        
        # Should be capped at capacity
        self.assertAlmostEqual(bucket.tokens, 10, places=2)


class TestRateLimitDecorator(unittest.TestCase):
    def test_rate_limit_decorator(self):
        counter = [0]
        
        @rate_limit(tokens_per_second=10, block=False)
        def increment():
            counter[0] += 1
            return counter[0]
            
        # First 10 calls should succeed (initial capacity)
        for i in range(10):
            self.assertEqual(increment(), i + 1)
            
        # Next call should fail
        with self.assertRaises(RateLimitExceeded):
            increment()
            
        # Wait for token to refill
        time.sleep(0.11)  # Slightly more than 0.1s needed for 1 token
        
        # Should succeed again
        self.assertEqual(increment(), 11)
            
    def test_blocking_decorator(self):
        @rate_limit(tokens_per_second=5, capacity=1, block=True)
        def slow_function():
            return time.time()
            
        # First call succeeds immediately
        first_time = slow_function()
        
        # Second call should block for ~0.2 seconds
        start = time.time()
        second_time = slow_function()
        elapsed = second_time - start
        
        self.assertGreaterEqual(elapsed, 0.19)  # Allow small margin of error


if __name__ == '__main__':
    unittest.main()