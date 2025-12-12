"""
Reservation Repository with RBT integration
"""
import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from domain.reservation import Reservation
from rbtree.rbtree import RedBlackTree

class ReservationRepository:
    """Repository for managing reservations with RBT"""
    
    def __init__(self, storage_file="data/reservations.json"):
        """
        Initialize repository
        
        Args:
            storage_file: File to persist reservations
        """
        self.storage_file = storage_file
        self.reservations: Dict[str, Reservation] = {}  # id -> Reservation
        self.rbtree = RedBlackTree()
        self._load_from_storage()
    
    def _load_from_storage(self):
        """Load reservations from storage file"""
        try:
            Path(self.storage_file).parent.mkdir(parents=True, exist_ok=True)
            
            if Path(self.storage_file).exists():
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    
                for reservation_data in data:
                    reservation = Reservation.from_dict(reservation_data)
                    self.reservations[reservation.id] = reservation
                    self.rbtree.insert(reservation.rbt_key, reservation)
                    
                print(f"Loaded {len(self.reservations)} reservations from storage")
        except Exception as e:
            print(f"Error loading reservations: {e}")
            # Start with empty repository
    
    def _save_to_storage(self):
        """Save reservations to storage file"""
        try:
            data = [res.to_dict() for res in self.reservations.values()]
            
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving reservations: {e}")
    
    def add(self, reservation: Reservation) -> bool:
        """
        Add new reservation
        
        Args:
            reservation: Reservation object
            
        Returns:
            bool: True if added, False if duplicate
        """
        if reservation.id in self.reservations:
            return False
            
        self.reservations[reservation.id] = reservation
        self.rbtree.insert(reservation.rbt_key, reservation)
        self._save_to_storage()
        return True
    
    def get(self, reservation_id: str) -> Optional[Reservation]:
        """
        Get reservation by ID
        
        Args:
            reservation_id: Reservation ID
            
        Returns:
            Reservation or None if not found
        """
        return self.reservations.get(reservation_id)
    
    def get_by_customer(self, customer_name: str) -> List[Reservation]:
        """
        Get reservations by customer name
        
        Args:
            customer_name: Customer name
            
        Returns:
            List of reservations
        """
        return [r for r in self.reservations.values() 
                if r.customer_name.lower() == customer_name.lower()]
    
    def get_by_date(self, date: datetime) -> List[Reservation]:
        """
        Get reservations for specific date
        
        Args:
            date: Date to filter
            
        Returns:
            List of reservations on that date
        """
        # Create time range for the entire day
        start_time = datetime.combine(date, datetime.min.time())
        end_time = datetime.combine(date, datetime.max.time())
        
        return self.get_by_time_range(start_time, end_time)
    
    def get_by_time_range(self, start_time: datetime, end_time: datetime) -> List[Reservation]:
        """
        Get reservations in time range using RBT
        
        Args:
            start_time: Start time
            end_time: End time
            
        Returns:
            List of reservations in range
        """
        # Convert to RBT keys
        from rbtree.utils import create_time_range_keys
        start_key, end_key = create_time_range_keys(start_time, end_time)
        
        # Use RBT range search for O(log n + k) performance
        return self.rbtree.search_range(start_key, end_key)
    
    def get_conflicting_reservations(self, reservation: Reservation) -> List[Reservation]:
        """
        Get reservations that conflict with given reservation
        
        Args:
            reservation: Reservation to check
            
        Returns:
            List of conflicting reservations
        """
        # Get all reservations in the time range
        candidates = self.get_by_time_range(
            reservation.reservation_time,
            reservation.end_time
        )
        
        # Filter for actual conflicts
        conflicts = []
        for candidate in candidates:
            if candidate.id != reservation.id and reservation.conflicts_with(candidate):
                conflicts.append(candidate)
                
        return conflicts
    
    def update(self, reservation: Reservation) -> bool:
        """
        Update existing reservation
        
        Args:
            reservation: Updated reservation
            
        Returns:
            bool: True if updated, False if not found
        """
        if reservation.id not in self.reservations:
            return False
            
        # Remove old entry from RBT
        old_reservation = self.reservations[reservation.id]
        self.rbtree.delete(old_reservation.rbt_key)
        
        # Update and re-insert
        self.reservations[reservation.id] = reservation
        self.rbtree.insert(reservation.rbt_key, reservation)
        self._save_to_storage()
        return True
    
    def delete(self, reservation_id: str) -> bool:
        """
        Delete reservation
        
        Args:
            reservation_id: Reservation ID to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        if reservation_id not in self.reservations:
            return False
            
        reservation = self.reservations[reservation_id]
        self.rbtree.delete(reservation.rbt_key)
        del self.reservations[reservation_id]
        self._save_to_storage()
        return True
    
    def get_all(self) -> List[Reservation]:
        """
        Get all reservations
        
        Returns:
            List of all reservations
        """
        return list(self.reservations.values())
    
    def get_active_reservations(self) -> List[Reservation]:
        """
        Get active (confirmed) reservations
        
        Returns:
            List of active reservations
        """
        now = datetime.now()
        active = []
        
        for reservation in self.reservations.values():
            if (reservation.status == "confirmed" and 
                reservation.reservation_time <= now <= reservation.end_time):
                active.append(reservation)
                
        return active
    
    def get_upcoming_reservations(self, hours_ahead: int = 24) -> List[Reservation]:
        """
        Get upcoming reservations
        
        Args:
            hours_ahead: Hours to look ahead
            
        Returns:
            List of upcoming reservations
        """
        now = datetime.now()
        end_time = now.replace(hour=23, minute=59, second=59)
        
        upcoming = []
        for reservation in self.reservations.values():
            if (reservation.status == "confirmed" and 
                now <= reservation.reservation_time <= end_time):
                upcoming.append(reservation)
                
        return sorted(upcoming, key=lambda r: r.reservation_time)
    
    def cancel_reservation(self, reservation_id: str) -> bool:
        """
        Cancel reservation
        
        Args:
            reservation_id: Reservation ID to cancel
            
        Returns:
            bool: True if cancelled, False if not found
        """
        if reservation_id not in self.reservations:
            return False
            
        reservation = self.reservations[reservation_id]
        reservation.update_status("cancelled")
        self._save_to_storage()
        return True
    
    def get_statistics(self) -> dict:
        """
        Get reservation statistics
        
        Returns:
            Dictionary with statistics
        """
        total = len(self.reservations)
        confirmed = sum(1 for r in self.reservations.values() 
                       if r.status == "confirmed")
        cancelled = sum(1 for r in self.reservations.values() 
                       if r.status == "cancelled")
        completed = sum(1 for r in self.reservations.values() 
                       if r.status == "completed")
        
        # Average party size
        if total > 0:
            avg_party = sum(r.party_size for r in self.reservations.values()) / total
        else:
            avg_party = 0
            
        # Today's reservations
        today = datetime.now().date()
        today_reservations = self.get_by_date(today)
        
        return {
            'total_reservations': total,
            'confirmed': confirmed,
            'cancelled': cancelled,
            'completed': completed,
            'average_party_size': round(avg_party, 1),
            'today_count': len(today_reservations),
            'rbt_size': len(self.rbtree),
            'rbt_height': self.rbtree.get_height()
        }
    
    def export_tree_structure(self) -> dict:
        """
        Export RBT structure for visualization
        
        Returns:
            Dictionary representation of RBT
        """
        return self.rbtree.to_dict()