"""
Red-Black Tree Implementation with Range Search
"""
from .node import RBNode, RED, BLACK

class RedBlackTree:
    """Red-Black Tree Implementation for Time-based Operations"""
    
    def __init__(self):
        """Initialize empty Red-Black Tree"""
        self.NIL = RBNode(None)
        self.NIL.color = BLACK
        self.NIL.left = None
        self.NIL.right = None
        self.root = self.NIL
        self.size = 0
        
    def __len__(self):
        """Return number of nodes in tree"""
        return self.size
    
    def is_empty(self):
        """Check if tree is empty"""
        return self.root == self.NIL
    
    # -------------------- Core Operations --------------------
    
    def insert(self, key, data):
        """
        Insert a node with given key and data
        
        Args:
            key: Comparable key
            data: Associated data object
            
        Returns:
            The inserted node
        """
        new_node = RBNode(key, data)
        new_node.left = self.NIL
        new_node.right = self.NIL
        
        # Regular BST insert
        parent = None
        current = self.root
        
        while current != self.NIL:
            parent = current
            if new_node.key < current.key:
                current = current.left
            else:
                current = current.right
                
        new_node.parent = parent
        
        if parent is None:
            self.root = new_node
        elif new_node.key < parent.key:
            parent.left = new_node
        else:
            parent.right = new_node
            
        self.size += 1
        
        # Fix Red-Black Tree violations
        self._fix_insert(new_node)
        return new_node
    
    def _fix_insert(self, node):
        """Fix Red-Black Tree properties after insertion"""
        while node != self.root and node.parent.color == RED:
            if node.parent.is_left_child():
                uncle = node.parent.parent.right
                
                # Case 1: Uncle is red
                if uncle.color == RED:
                    node.parent.color = BLACK
                    uncle.color = BLACK
                    node.parent.parent.color = RED
                    node = node.parent.parent
                else:
                    # Case 2: Node is right child
                    if node.is_right_child():
                        node = node.parent
                        self._left_rotate(node)
                    
                    # Case 3: Node is left child
                    node.parent.color = BLACK
                    node.parent.parent.color = RED
                    self._right_rotate(node.parent.parent)
            else:
                # Symmetric cases for right child
                uncle = node.parent.parent.left
                
                if uncle.color == RED:
                    node.parent.color = BLACK
                    uncle.color = BLACK
                    node.parent.parent.color = RED
                    node = node.parent.parent
                else:
                    if node.is_left_child():
                        node = node.parent
                        self._right_rotate(node)
                    
                    node.parent.color = BLACK
                    node.parent.parent.color = RED
                    self._left_rotate(node.parent.parent)
                    
        self.root.color = BLACK
    
    # -------------------- Rotation Operations --------------------
    
    def _left_rotate(self, x):
        """Left rotation at node x"""
        y = x.right
        x.right = y.left
        
        if y.left != self.NIL:
            y.left.parent = x
            
        y.parent = x.parent
        
        if x.parent is None:
            self.root = y
        elif x.is_left_child():
            x.parent.left = y
        else:
            x.parent.right = y
            
        y.left = x
        x.parent = y
    
    def _right_rotate(self, y):
        """Right rotation at node y"""
        x = y.left
        y.left = x.right
        
        if x.right != self.NIL:
            x.right.parent = y
            
        x.parent = y.parent
        
        if y.parent is None:
            self.root = x
        elif y.is_right_child():
            y.parent.right = x
        else:
            y.parent.left = x
            
        x.right = y
        y.parent = x
    
    # -------------------- Search Operations --------------------
    
    def search(self, key):
        """
        Search for a node with given key
        
        Args:
            key: Key to search for
            
        Returns:
            Node data if found, None otherwise
        """
        node = self._search_node(key)
        return node.data if node != self.NIL else None
    
    def _search_node(self, key):
        """Internal method to search for a node"""
        current = self.root
        
        while current != self.NIL:
            if key == current.key:
                return current
            elif key < current.key:
                current = current.left
            else:
                current = current.right
                
        return self.NIL
    
    def search_range(self, start_key, end_key):
        """
        Search for all nodes with keys in range [start_key, end_key]
        
        Args:
            start_key: Start of range (inclusive)
            end_key: End of range (inclusive)
            
        Returns:
            List of data objects in range
        """
        results = []
        self._search_range_helper(self.root, start_key, end_key, results)
        return results
    
    def _search_range_helper(self, node, start, end, results):
        """Recursive helper for range search"""
        if node == self.NIL:
            return
            
        # If node's key is greater than start, search left subtree
        if node.key > start:
            self._search_range_helper(node.left, start, end, results)
            
        # If node's key is in range, add to results
        if start <= node.key <= end:
            results.append(node.data)
            
        # If node's key is less than end, search right subtree
        if node.key < end:
            self._search_range_helper(node.right, start, end, results)
    
    def find_min(self):
        """Find node with minimum key"""
        if self.root == self.NIL:
            return None
            
        current = self.root
        while current.left != self.NIL:
            current = current.left
            
        return current.data
    
    def find_max(self):
        """Find node with maximum key"""
        if self.root == self.NIL:
            return None
            
        current = self.root
        while current.right != self.NIL:
            current = current.right
            
        return current.data
    
    # -------------------- Delete Operations --------------------
    
    def delete(self, key):
        """
        Delete node with given key
        
        Args:
            key: Key of node to delete
            
        Returns:
            True if deleted, False if not found
        """
        node = self._search_node(key)
        if node == self.NIL:
            return False
            
        self._delete_node(node)
        self.size -= 1
        return True
    
    def _delete_node(self, z):
        """Internal method to delete a node"""
        y = z
        y_original_color = y.color
        
        if z.left == self.NIL:
            x = z.right
            self._transplant(z, z.right)
        elif z.right == self.NIL:
            x = z.left
            self._transplant(z, z.left)
        else:
            y = self._minimum(z.right)
            y_original_color = y.color
            x = y.right
            
            if y.parent == z:
                x.parent = y
            else:
                self._transplant(y, y.right)
                y.right = z.right
                y.right.parent = y
                
            self._transplant(z, y)
            y.left = z.left
            y.left.parent = y
            y.color = z.color
            
        if y_original_color == BLACK:
            self._fix_delete(x)
    
    def _transplant(self, u, v):
        """Replace subtree rooted at u with subtree rooted at v"""
        if u.parent is None:
            self.root = v
        elif u.is_left_child():
            u.parent.left = v
        else:
            u.parent.right = v
            
        v.parent = u.parent
    
    def _minimum(self, node):
        """Find minimum node in subtree"""
        while node.left != self.NIL:
            node = node.left
        return node
    
    def _fix_delete(self, x):
        """Fix Red-Black Tree properties after deletion"""
        while x != self.root and x.color == BLACK:
            if x.is_left_child():
                w = x.parent.right
                
                # Case 1: Sibling is red
                if w.color == RED:
                    w.color = BLACK
                    x.parent.color = RED
                    self._left_rotate(x.parent)
                    w = x.parent.right
                
                # Case 2: Both sibling's children are black
                if w.left.color == BLACK and w.right.color == BLACK:
                    w.color = RED
                    x = x.parent
                else:
                    # Case 3: Sibling's right child is black
                    if w.right.color == BLACK:
                        w.left.color = BLACK
                        w.color = RED
                        self._right_rotate(w)
                        w = x.parent.right
                    
                    # Case 4: Sibling's right child is red
                    w.color = x.parent.color
                    x.parent.color = BLACK
                    w.right.color = BLACK
                    self._left_rotate(x.parent)
                    x = self.root
            else:
                # Symmetric cases for right child
                w = x.parent.left
                
                if w.color == RED:
                    w.color = BLACK
                    x.parent.color = RED
                    self._right_rotate(x.parent)
                    w = x.parent.left
                
                if w.right.color == BLACK and w.left.color == BLACK:
                    w.color = RED
                    x = x.parent
                else:
                    if w.left.color == BLACK:
                        w.right.color = BLACK
                        w.color = RED
                        self._left_rotate(w)
                        w = x.parent.left
                    
                    w.color = x.parent.color
                    x.parent.color = BLACK
                    w.left.color = BLACK
                    self._right_rotate(x.parent)
                    x = self.root
                    
        x.color = BLACK
    
    # -------------------- Traversal Operations --------------------
    
    def inorder_traversal(self):
        """In-order traversal of tree"""
        result = []
        self._inorder_helper(self.root, result)
        return result
    
    def _inorder_helper(self, node, result):
        """Recursive helper for in-order traversal"""
        if node == self.NIL:
            return
            
        self._inorder_helper(node.left, result)
        result.append(node.data)
        self._inorder_helper(node.right, result)
    
    def preorder_traversal(self):
        """Pre-order traversal of tree"""
        result = []
        self._preorder_helper(self.root, result)
        return result
    
    def _preorder_helper(self, node, result):
        """Recursive helper for pre-order traversal"""
        if node == self.NIL:
            return
            
        result.append(node.data)
        self._preorder_helper(node.left, result)
        self._inorder_helper(node.right, result)
    
    # -------------------- Utility Methods --------------------
    
    def get_height(self):
        """Get height of tree"""
        return self._get_height(self.root)
    
    def _get_height(self, node):
        """Recursively calculate height"""
        if node == self.NIL:
            return 0
            
        left_height = self._get_height(node.left)
        right_height = self._get_height(node.right)
        
        return max(left_height, right_height) + 1
    
    def is_valid_rbt(self):
        """Validate Red-Black Tree properties"""
        # Property 1: Root is black
        if self.root.color != BLACK:
            return False, "Root is not black"
            
        # Property 2: No red-red parent-child
        if not self._check_red_property(self.root):
            return False, "Red-red parent-child violation"
            
        # Property 3: All paths have same black height
        black_height, valid = self._check_black_height(self.root)
        if not valid:
            return False, f"Black height violation: {black_height}"
            
        return True, "Valid Red-Black Tree"
    
    def _check_red_property(self, node):
        """Check no red node has red children"""
        if node == self.NIL:
            return True
            
        if node.color == RED:
            if node.left.color == RED or node.right.color == RED:
                return False
                
        return (self._check_red_property(node.left) and 
                self._check_red_property(node.right))
    
    def _check_black_height(self, node):
        """Check black height consistency"""
        if node == self.NIL:
            return 1, True
            
        left_bh, left_valid = self._check_black_height(node.left)
        right_bh, right_valid = self._check_black_height(node.right)
        
        if not left_valid or not right_valid or left_bh != right_bh:
            return max(left_bh, right_bh), False
            
        bh = left_bh
        if node.color == BLACK:
            bh += 1
            
        return bh, True
    
    def to_dict(self):
        """Convert tree to dictionary for serialization"""
        return self._to_dict_helper(self.root)
    
    def _to_dict_helper(self, node):
        """Recursive helper for dict conversion"""
        if node == self.NIL:
            return None
            
        return {
            'key': node.key,
            'data': node.data.to_dict() if hasattr(node.data, 'to_dict') else str(node.data),
            'color': 'RED' if node.color == RED else 'BLACK',
            'left': self._to_dict_helper(node.left),
            'right': self._to_dict_helper(node.right)
        }
    
    def print_tree(self):
        """Print tree structure (for debugging)"""
        self._print_helper(self.root, "", True)
    
    def _print_helper(self, node, indent, last):
        """Recursive helper for tree printing"""
        if node != self.NIL:
            print(indent, end="")
            if last:
                print("R----", end="")
                indent += "     "
            else:
                print("L----", end="")
                indent += "|    "
                
            color = "RED" if node.color == RED else "BLACK"
            print(f"{node.key}({color})")
            self._print_helper(node.left, indent, False)
            self._print_helper(node.right, indent, True)