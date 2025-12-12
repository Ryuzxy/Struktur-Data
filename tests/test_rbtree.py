"""
Unit tests for Red-Black Tree implementation
"""
import pytest
from datetime import datetime
from rbtree.rbtree import RedBlackTree
from domain.reservation import ReservationFactory

class TestRedBlackTree:
    """Test cases for Red-Black Tree"""
    
    def test_empty_tree(self):
        """Test empty tree properties"""
        tree = RedBlackTree()
        assert tree.is_empty()
        assert len(tree) == 0
        assert tree.get_height() == 0
        
        # Search should return None
        assert tree.search(123) is None
        
        # Range search should return empty list
        assert tree.search_range(0, 100) == []
    
    def test_insert_single_node(self):
        """Test inserting single node"""
        tree = RedBlackTree()
        tree.insert(10, "data1")
        
        assert not tree.is_empty()
        assert len(tree) == 1
        assert tree.search(10) == "data1"
        assert tree.find_min() == "data1"
        assert tree.find_max() == "data1"
        
        # Root should be black
        assert tree.root.color == False  # BLACK
    
    def test_insert_multiple_nodes(self):
        """Test inserting multiple nodes"""
        tree = RedBlackTree()
        
        # Insert in random order
        data = [(15, "data15"), (5, "data5"), (20, "data20"), 
                (3, "data3"), (10, "data10"), (17, "data17"), (25, "data25")]
        
        for key, value in data:
            tree.insert(key, value)
        
        assert len(tree) == 7
        
        # Check all data can be retrieved
        for key, value in data:
            assert tree.search(key) == value
        
        # Check min and max
        assert tree.find_min() == "data3"
        assert tree.find_max() == "data25"
    
    def test_tree_properties(self):
        """Test Red-Black Tree properties"""
        tree = RedBlackTree()
        
        # Insert 100 nodes
        for i in range(100):
            tree.insert(i, f"data{i}")
        
        assert len(tree) == 100
        
        # Verify RBT properties
        is_valid, message = tree.is_valid_rbt()
        assert is_valid, message
        
        # Tree height should be O(log n)
        height = tree.get_height()
        assert height <= 2 * (100).bit_length()  # Upper bound for RBT
    
    def test_range_search(self):
        """Test range search functionality"""
        tree = RedBlackTree()
        
        # Insert values
        values = [(1, "A"), (3, "B"), (5, "C"), (7, "D"), (9, "E")]
        for key, value in values:
            tree.insert(key, value)
        
        # Test exact range
        results = tree.search_range(3, 7)
        assert len(results) == 3
        assert set(results) == {"B", "C", "D"}
        
        # Test partial range
        results = tree.search_range(4, 8)
        assert len(results) == 2
        assert set(results) == {"C", "D"}
        
        # Test range outside bounds
        results = tree.search_range(10, 15)
        assert len(results) == 0
        
        # Test range covering all
        results = tree.search_range(0, 10)
        assert len(results) == 5
    
    def test_delete(self):
        """Test node deletion"""
        tree = RedBlackTree()
        
        # Insert nodes
        for i in [10, 5, 15, 3, 7, 12, 18]:
            tree.insert(i, f"data{i}")
        
        assert len(tree) == 7
        
        # Delete leaf node
        assert tree.delete(3)
        assert len(tree) == 6
        assert tree.search(3) is None
        assert tree.is_valid_rbt()[0]
        
        # Delete node with one child
        assert tree.delete(15)
        assert len(tree) == 5
        assert tree.search(15) is None
        assert tree.is_valid_rbt()[0]
        
        # Delete root
        assert tree.delete(10)
        assert len(tree) == 4
        assert tree.search(10) is None
        assert tree.is_valid_rbt()[0]
        
        # Try to delete non-existent node
        assert not tree.delete(100)
        assert len(tree) == 4
    
    def test_inorder_traversal(self):
        """Test inorder traversal"""
        tree = RedBlackTree()
        
        # Insert in random order
        insert_order = [20, 10, 30, 5, 15, 25, 35]
        for key in insert_order:
            tree.insert(key, f"data{key}")
        
        # Inorder should return sorted order
        inorder = tree.inorder_traversal()
        expected_order = sorted([f"data{key}" for key in insert_order])
        assert inorder == expected_order
    
    def test_with_reservation_data(self):
        """Test RBT with actual reservation data"""
        tree = RedBlackTree()
        reservations = []
        
        # Create reservations with different times
        for i in range(10):
            time = datetime(2024, 1, 1, 10 + i, 0)  # 10:00, 11:00, etc.
            reservation = ReservationFactory.create_reservation(
                customer_name=f"Customer{i}",
                customer_phone=f"123-456-{i:04d}",
                party_size=i % 4 + 1,
                reservation_time=time
            )
            reservations.append(reservation)
            tree.insert(reservation.rbt_key, reservation)
        
        assert len(tree) == 10
        
        # Test range search for morning (10:00 - 12:00)
        morning_start = datetime(2024, 1, 1, 10, 0).timestamp()
        morning_end = datetime(2024, 1, 1, 12, 0).timestamp()
        
        from rbtree.utils import create_time_range_keys
        start_key, end_key = create_time_range_keys(
            datetime(2024, 1, 1, 10, 0),
            datetime(2024, 1, 1, 12, 0)
        )
        
        morning_reservations = tree.search_range(start_key, end_key)
        assert len(morning_reservations) == 3  # 10:00, 11:00, 12:00
    
    def test_performance_large_dataset(self):
        """Test performance with large dataset"""
        tree = RedBlackTree()
        
        # Insert 1000 nodes
        for i in range(1000):
            tree.insert(i, f"data{i}")
        
        assert len(tree) == 1000
        
        # Verify tree properties
        is_valid, message = tree.is_valid_rbt()
        assert is_valid, message
        
        # Height should be reasonable for 1000 nodes
        height = tree.get_height()
        # RBT guarantees height <= 2*log2(n+1)
        max_expected_height = 2 * (1001).bit_length()
        assert height <= max_expected_height
        
        # Test search performance
        import time
        start = time.time()
        for i in range(100):
            tree.search(i * 10)
        end = time.time()
        
        # Should be very fast (O(log n))
        assert (end - start) < 0.1  # Less than 100ms for 100 searches
    
    def test_edge_cases(self):
        """Test edge cases"""
        tree = RedBlackTree()
        
        # Insert duplicate keys (with different data)
        tree.insert(10, "first")
        tree.insert(10, "second")  # This should work with our timestamp.id key scheme
        
        # Both should be accessible via range search
        results = tree.search_range(9, 11)
        assert len(results) == 2
        
        # Insert negative keys
        tree.insert(-5, "negative")
        assert tree.search(-5) == "negative"
        assert tree.find_min() == "negative"
        
        # Insert float keys
        tree.insert(3.14, "pi")
        tree.insert(2.71, "e")
        
        assert tree.search(3.14) == "pi"
        assert tree.search(2.71) == "e"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])