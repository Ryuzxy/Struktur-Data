"""
Reservation Service with RBT optimization
"""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict

from domain.reservation import Reservation, ReservationFactory
from domain.table import TableManager
from repositories.reservation_repo import ReservationRepository
from rbtree.rbtree import RedBlackTree
from rbtree.utils import generate_rbt_key
import config

class ReservationService:
    """Service layer for reservation operations"""
    
    def __init__(self):
        self.repository = ReservationRepository()
        self.table_manager = TableManager()
        self.rbt_stats = {
            'insert_count': 0,
            'search_count': 0,
            'range_search_count': 0,
            'delete_count': 0
        }
    
    # -------------------- Core Reservation Operations --------------------
    
    def create_reservation(self, customer_name: str, customer_phone: str,
                          party_size: int, reservation_time: datetime,
                          duration_hours: int = 2, special_requests: str = "") -> Tuple[bool, str, Optional[Reservation]]:
        """
        Create new reservation with conflict checking
        
        Args:
            customer_name: Customer name
            customer_phone: Customer phone
            party_size: Number of people
            reservation_time: Reservation datetime
            duration_hours: Duration in hours
            special_requests: Special requests
            
        Returns:
            Tuple of (success, message, reservation)
        """
        # Validate inputs
        is_valid, error_msg = ReservationFactory.validate_reservation_data(
            customer_name, party_size, reservation_time
        )
        if not is_valid:
            return False, error_msg, None
        
        # Check business hours
        if not self._is_within_business_hours(reservation_time, duration_hours):
            return False, "Reservation outside business hours", None
        
        # Create reservation
        reservation = ReservationFactory.create_reservation(
            customer_name=customer_name,
            customer_phone=customer_phone,
            party_size=party_size,
            reservation_time=reservation_time,
            duration_hours=duration_hours,
            special_requests=special_requests
        )
        
        # Find available table
        table = self.table_manager.find_available_table(
            party_size, reservation_time, duration_hours
        )
        
        if table:
            reservation.assign_table(table.table_number)
            table.reserve(reservation)
        else:
            # Try to find any available table (even if slightly over capacity)
            for t in self.table_manager.tables.values():
                if (t.is_available_at(reservation_time, duration_hours) and 
                    party_size <= t.capacity + 2):  # Allow slight overflow
                    reservation.assign_table(t.table_number)
                    t.reserve(reservation)
                    break
            else:
                return False, "No tables available for the requested time", None
        
        # Check for conflicts using RBT
        conflicts = self.repository.get_conflicting_reservations(reservation)
        if conflicts:
            # Check if conflicts are for same table
            same_table_conflicts = [c for c in conflicts 
                                   if c.table_number == reservation.table_number]
            if same_table_conflicts:
                return False, f"Table {reservation.table_number} already reserved for this time", None
        
        # Save reservation
        if self.repository.add(reservation):
            self.rbt_stats['insert_count'] += 1
            return True, "Reservation created successfully", reservation
        else:
            return False, "Failed to create reservation", None
    
    def get_reservation(self, reservation_id: str) -> Optional[Reservation]:
        """
        Get reservation by ID
        
        Args:
            reservation_id: Reservation ID
            
        Returns:
            Reservation or None
        """
        self.rbt_stats['search_count'] += 1
        return self.repository.get(reservation_id)
    
    def update_reservation(self, reservation_id: str, **kwargs) -> Tuple[bool, str]:
        """
        Update reservation
        
        Args:
            reservation_id: Reservation ID
            **kwargs: Fields to update
            
        Returns:
            Tuple of (success, message)
        """
        reservation = self.repository.get(reservation_id)
        if not reservation:
            return False, "Reservation not found"
        
        # Check if updating time or duration
        if 'reservation_time' in kwargs or 'duration_hours' in kwargs:
            new_time = kwargs.get('reservation_time', reservation.reservation_time)
            new_duration = kwargs.get('duration_hours', reservation.duration_hours)
            
            # Check for conflicts with new time
            temp_reservation = Reservation(
                reservation_id=reservation.id,
                customer_name=reservation.customer_name,
                customer_phone=reservation.customer_phone,
                party_size=reservation.party_size,
                reservation_time=new_time,
                duration_hours=new_duration,
                table_number=reservation.table_number,
                special_requests=reservation.special_requests
            )
            
            conflicts = self.repository.get_conflicting_reservations(temp_reservation)
            # Filter out self
            conflicts = [c for c in conflicts if c.id != reservation_id]
            
            if conflicts:
                same_table_conflicts = [c for c in conflicts 
                                       if c.table_number == reservation.table_number]
                if same_table_conflicts:
                    return False, "New time conflicts with existing reservation"
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(reservation, key):
                setattr(reservation, key, value)
        
        reservation.updated_at = datetime.now()
        
        # Update RBT key if time changed
        if 'reservation_time' in kwargs:
            reservation.rbt_key = generate_rbt_key(
                reservation.reservation_time, 
                int(reservation.id) if reservation.id.isdigit() else hash(reservation.id) % 1000
            )
        
        if self.repository.update(reservation):
            return True, "Reservation updated successfully"
        else:
            return False, "Failed to update reservation"
    
    def cancel_reservation(self, reservation_id: str) -> Tuple[bool, str]:
        """
        Cancel reservation
        
        Args:
            reservation_id: Reservation ID
            
        Returns:
            Tuple of (success, message)
        """
        self.rbt_stats['delete_count'] += 1
        
        if self.repository.cancel_reservation(reservation_id):
            # Release table
            reservation = self.repository.get(reservation_id)
            if reservation and reservation.table_number:
                table = self.table_manager.tables.get(reservation.table_number)
                if table:
                    table.release()
            
            return True, "Reservation cancelled successfully"
        else:
            return False, "Reservation not found"
    
    # -------------------- Query Operations --------------------
    
    def get_reservations_by_date(self, date: datetime) -> List[Reservation]:
        """
        Get reservations for specific date using RBT
        
        Args:
            date: Date to query
            
        Returns:
            List of reservations
        """
        self.rbt_stats['range_search_count'] += 1
        return self.repository.get_by_date(date)
    
    def get_reservations_by_customer(self, customer_name: str) -> List[Reservation]:
        """
        Get reservations by customer name
        
        Args:
            customer_name: Customer name
            
        Returns:
            List of reservations
        """
        return self.repository.get_by_customer(customer_name)
    
    def get_reservations_by_time_range(self, start_time: datetime, 
                                      end_time: datetime) -> List[Reservation]:
        """
        Get reservations in time range using RBT
        
        Args:
            start_time: Start time
            end_time: End time
            
        Returns:
            List of reservations
        """
        self.rbt_stats['range_search_count'] += 1
        return self.repository.get_by_time_range(start_time, end_time)
    
    def get_upcoming_reservations(self, hours_ahead: int = 24) -> List[Reservation]:
        """
        Get upcoming reservations
        
        Args:
            hours_ahead: Hours to look ahead
            
        Returns:
            List of upcoming reservations
        """
        return self.repository.get_upcoming_reservations(hours_ahead)
    
    def get_active_reservations(self) -> List[Reservation]:
        """
        Get currently active reservations
        
        Returns:
            List of active reservations
        """
        return self.repository.get_active_reservations()
    
    # -------------------- Table Management --------------------
    
    def find_available_tables(self, party_size: int, reservation_time: datetime,
                             duration_hours: int = 2) -> List[Dict]:
        """
        Find available tables for given criteria
        
        Args:
            party_size: Number of people
            reservation_time: Desired time
            duration_hours: Duration needed
            
        Returns:
            List of available tables
        """
        available_tables = []
        
        for table in self.table_manager.tables.values():
            if (table.can_accommodate(party_size) and 
                table.is_available_at(reservation_time, duration_hours)):
                available_tables.append({
                    'table_number': table.table_number,
                    'capacity': table.capacity,
                    'location': table.location,
                    'description': table.description,
                    'available_at': table.next_available.strftime('%H:%M') 
                    if table.next_available > datetime.now() else "Now"
                })
        
        return sorted(available_tables, key=lambda x: x['capacity'])
    
    def get_table_status(self) -> Dict:
        """
        Get status of all tables
        
        Returns:
            Dictionary of table statuses
        """
        return self.table_manager.get_table_status()
    
    # -------------------- Business Logic --------------------
    
    def _is_within_business_hours(self, reservation_time: datetime, 
                                 duration_hours: int) -> bool:
        """
        Check if reservation is within business hours
        
        Args:
            reservation_time: Reservation time
            duration_hours: Duration
            
        Returns:
            bool: True if within business hours
        """
        opening_time = reservation_time.replace(
            hour=config.Config.OPENING_HOUR, 
            minute=0, 
            second=0
        )
        closing_time = reservation_time.replace(
            hour=config.Config.CLOSING_HOUR, 
            minute=0, 
            second=0
        )
        end_time = reservation_time + timedelta(hours=duration_hours)
        
        return (opening_time <= reservation_time <= closing_time and 
                end_time <= closing_time)
    
    def suggest_alternative_times(self, desired_time: datetime, 
                                 party_size: int, duration_hours: int = 2) -> List[Dict]:
        """
        Suggest alternative times when desired time is unavailable
        
        Args:
            desired_time: Desired reservation time
            party_size: Number of people
            duration_hours: Duration needed
            
        Returns:
            List of alternative time slots
        """
        alternatives = []
        
        # Check +/- 30 minutes
        for offset_minutes in [-30, 30, -60, 60, -90, 90]:
            alternative_time = desired_time + timedelta(minutes=offset_minutes)
            
            if not self._is_within_business_hours(alternative_time, duration_hours):
                continue
            
            # Check if any tables available
            available_tables = self.find_available_tables(
                party_size, alternative_time, duration_hours
            )
            
            if available_tables:
                alternatives.append({
                    'time': alternative_time,
                    'available_tables': len(available_tables),
                    'table_numbers': [t['table_number'] for t in available_tables[:3]]
                })
        
        # Sort by closeness to desired time
        alternatives.sort(key=lambda x: abs((x['time'] - desired_time).total_seconds()))
        
        return alternatives[:5]  # Return top 5 alternatives
    
    # -------------------- Analytics --------------------
    
    def get_statistics(self) -> Dict:
        """
        Get reservation statistics
        
        Returns:
            Dictionary with statistics
        """
        repo_stats = self.repository.get_statistics()
        repo_stats.update({
            'rbt_operations': self.rbt_stats,
            'table_count': len(self.table_manager.tables),
            'available_tables_now': sum(1 for t in self.table_manager.tables.values() 
                                       if t.status.value == 'available'),
            'occupied_tables_now': sum(1 for t in self.table_manager.tables.values() 
                                      if t.status.value == 'occupied')
        })
        return repo_stats
    
    def get_daily_schedule(self, date: datetime) -> Dict:
        """
        Get daily schedule with time slots
        
        Args:
            date: Date to get schedule for
            
        Returns:
            Dictionary with time slots and reservations
        """
        schedule = {}
        
        # Create time slots for the day
        for hour in range(config.Config.OPENING_HOUR, config.Config.CLOSING_HOUR):
            for minute in [0, 30]:
                slot_time = datetime.combine(date, datetime.min.time()).replace(
                    hour=hour, minute=minute
                )
                slot_end = slot_time + timedelta(minutes=30)
                
                # Get reservations for this time slot
                reservations = self.get_reservations_by_time_range(slot_time, slot_end)
                
                schedule[f"{hour:02d}:{minute:02d}"] = {
                    'time': slot_time.strftime('%H:%M'),
                    'reservations': [
                        {
                            'id': r.id,
                            'customer': r.customer_name,
                            'table': r.table_number,
                            'party_size': r.party_size,
                            'duration': r.duration_hours
                        }
                        for r in reservations if r.status == 'confirmed'
                    ],
                    'reservation_count': len([r for r in reservations 
                                            if r.status == 'confirmed'])
                }
        
        return schedule
    
    def get_rbt_performance_metrics(self) -> Dict:
        """
        Get RBT performance metrics
        
        Returns:
            Dictionary with performance metrics
        """
        tree_stats = self.repository.rbtree
        return {
            'total_nodes': len(tree_stats),
            'tree_height': tree_stats.get_height(),
            'is_valid': tree_stats.is_valid_rbt()[0],
            'min_key': tree_stats.find_min(),
            'max_key': tree_stats.find_max(),
            'operations': self.rbt_stats
        }
    
    def export_rbt_structure(self) -> Dict:
        """
        Export RBT structure for visualization
        
        Returns:
            Dictionary representation of RBT
        """
        return self.repository.export_tree_structure()