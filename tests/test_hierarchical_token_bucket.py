import unittest
import time
import threading
from token_bucket.hierarchical import HierarchicalTokenBucket, create_bucket_hierarchy


class TestHierarchicalTokenBucket(unittest.TestCase):
    def test_simple_hierarchy(self):
        # Create a simple hierarchy
        root = HierarchicalTokenBucket(capacity=100, fill_rate=10, name="root")
        child = HierarchicalTokenBucket(capacity=20, fill_rate=2, parent=root, name="child")
        
        # Verify initial tokens
        self.assertAlmostEqual(root.tokens, 100, delta=0.1)
        self.assertAlmostEqual(child.tokens, 20, delta=0.1)
        
        # Consume from child, which should also consume from root
        self.assertTrue(child.consume(10))
        
        # Verify tokens were consumed from both
        self.assertAlmostEqual(root.tokens, 90, delta=0.1)
        self.assertAlmostEqual(child.tokens, 10, delta=0.1)
    
    def test_deep_hierarchy(self):
        # Create a deep hierarchy
        root = HierarchicalTokenBucket(capacity=100, fill_rate=10, name="root")
        level1 = HierarchicalTokenBucket(capacity=50, fill_rate=5, parent=root, name="level1")
        level2 = HierarchicalTokenBucket(capacity=20, fill_rate=2, parent=level1, name="level2")
        level3 = HierarchicalTokenBucket(capacity=10, fill_rate=1, parent=level2, name="level3")
        
        # Consume from the deepest level
        self.assertTrue(level3.consume(5))
        
        # Verify tokens were consumed at all levels
        self.assertAlmostEqual(root.tokens, 95, delta=0.1)
        self.assertAlmostEqual(level1.tokens, 45, delta=0.1)
        self.assertAlmostEqual(level2.tokens, 15, delta=0.1)
        self.assertAlmostEqual(level3.tokens, 5, delta=0.1)
    
    def test_consumption_hierarchy_limits(self):
        # Create a hierarchy where a child has fewer tokens than parent
        root = HierarchicalTokenBucket(capacity=100, fill_rate=10, name="root")
        child = HierarchicalTokenBucket(capacity=15, fill_rate=2, parent=root, name="child")
        
        # Try to consume more than child has but less than root
        self.assertFalse(child.consume(20, block=False))
        
        # Verify no tokens were consumed from either
        self.assertAlmostEqual(root.tokens, 100, delta=0.1)
        self.assertAlmostEqual(child.tokens, 15, delta=0.1)
        
        # Now consume exactly what child has
        self.assertTrue(child.consume(15))
        
        # Verify tokens were consumed from both
        self.assertAlmostEqual(root.tokens, 85, delta=0.1)
        self.assertAlmostEqual(child.tokens, 0, delta=0.1)
    
    def test_blocking_hierarchical_consume(self):
        # Create a hierarchy with empty child bucket
        root = HierarchicalTokenBucket(capacity=100, fill_rate=10, name="root")
        child = HierarchicalTokenBucket(capacity=5, fill_rate=5, initial_tokens=0, name="child", parent=root)
        
        # Try to consume with blocking
        start = time.time()
        self.assertTrue(child.consume(2, block=True))
        elapsed = time.time() - start
        
        # Should have blocked for about 0.4 seconds (2 tokens / 5 tokens per second)
        self.assertGreaterEqual(elapsed, 0.3)
        self.assertLess(elapsed, 0.7)  # Allow margin for test execution
        
        # Verify tokens were consumed
        self.assertAlmostEqual(root.tokens, 98, delta=0.1)
        # After blocking, there might be small residual tokens due to timing differences
        self.assertAlmostEqual(child.tokens, 0, delta=0.1)  # Allow small delta for floating point
    
    def test_factory_function(self):
        # Define a hierarchy configuration
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
                },
                {
                    "name": "service2",
                    "capacity": 20,
                    "fill_rate": 2
                }
            ]
        }
        
        # Create the hierarchy
        buckets = create_bucket_hierarchy(config)
        
        # Verify buckets were created correctly
        self.assertEqual(len(buckets), 4)
        self.assertIn("global", buckets)
        self.assertIn("service1", buckets)
        self.assertIn("endpoint1", buckets)
        self.assertIn("service2", buckets)
        
        # Verify parent-child relationships
        endpoint1 = buckets["endpoint1"]
        service1 = buckets["service1"]
        global_bucket = buckets["global"]
        
        self.assertEqual(endpoint1.parent, service1)
        self.assertEqual(service1.parent, global_bucket)
        self.assertIsNone(global_bucket.parent)
        
        # Test consumption through the hierarchy
        self.assertTrue(endpoint1.consume(5))
        
        # Verify tokens were consumed at all levels
        self.assertAlmostEqual(global_bucket.tokens, 95, delta=0.1)
        self.assertAlmostEqual(service1.tokens, 35, delta=0.1)
        self.assertAlmostEqual(endpoint1.tokens, 10, delta=0.1)
    
    def test_sibling_independence(self):
        # Create a hierarchy with siblings
        root = HierarchicalTokenBucket(capacity=100, fill_rate=10, name="root")
        child1 = HierarchicalTokenBucket(capacity=20, fill_rate=2, parent=root, name="child1")
        child2 = HierarchicalTokenBucket(capacity=30, fill_rate=3, parent=root, name="child2")
        
        # Consume from one child
        self.assertTrue(child1.consume(10))
        
        # Verify only the relevant buckets were affected
        self.assertAlmostEqual(root.tokens, 90, delta=0.1)
        self.assertAlmostEqual(child1.tokens, 10, delta=0.1)
        self.assertAlmostEqual(child2.tokens, 30, delta=0.1)  # Unchanged
        
    def test_hierarchy_refill(self):
        """Test that tokens refill correctly at all levels of the hierarchy"""
        root = HierarchicalTokenBucket(capacity=100, fill_rate=20, name="root", initial_tokens=80)
        child = HierarchicalTokenBucket(capacity=50, fill_rate=10, parent=root, name="child", initial_tokens=30)
        
        # Wait for tokens to refill
        time.sleep(1)
        
        # Verify tokens refilled at correct rates
        self.assertAlmostEqual(root.tokens, 100, delta=0.1)  # Capped at capacity
        # Allow for slight floating-point differences
        self.assertAlmostEqual(child.tokens, 40, delta=0.1)  # Should have added ~10 tokens
        
    def test_concurrent_consumption(self):
        """Test consuming tokens from multiple hierarchical buckets concurrently"""
        root = HierarchicalTokenBucket(capacity=100, fill_rate=10, name="root")
        child1 = HierarchicalTokenBucket(capacity=30, fill_rate=5, parent=root, name="child1")
        child2 = HierarchicalTokenBucket(capacity=30, fill_rate=5, parent=root, name="child2")
        
        # Use threads to consume concurrently
        results = {"child1": False, "child2": False}
        
        def consume_child1():
            results["child1"] = child1.consume(20)
            
        def consume_child2():
            results["child2"] = child2.consume(20)
        
        t1 = threading.Thread(target=consume_child1)
        t2 = threading.Thread(target=consume_child2)
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
        # Both should succeed and tokens should be consumed from root
        self.assertTrue(results["child1"])
        self.assertTrue(results["child2"])
        self.assertAlmostEqual(root.tokens, 60, delta=0.1)  # 100 - 20 - 20
        self.assertAlmostEqual(child1.tokens, 10, delta=0.1)  # 30 - 20
        self.assertAlmostEqual(child2.tokens, 10, delta=0.1)  # 30 - 20
        
    def test_boundary_conditions(self):
        """Test edge cases like zero capacity, zero fill rate, etc."""
        # Zero initial tokens
        root = HierarchicalTokenBucket(capacity=10, fill_rate=10, initial_tokens=0)
        child = HierarchicalTokenBucket(capacity=5, fill_rate=5, initial_tokens=0, parent=root)
        
        # Should not be able to consume immediately
        self.assertFalse(child.consume(1, block=False))
        
        # Very small capacity and fill rate
        root = HierarchicalTokenBucket(capacity=0.1, fill_rate=0.1)
        self.assertAlmostEqual(root.tokens, 0.1, delta=0.01)
        self.assertTrue(root.consume(0.05))
        self.assertAlmostEqual(root.tokens, 0.05, delta=0.01)
        
    def test_multiple_consumption_attempts(self):
        """Test multiple consecutive consumption attempts"""
        root = HierarchicalTokenBucket(capacity=50, fill_rate=5, name="root")
        child = HierarchicalTokenBucket(capacity=20, fill_rate=2, parent=root, name="child")
        
        # Consume multiple times
        self.assertTrue(child.consume(5))
        self.assertTrue(child.consume(5))
        self.assertTrue(child.consume(5))
        self.assertTrue(child.consume(5))
        
        # Should be out of tokens now
        self.assertFalse(child.consume(1, block=False))
        
        # Root should still have tokens but child is empty
        self.assertAlmostEqual(root.tokens, 30, delta=0.1)  # 50 - 20
        self.assertAlmostEqual(child.tokens, 0, delta=0.1)
        
    def test_nested_hierarchies_with_shared_parent(self):
        """Test more complex hierarchies with shared parents and multiple levels"""
        # Create a more complex hierarchy:
        #       root
        #      /    \
        #  team1    team2
        #  /  \      /  \
        # u1  u2    u3   u4
        
        root = HierarchicalTokenBucket(capacity=1000, fill_rate=100, name="root")
        team1 = HierarchicalTokenBucket(capacity=400, fill_rate=40, parent=root, name="team1")
        team2 = HierarchicalTokenBucket(capacity=400, fill_rate=40, parent=root, name="team2")
        
        user1 = HierarchicalTokenBucket(capacity=100, fill_rate=10, parent=team1, name="user1")
        user2 = HierarchicalTokenBucket(capacity=100, fill_rate=10, parent=team1, name="user2")
        user3 = HierarchicalTokenBucket(capacity=100, fill_rate=10, parent=team2, name="user3")
        user4 = HierarchicalTokenBucket(capacity=100, fill_rate=10, parent=team2, name="user4")
        
        # Users from different teams should not affect each other's direct parent
        self.assertTrue(user1.consume(50))
        self.assertTrue(user3.consume(50))
        
        # Check that the correct amounts were consumed
        self.assertAlmostEqual(root.tokens, 900, delta=0.1)  # 1000 - 50 - 50
        self.assertAlmostEqual(team1.tokens, 350, delta=0.1)  # 400 - 50
        self.assertAlmostEqual(team2.tokens, 350, delta=0.1)  # 400 - 50
        self.assertAlmostEqual(user1.tokens, 50, delta=0.1)  # 100 - 50
        self.assertAlmostEqual(user2.tokens, 100, delta=0.1)  # Unchanged
        self.assertAlmostEqual(user3.tokens, 50, delta=0.1)  # 100 - 50
        self.assertAlmostEqual(user4.tokens, 100, delta=0.1)  # Unchanged
        
        # Now consume from the other users
        self.assertTrue(user2.consume(75))
        self.assertTrue(user4.consume(75))
        
        # Check final state
        self.assertAlmostEqual(root.tokens, 750, delta=0.1)  # 900 - 75 - 75
        self.assertAlmostEqual(team1.tokens, 275, delta=0.1)  # 350 - 75
        self.assertAlmostEqual(team2.tokens, 275, delta=0.1)  # 350 - 75


if __name__ == '__main__':
    unittest.main()