"""
Red-Black Tree Node Implementation
"""
RED = True
BLACK = False

class RBNode:
    """Node for Red-Black Tree"""
    
    def __init__(self, key, data=None):
        """
        Initialize a Red-Black Tree node
        
        Args:
            key: Comparable key for ordering (timestamp + id)
            data: Associated data (Reservation/Order object)
        """
        self.key = key
        self.data = data
        self.color = RED  # New nodes are always red
        self.left = None
        self.right = None
        self.parent = None
        
    def __repr__(self):
        color_str = "RED" if self.color == RED else "BLACK"
        return f"RBNode(key={self.key}, color={color_str}, data={self.data})"
    
    def is_red(self):
        """Check if node is red"""
        return self.color == RED
    
    def is_black(self):
        """Check if node is black"""
        return self.color == BLACK
    
    def flip_color(self):
        """Flip node color"""
        self.color = not self.color
        
    def get_sibling(self):
        """Get sibling node"""
        if self.parent is None:
            return None
            
        if self == self.parent.left:
            return self.parent.right
        return self.parent.left
    
    def get_uncle(self):
        """Get uncle node (parent's sibling)"""
        if self.parent is None or self.parent.parent is None:
            return None
        return self.parent.get_sibling()
    
    def is_left_child(self):
        """Check if node is left child of its parent"""
        if self.parent is None:
            return False
        return self == self.parent.left
    
    def is_right_child(self):
        """Check if node is right child of its parent"""
        if self.parent is None:
            return False
        return self == self.parent.right