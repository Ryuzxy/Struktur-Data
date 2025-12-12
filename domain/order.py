"""
Order Domain Model
"""
from datetime import datetime
import uuid
from enum import Enum

class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"
    PREPARING = "preparing"
    READY = "ready"
    SERVED = "served"
    CANCELLED = "cancelled"
    PAID = "paid"

class OrderItem:
    """Individual item in an order"""
    
    def __init__(self, item_id, name, quantity, price, category=""):
        self.item_id = item_id
        self.name = name
        self.quantity = quantity
        self.price = price
        self.category = category
        self.subtotal = quantity * price
        
    def to_dict(self):
        return {
            'item_id': self.item_id,
            'name': self.name,
            'quantity': self.quantity,
            'price': self.price,
            'category': self.category,
            'subtotal': self.subtotal
        }

class Order:
    """Order entity with RBT integration for time-based queries"""
    
    def __init__(self, order_id, table_number, customer_name="Walk-in"):
        """
        Initialize an order
        
        Args:
            order_id: Unique order identifier
            table_number: Table number
            customer_name: Customer name (default: Walk-in)
        """
        self.id = order_id
        self.table_number = table_number
        self.customer_name = customer_name
        self.items = []
        self.status = OrderStatus.PENDING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.total_amount = 0.0
        self.paid_amount = 0.0
        self.reservation_id = None
        
        # RBT key for efficient time-based queries
        timestamp = self.created_at.timestamp()
        self.rbt_key = float(f"{timestamp}.{order_id % 1000:03d}")
        
    def __repr__(self):
        return (f"Order(id={self.id}, table={self.table_number}, "
                f"status={self.status.value}, total={self.total_amount})")
    
    def add_item(self, item_id, name, quantity, price, category=""):
        """
        Add item to order
        
        Args:
            item_id: Item identifier
            name: Item name
            quantity: Quantity
            price: Unit price
            category: Item category
        """
        item = OrderItem(item_id, name, quantity, price, category)
        self.items.append(item)
        self._update_totals()
        self.updated_at = datetime.now()
        
    def remove_item(self, item_id):
        """
        Remove item from order
        
        Args:
            item_id: Item identifier to remove
            
        Returns:
            bool: True if removed, False if not found
        """
        for i, item in enumerate(self.items):
            if item.item_id == item_id:
                self.items.pop(i)
                self._update_totals()
                self.updated_at = datetime.now()
                return True
        return False
    
    def update_item_quantity(self, item_id, new_quantity):
        """
        Update item quantity
        
        Args:
            item_id: Item identifier
            new_quantity: New quantity
            
        Returns:
            bool: True if updated, False if not found
        """
        for item in self.items:
            if item.item_id == item_id:
                item.quantity = new_quantity
                item.subtotal = new_quantity * item.price
                self._update_totals()
                self.updated_at = datetime.now()
                return True
        return False
    
    def _update_totals(self):
        """Update order totals"""
        self.total_amount = sum(item.subtotal for item in self.items)
        
    def update_status(self, new_status):
        """
        Update order status
        
        Args:
            new_status: New OrderStatus
        """
        if not isinstance(new_status, OrderStatus):
            raise ValueError("Status must be OrderStatus enum")
            
        self.status = new_status
        self.updated_at = datetime.now()
        
        # Auto-pay if served for more than 30 minutes
        if (new_status == OrderStatus.SERVED and 
            (datetime.now() - self.created_at).seconds > 1800):
            self.status = OrderStatus.PAID
    
    def add_payment(self, amount):
        """
        Add payment to order
        
        Args:
            amount: Payment amount
            
        Returns:
            float: Change amount (negative if insufficient)
        """
        self.paid_amount += amount
        change = amount - (self.total_amount - self.paid_amount)
        
        if self.paid_amount >= self.total_amount:
            self.status = OrderStatus.PAID
            
        self.updated_at = datetime.now()
        return change
    
    def is_paid(self):
        """Check if order is fully paid"""
        return self.status == OrderStatus.PAID or self.paid_amount >= self.total_amount
    
    def get_summary(self):
        """Get order summary"""
        return {
            'order_id': self.id,
            'table_number': self.table_number,
            'customer_name': self.customer_name,
            'item_count': len(self.items),
            'total_amount': self.total_amount,
            'paid_amount': self.paid_amount,
            'status': self.status.value,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }
    
    def to_dict(self):
        """Convert order to dictionary"""
        return {
            'id': self.id,
            'table_number': self.table_number,
            'customer_name': self.customer_name,
            'items': [item.to_dict() for item in self.items],
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'total_amount': self.total_amount,
            'paid_amount': self.paid_amount,
            'reservation_id': self.reservation_id,
            'rbt_key': self.rbt_key
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create Order from dictionary"""
        order = cls(
            order_id=data['id'],
            table_number=data['table_number'],
            customer_name=data['customer_name']
        )
        
        order.items = [OrderItem(**item) for item in data['items']]
        order.status = OrderStatus(data['status'])
        order.created_at = datetime.fromisoformat(data['created_at'])
        order.updated_at = datetime.fromisoformat(data['updated_at'])
        order.total_amount = data['total_amount']
        order.paid_amount = data['paid_amount']
        order.reservation_id = data['reservation_id']
        
        return order

class OrderFactory:
    """Factory for creating orders"""
    
    @staticmethod
    def create_order(table_number, customer_name="Walk-in"):
        """
        Create a new order
        
        Args:
            table_number: Table number
            customer_name: Customer name
            
        Returns:
            Order object
        """
        order_id = str(uuid.uuid4())[:8]
        return Order(order_id, table_number, customer_name)
    
    @staticmethod
    def create_from_reservation(reservation):
        """
        Create order from reservation
        
        Args:
            reservation: Reservation object
            
        Returns:
            Order object
        """
        order = OrderFactory.create_order(
            table_number=reservation.table_number,
            customer_name=reservation.customer_name
        )
        order.reservation_id = reservation.id
        return order