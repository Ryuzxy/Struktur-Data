"""
Table Domain Model
"""
from datetime import datetime
from enum import Enum

class TableStatus(Enum):
    """Table status enumeration"""
    AVAILABLE = "available"
    RESERVED = "reserved"
    OCCUPIED = "occupied"
    CLEANING = "cleaning"
    MAINTENANCE = "maintenance"

class Table:
    """Table entity"""
    
    def __init__(self, table_number, capacity, location="", description=""):
        """
        Initialize a table
        
        Args:
            table_number: Table number/identifier
            capacity: Maximum number of people
            location: Table location in café
            description: Additional description
        """
        self.table_number = table_number
        self.capacity = capacity
        self.location = location
        self.description = description
        self.status = TableStatus.AVAILABLE
        self.current_reservation = None
        self.current_order = None
        self.last_used = None
        self.next_available = datetime.now()
        
    def __repr__(self):
        return (f"Table({self.table_number}, cap={self.capacity}, "
                f"status={self.status.value}, loc={self.location})")
    
    def reserve(self, reservation):
        """
        Reserve table for a reservation
        
        Args:
            reservation: Reservation object
            
        Returns:
            bool: True if reserved, False if not available
        """
        if self.status != TableStatus.AVAILABLE:
            return False
            
        self.status = TableStatus.RESERVED
        self.current_reservation = reservation.id
        self.next_available = reservation.end_time
        return True
    
    def occupy(self, order):
        """
        Occupy table with an order
        
        Args:
            order: Order object
            
        Returns:
            bool: True if occupied, False if not available
        """
        if self.status == TableStatus.OCCUPIED:
            return False
            
        self.status = TableStatus.OCCUPIED
        self.current_order = order.id
        self.last_used = datetime.now()
        return True
    
    def release(self):
        """
        Release table (after order is paid)
        
        Returns:
            bool: True if released, False if already available
        """
        if self.status == TableStatus.AVAILABLE:
            return False
            
        self.status = TableStatus.CLEANING
        self.current_reservation = None
        self.current_order = None
        self.last_used = datetime.now()
        
        # Table will be available after 15 minutes cleaning
        from datetime import timedelta
        self.next_available = datetime.now() + timedelta(minutes=15)
        return True
    
    def make_available(self):
        """
        Make table available (after cleaning)
        
        Returns:
            bool: True if made available, False if already available
        """
        if self.status == TableStatus.AVAILABLE:
            return False
            
        self.status = TableStatus.AVAILABLE
        self.next_available = datetime.now()
        return True
    
    def is_available_at(self, check_time, duration_hours=2):
        """
        Check if table is available at given time
        
        Args:
            check_time: Time to check
            duration_hours: Duration needed
            
        Returns:
            bool: True if available, False otherwise
        """
        if self.status == TableStatus.MAINTENANCE:
            return False
            
        if check_time < self.next_available:
            return False
            
        return True
    
    def can_accommodate(self, party_size):
        """
        Check if table can accommodate party size
        
        Args:
            party_size: Number of people
            
        Returns:
            bool: True if can accommodate, False otherwise
        """
        return party_size <= self.capacity
    
    def to_dict(self):
        """Convert table to dictionary"""
        return {
            'table_number': self.table_number,
            'capacity': self.capacity,
            'location': self.location,
            'description': self.description,
            'status': self.status.value,
            'current_reservation': self.current_reservation,
            'current_order': self.current_order,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'next_available': self.next_available.isoformat() if self.next_available else None
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create Table from dictionary"""
        table = cls(
            table_number=data['table_number'],
            capacity=data['capacity'],
            location=data['location'],
            description=data['description']
        )
        
        table.status = TableStatus(data['status'])
        table.current_reservation = data['current_reservation']
        table.current_order = data['current_order']
        
        if data['last_used']:
            table.last_used = datetime.fromisoformat(data['last_used'])
        if data['next_available']:
            table.next_available = datetime.fromisoformat(data['next_available'])
            
        return table

class TableManager:
    """Manager for tables with RBT integration"""
    
    def __init__(self):
        self.tables = {}  # table_number -> Table object
        self._initialize_default_tables()
    
    def _initialize_default_tables(self):
        """Initialize default tables for café"""
        default_tables = [
            (1, 2, "Window", "Small table by window"),
            (2, 2, "Window", "Small table by window"),
            (3, 4, "Center", "Medium center table"),
            (4, 4, "Center", "Medium center table"),
            (5, 4, "Center", "Medium center table"),
            (6, 6, "Back", "Large family table"),
            (7, 6, "Back", "Large family table"),
            (8, 8, "Private", "Private booth"),
            (9, 8, "Private", "Private booth"),
            (10, 10, "VIP", "VIP section"),
        ]
        
        for table_num, capacity, location, desc in default_tables:
            self.tables[table_num] = Table(table_num, capacity, location, desc)
    
    def find_available_table(self, party_size, check_time, duration_hours=2):
        """
        Find available table for given party size and time
        
        Args:
            party_size: Number of people
            check_time: Reservation time
            duration_hours: Duration needed
            
        Returns:
            Table object or None if no table available
        """
        for table in self.tables.values():
            if (table.can_accommodate(party_size) and 
                table.is_available_at(check_time, duration_hours)):
                return table
        return None
    
    def get_table_status(self):
        """Get status of all tables"""
        return {num: table.to_dict() for num, table in self.tables.items()}
    
    def update_table_status(self, table_number, new_status):
        """
        Update table status
        
        Args:
            table_number: Table number
            new_status: New TableStatus
            
        Returns:
            bool: True if updated, False if table not found
        """
        if table_number not in self.tables:
            return False
            
        self.tables[table_number].status = new_status
        return True
    
    def add_table(self, table_number, capacity, location="", description=""):
        """
        Add new table
        
        Args:
            table_number: Table number
            capacity: Table capacity
            location: Table location
            description: Table description
            
        Returns:
            bool: True if added, False if table number exists
        """
        if table_number in self.tables:
            return False
            
        self.tables[table_number] = Table(table_number, capacity, location, description)
        return True
    
    def remove_table(self, table_number):
        """
        Remove table
        
        Args:
            table_number: Table number to remove
            
        Returns:
            bool: True if removed, False if not found
        """
        if table_number not in self.tables:
            return False
            
        del self.tables[table_number]
        return True