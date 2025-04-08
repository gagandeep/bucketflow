from bucketflow.hierarchical import HierarchicalTokenBucket, create_bucket_hierarchy
import time

def simple_hierarchy_example():
    """
    Demonstrate a simple hierarchy with a root bucket and child buckets.
    """
    print("Simple Hierarchy Example")
    
    # Create a root bucket with 100 tokens, filling at 10 tokens per second
    root = HierarchicalTokenBucket(capacity=100, fill_rate=10, name="root")
    
    # Create child buckets
    user1 = HierarchicalTokenBucket(capacity=20, fill_rate=2, parent=root, name="user1")
    user2 = HierarchicalTokenBucket(capacity=30, fill_rate=3, parent=root, name="user2")
    
    # Create nested child bucket
    api1 = HierarchicalTokenBucket(capacity=10, fill_rate=1, parent=user2, name="api1")
    
    print(f"Root tokens: {root.tokens}")
    print(f"User1 tokens: {user1.tokens}")
    print(f"User2 tokens: {user2.tokens}")
    print(f"API1 tokens: {api1.tokens}")
    
    print("\nConsuming 15 tokens from user1...")
    success = user1.consume(15)
    print(f"Success: {success}")
    print(f"Root tokens after: {root.tokens}")
    print(f"User1 tokens after: {user1.tokens}")
    
    print("\nConsuming 8 tokens from api1...")
    success = api1.consume(8)
    print(f"Success: {success}")
    print(f"Root tokens after: {root.tokens}")
    print(f"User2 tokens after: {user2.tokens}")
    print(f"API1 tokens after: {api1.tokens}")
    
    # Try to consume more than available at the lowest level
    print("\nTrying to consume 5 more tokens from api1 (should fail)...")
    success = api1.consume(5, block=False)
    print(f"Success: {success}")
    
    # Try with blocking
    print("\nTrying to consume 5 more tokens from api1 with blocking...")
    start = time.time()
    success = api1.consume(5, block=True)
    end = time.time()
    print(f"Success: {success}")
    print(f"Blocked for {end - start:.2f} seconds")
    print(f"API1 tokens after: {api1.tokens}")


def factory_example():
    """
    Demonstrate creating a hierarchy using the factory function.
    """
    print("\nFactory Function Example")
    
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
                    },
                    {
                        "name": "endpoint2",
                        "capacity": 25,
                        "fill_rate": 2.5
                    }
                ]
            },
            {
                "name": "service2",
                "capacity": 60,
                "fill_rate": 6
            }
        ]
    }
    
    # Create the hierarchy
    buckets = create_bucket_hierarchy(config)
    
    # Use the buckets
    print("Available buckets:", ", ".join(buckets.keys()))
    
    # Consume from an endpoint
    endpoint = buckets["endpoint1"]
    print(f"\nConsuming 10 tokens from {endpoint.name}...")
    success = endpoint.consume(10)
    print(f"Success: {success}")
    
    # Check tokens at each level
    print(f"Global tokens: {buckets['global'].tokens}")
    print(f"Service1 tokens: {buckets['service1'].tokens}")
    print(f"Endpoint1 tokens: {buckets['endpoint1'].tokens}")


if __name__ == "__main__":
    simple_hierarchy_example()
    factory_example()