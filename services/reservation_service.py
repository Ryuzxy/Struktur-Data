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
                          duration_hours: int = 2, special_requests: str = "",
                          table_number: int = None) -> Tuple[bool, str, Optional[Reservation]]:
        """
        Create new reservation with conflict checking
        
        Args:
            customer_name: Customer name
            customer_phone: Customer phone
            party_size: Number of people
            reservation_time: Reservation datetime
            duration_hours: Duration in hours
            special_requests: Special requests
            table_number: Pre-selected table number
            
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
            return False, "Reservation outside business hours (08:00-22:00)", None
        
        # Create reservation
        reservation = ReservationFactory.create_reservation(
            customer_name=customer_name,
            customer_phone=customer_phone,
            party_size=party_size,
            reservation_time=reservation_time,
            duration_hours=duration_hours,
            special_requests=special_requests,
            table_number=table_number  # Assign table number
        )
        
        # Jika table_number tidak disediakan, cari table otomatis
        if not table_number:
            table = self.table_manager.find_available_table(
                party_size, reservation_time, duration_hours
            )
            
            if table:
                reservation.assign_table(table.table_number)
            else:
                return False, "No tables available for the requested time", None
        else:
            # Validasi table yang dipilih tersedia
            table = self.table_manager.tables.get(table_number)
            if not table:
                return False, f"Table {table_number} does not exist", None
            
            if not table.can_accommodate(party_size):
                return False, f"Table {table_number} cannot accommodate {party_size} people", None
            
            if not table.is_available_at(reservation_time, duration_hours):
                return False, f"Table {table_number} is not available at this time", None
        
        # Check for conflicts using RBT
        conflicts = self.repository.get_conflicting_reservations(reservation)
        if conflicts:
            same_table_conflicts = [c for c in conflicts 
                                   if c.table_number == reservation.table_number and 
                                   c.status == 'confirmed']
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
    
    def get_reservations_by_date(self, date) -> List[Reservation]:
        """Get reservations by specific date"""
        try:
            all_reservations = self.repository.get_all()
            
            # Filter by date
            filtered = [
                r for r in all_reservations 
                if r.reservation_time.date() == date
            ]
            
            return filtered
        except Exception as e:
            print(f"Error getting reservations by date: {str(e)}")
            return []

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
            hours_ahead: Number of hours to look ahead
            
        Returns:
            List of upcoming reservations
        """
        now = datetime.now()
        future_time = now + timedelta(hours=hours_ahead)
        
        return self.repository.get_by_time_range(now, future_time)

    def get_active_reservations(self) -> List[Reservation]:
        """
        Get currently active reservations
        
        Returns:
            List of active reservations
        """
        now = datetime.now()
        # Get reservations that are happening now
        reservations = self.repository.get_all()
        return [r for r in reservations if r.is_active_at(now) and r.status == 'confirmed']
    
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
        """Get reservation statistics"""
        try:
            all_reservations = self.repository.get_all()
            today = datetime.now().date()
            
            confirmed = [r for r in all_reservations if r.status == 'confirmed']
            cancelled = [r for r in all_reservations if r.status == 'cancelled']
            completed = [r for r in all_reservations if r.status == 'completed']
            today_reservations = [r for r in all_reservations if r.reservation_time.date() == today]
            
            total_party_size = sum(r.party_size for r in all_reservations)
            avg_party_size = total_party_size / len(all_reservations) if all_reservations else 0
            
            return {
                'total_reservations': len(all_reservations),
                'confirmed': len(confirmed),
                'cancelled': len(cancelled),
                'completed': len(completed),
                'today_count': len(today_reservations),
                'average_party_size': round(avg_party_size, 1),
                'rbt_size': len(self.repository.reservations),
                'rbt_height': self.repository.rbtree.get_height() if hasattr(self.repository.rbtree, 'get_height') else 0,
                'table_count': 15,
                'available_tables_now': self._count_available_tables(),
                'rbt_operations': {
                    'insert_count': self.rbt_stats.get('insert_count', 0),
                    'search_count': self.rbt_stats.get('search_count', 0),
                    'range_search_count': self.rbt_stats.get('range_search_count', 0),
                    'delete_count': self.rbt_stats.get('delete_count', 0)
                }
            }
        except Exception as e:
            print(f"Error getting statistics: {str(e)}")
            return {
                'total_reservations': 0,
                'confirmed': 0,
                'cancelled': 0,
                'completed': 0,
                'today_count': 0,
                'average_party_size': 0,
                'rbt_size': 0,
                'rbt_height': 0,
                'table_count': 15,
                'available_tables_now': 0,
                'rbt_operations': {
                    'insert_count': 0,
                    'search_count': 0,
                    'range_search_count': 0,
                    'delete_count': 0
                }
            }
    
    def _count_available_tables(self) -> int:
        """Count available tables right now"""
        try:
            now = datetime.now()
            occupied = set()
            
            for reservation in self.repository.get_all():
                if (reservation.status == 'confirmed' and 
                    reservation.is_active_at(now)):
                    if reservation.table_number:
                        occupied.add(reservation.table_number)
            
            return 15 - len(occupied)
        except Exception as e:
            print(f"Error counting available tables: {str(e)}")
            return 15

    def get_all_reservations(self) -> List[Reservation]:
        """Get all reservations"""
        return self.repository.get_all()
    
    def get_daily_schedule(self, date: datetime) -> Dict:
        """
        Get daily schedule with time slots
        
        Args:
            date: Date to get schedule for
            
        Returns:
            Dictionary with time slots and reservations
        """
        schedule = {}
        
        # Ensure date is a date object, not datetime
        if isinstance(date, datetime):
            date = date.date()
        
        # Create time slots for the day
        for hour in range(config.Config.OPENING_HOUR, config.Config.CLOSING_HOUR):
            for minute in [0, 30]:
                # Create slot time correctly
                slot_time = datetime.combine(date, datetime.min.time()).replace(
                    hour=hour, minute=minute
                )
                slot_end = slot_time + timedelta(minutes=30)
                
                # Get reservations for this time slot
                reservations = self.get_reservations_by_time_range(slot_time, slot_end)
                
                # Format time slot key properly
                slot_key = slot_time.strftime('%H:%M')
                
                schedule[slot_key] = {
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
    
    # Add these methods to ReservationService class:

    def search_reservations(self, filters: Dict[str, any] = None) -> List[Reservation]:
        """
        Search reservations with filters
        
        Args:
            filters: Dictionary with filter criteria
            
        Returns:
            List of filtered reservations
        """
        from utils.crud_helpers import CRUDHelper
        
        all_reservations = self.repository.get_all()
        
        if not filters:
            return all_reservations
        
        return CRUDHelper.filter_reservations(all_reservations, filters)

    def get_reservation_with_details(self, reservation_id: str) -> Optional[Dict[str, any]]:
        """
        Get reservation with additional details
        
        Args:
            reservation_id: Reservation ID
            
        Returns:
            Dictionary with reservation details or None
        """
        reservation = self.repository.get(reservation_id)
        if not reservation:
            return None
        
        # Get conflicting reservations
        conflicts = self.repository.get_conflicting_reservations(reservation)
        
        # Get table details
        table_info = None
        if reservation.table_number:
            table = self.table_manager.tables.get(reservation.table_number)
            if table:
                table_info = table.to_dict()
        
        # Calculate time until reservation
        now = datetime.now()
        time_until = reservation.reservation_time - now
        hours_until = time_until.total_seconds() / 3600
        
        return {
            'reservation': reservation.to_dict(),
            'conflicts': [c.to_dict() for c in conflicts],
            'conflict_count': len(conflicts),
            'table_info': table_info,
            'time_until_hours': hours_until,
            'is_upcoming': hours_until > 0,
            'is_active': reservation.is_active_at(now),
            'rbt_key_info': {
                'key': reservation.rbt_key,
                'timestamp': reservation.reservation_time.timestamp(),
                'unique_id': int(str(reservation.rbt_key).split('.')[1]) if '.' in str(reservation.rbt_key) else 0
            }
        }

    def bulk_update_reservations(self, reservation_ids: List[str], updates: Dict[str, any]) -> Dict[str, any]:
        """
        Bulk update multiple reservations
        
        Args:
            reservation_ids: List of reservation IDs
            updates: Dictionary with updates to apply
            
        Returns:
            Dictionary with results
        """
        results = {
            'success_count': 0,
            'failure_count': 0,
            'failures': []
        }
        
        for reservation_id in reservation_ids:
            try:
                success, message = self.update_reservation(reservation_id, **updates)
                if success:
                    results['success_count'] += 1
                else:
                    results['failure_count'] += 1
                    results['failures'].append({
                        'reservation_id': reservation_id,
                        'error': message
                    })
            except Exception as e:
                results['failure_count'] += 1
                results['failures'].append({
                    'reservation_id': reservation_id,
                    'error': str(e)
                })
        
        return results

    def delete_reservation_permanently(self, reservation_id: str) -> Tuple[bool, str]:
        """
        Permanently delete reservation
        
        Args:
            reservation_id: Reservation ID to delete
            
        Returns:
            Tuple of (success, message)
        """
        if self.repository.delete(reservation_id):
            self.rbt_stats['delete_count'] += 1
            return True, "Reservation deleted permanently"
        else:
            return False, "Reservation not found or could not be deleted"

    def get_detailed_statistics(self, days_back: int = 30) -> Dict[str, any]:
        """
        Get detailed statistics
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Dictionary with detailed statistics
        """
        from utils.crud_helpers import CRUDHelper
        
        all_reservations = self.repository.get_all()
        now = datetime.now()
        start_date = now - timedelta(days=days_back)
        
        # Filter recent reservations
        recent_reservations = [
            r for r in all_reservations 
            if r.created_at >= start_date
        ]
        
        # Basic statistics
        basic_stats = CRUDHelper.calculate_statistics(recent_reservations)
        
        # Daily trends
        daily_data = {}
        current_date = start_date.date()
        end_date = now.date()
        
        while current_date <= end_date:
            daily_reservations = [
                r for r in recent_reservations 
                if r.reservation_time.date() == current_date
            ]
            
            daily_data[current_date.isoformat()] = {
                'total': len(daily_reservations),
                'confirmed': len([r for r in daily_reservations if r.status == 'confirmed']),
                'cancelled': len([r for r in daily_reservations if r.status == 'cancelled']),
                'completed': len([r for r in daily_reservations if r.status == 'completed']),
                'avg_party_size': sum(r.party_size for r in daily_reservations) / len(daily_reservations) 
                if daily_reservations else 0
            }
            
            current_date += timedelta(days=1)
        
        # Customer statistics
        customer_counts = {}
        for r in recent_reservations:
            if r.customer_name not in customer_counts:
                customer_counts[r.customer_name] = {
                    'count': 0,
                    'phone': r.customer_phone,
                    'total_party_size': 0
                }
            customer_counts[r.customer_name]['count'] += 1
            customer_counts[r.customer_name]['total_party_size'] += r.party_size
        
        top_customers = sorted(
            customer_counts.items(), 
            key=lambda x: x[1]['count'], 
            reverse=True
        )[:10]
        
        # Table usage statistics
        table_usage = {}
        for table_num, table in self.table_manager.tables.items():
            table_reservations = [
                r for r in recent_reservations 
                if r.table_number == table_num and r.status == 'confirmed'
            ]
            table_usage[table_num] = {
                'reservation_count': len(table_reservations),
                'total_hours': sum(r.duration_hours for r in table_reservations),
                'avg_party_size': sum(r.party_size for r in table_reservations) / len(table_reservations) 
                if table_reservations else 0,
                'capacity': table.capacity,
                'location': table.location
            }
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': now.isoformat(),
                'days': days_back
            },
            'basic_statistics': basic_stats,
            'daily_trends': daily_data,
            'top_customers': [
                {
                    'name': name,
                    'reservation_count': data['count'],
                    'phone': data['phone'],
                    'avg_party_size': data['total_party_size'] / data['count']
                }
                for name, data in top_customers
            ],
            'table_usage': table_usage,
            'rbt_performance': {
                'total_nodes': len(self.repository.rbtree),
                'tree_height': self.repository.rbtree.get_height(),
                'operations': self.rbt_stats,
                'is_balanced': self.repository.rbtree.is_valid_rbt()[0]
            }
        }