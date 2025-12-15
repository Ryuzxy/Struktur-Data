"""
Reservation Domain Model
"""
from datetime import datetime, timedelta
import uuid

class Reservation:
    """Reservation entity with RBT integration"""
    
    def __init__(self, reservation_id, customer_name, customer_phone,
                 party_size, reservation_time, duration_hours=2,
                 table_number=None, special_requests=""):
        """
        Initialize a reservation
        
        Args:
            reservation_id: Unique identifier
            customer_name: Customer name
            customer_phone: Customer phone number
            party_size: Number of people
            reservation_time: Datetime of reservation
            duration_hours: Reservation duration in hours (default 2)
            table_number: Assigned table number
            special_requests: Special requests from customer
        """
        self.id = reservation_id
        self.customer_name = customer_name
        self.customer_phone = customer_phone
        self.party_size = party_size
        self.reservation_time = reservation_time
        self.duration_hours = duration_hours
        self.duration = timedelta(hours=duration_hours)
        self.end_time = reservation_time + self.duration
        self.table_number = table_number
        self.special_requests = special_requests
        self.status = "confirmed"  # confirmed, cancelled, completed
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # RBT key for efficient searching
        # Format: timestamp + unique_id to ensure uniqueness
        timestamp = reservation_time.timestamp()
        # Convert reservation_id to integer hash for modulo operation
        id_hash = hash(reservation_id) % 1000
        # Combine as single float: timestamp.idhash (e.g., 1765947600852)
        self.rbt_key = float(int(timestamp * 1000) + id_hash)
        
    def __repr__(self):
        return (f"Reservation(id={self.id}, customer={self.customer_name}, "
                f"time={self.reservation_time.strftime('%Y-%m-%d %H:%M')}, "
                f"party={self.party_size}, status={self.status})")
    
    def conflicts_with(self, other_reservation):
        """
        Check if this reservation conflicts with another
        
        Args:
            other_reservation: Another Reservation object
            
        Returns:
            bool: True if conflicts, False otherwise
        """
        # Two reservations conflict if their time intervals overlap
        # and they might be for the same table (or table not assigned yet)
        return (self.reservation_time < other_reservation.end_time and 
                self.end_time > other_reservation.reservation_time)
    
    def is_active_at(self, check_time):
        """
        Check if reservation is active at given time
        
        Args:
            check_time: Datetime to check
            
        Returns:
            bool: True if active, False otherwise
        """
        return self.reservation_time <= check_time <= self.end_time
    
    def get_time_interval(self):
        """
        Get time interval as tuple
        
        Returns:
            Tuple of (start_time, end_time)
        """
        return (self.reservation_time, self.end_time)
    
    def to_dict(self):
        """
        Convert reservation to dictionary
        
        Returns:
            dict: Dictionary representation
        """
        return {
            'id': str(self.id),
            'customer_name': str(self.customer_name),
            'customer_phone': str(self.customer_phone),
            'party_size': int(self.party_size),
            'reservation_time': self.reservation_time.isoformat(),
            'duration_hours': int(self.duration_hours),
            'end_time': self.end_time.isoformat(),
            'table_number': int(self.table_number) if self.table_number else None,
            'special_requests': str(self.special_requests),
            'status': str(self.status),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'rbt_key': float(self.rbt_key)
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Create reservation from dictionary
        
        Args:
            data: Dictionary with reservation data
            
        Returns:
            Reservation object
        """
        return cls(
            reservation_id=data['id'],
            customer_name=data['customer_name'],
            customer_phone=data['customer_phone'],
            party_size=int(data['party_size']),
            reservation_time=datetime.fromisoformat(data['reservation_time']),
            duration_hours=int(data.get('duration_hours', 2)),
            table_number=int(data['table_number']) if data.get('table_number') else None,
            special_requests=data.get('special_requests', '')
        )
    
    def update_status(self, new_status):
        """
        Update reservation status
        
        Args:
            new_status: New status (confirmed, cancelled, completed)
        """
        valid_statuses = ['confirmed', 'cancelled', 'completed']
        if new_status not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
            
        self.status = new_status
        self.updated_at = datetime.now()
    
    def assign_table(self, table_number):
        """
        Assign table to reservation
        
        Args:
            table_number: Table number to assign
        """
        self.table_number = table_number
        self.updated_at = datetime.now()

class ReservationFactory:
    """Factory for creating reservations"""
    
    @staticmethod
    def create_reservation(customer_name, customer_phone, party_size,
                          reservation_time, duration_hours=2, **kwargs):
        """
        Create a new reservation with auto-generated ID
        
        Args:
            customer_name: Customer name
            customer_phone: Customer phone
            party_size: Number of people
            reservation_time: Reservation datetime
            duration_hours: Duration in hours
            **kwargs: Additional arguments
            
        Returns:
            Reservation object
        """
        reservation_id = str(uuid.uuid4())[:8]  # Short unique ID
        return Reservation(
            reservation_id=reservation_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            party_size=party_size,
            reservation_time=reservation_time,
            duration_hours=duration_hours,
            **kwargs
        )
    
    @staticmethod
    def validate_reservation_data(customer_name, party_size, reservation_time):
        """
        Validate reservation data
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not customer_name or len(customer_name.strip()) < 2:
            return False, "Customer name must be at least 2 characters"
            
        if not isinstance(party_size, int) or party_size < 1 or party_size > 20:
            return False, "Party size must be between 1 and 20"
            
        if not isinstance(reservation_time, datetime):
            return False, "Reservation time must be a datetime object"
            
        if reservation_time < datetime.now():
            return False, "Reservation time cannot be in the past"
            
        return True, "Valid reservation data"