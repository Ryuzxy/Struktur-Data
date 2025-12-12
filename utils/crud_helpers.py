"""
Helper functions for CRUD operations
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from domain.reservation import Reservation

class CRUDHelper:
    """Helper class for CRUD operations"""
    
    @staticmethod
    def validate_reservation_data(data: Dict[str, Any]) -> tuple:
        """
        Validate reservation data
        
        Args:
            data: Dictionary with reservation data
            
        Returns:
            Tuple of (is_valid, error_message, cleaned_data)
        """
        required_fields = ['customer_name', 'customer_phone', 'party_size', 'reservation_time']
        
        # Check required fields
        for field in required_fields:
            if field not in data or not data[field]:
                return False, f"Missing required field: {field}", None
        
        # Validate customer name
        customer_name = data['customer_name'].strip()
        if len(customer_name) < 2:
            return False, "Customer name must be at least 2 characters", None
        
        # Validate phone number (basic validation)
        phone = str(data['customer_phone']).strip()
        if len(phone) < 8:
            return False, "Phone number must be at least 8 digits", None
        
        # Validate party size
        try:
            party_size = int(data['party_size'])
            if party_size < 1 or party_size > 20:
                return False, "Party size must be between 1 and 20", None
        except (ValueError, TypeError):
            return False, "Invalid party size", None
        
        # Validate reservation time
        try:
            if isinstance(data['reservation_time'], str):
                reservation_time = datetime.fromisoformat(data['reservation_time'].replace('Z', '+00:00'))
            else:
                reservation_time = data['reservation_time']
            
            # Check if reservation is in the future
            if reservation_time < datetime.now():
                return False, "Reservation time cannot be in the past", None
            
            # Check business hours (8:00 - 22:00)
            hour = reservation_time.hour
            if hour < 8 or hour > 21:  # 22:00 is closing, so last reservation at 21:00
                return False, "Reservation must be between 08:00 and 22:00", None
            
        except (ValueError, TypeError):
            return False, "Invalid reservation time format", None
        
        # Validate duration
        duration_hours = data.get('duration_hours', 2)
        try:
            duration_hours = float(duration_hours)
            if duration_hours < 0.5 or duration_hours > 4:
                return False, "Duration must be between 0.5 and 4 hours", None
        except (ValueError, TypeError):
            return False, "Invalid duration", None
        
        # Check end time
        end_time = reservation_time + timedelta(hours=duration_hours)
        if end_time.hour > 22 or (end_time.hour == 22 and end_time.minute > 0):
            return False, "Reservation must end by 22:00", None
        
        # Clean and return data
        cleaned_data = {
            'customer_name': customer_name,
            'customer_phone': phone,
            'party_size': party_size,
            'reservation_time': reservation_time,
            'duration_hours': duration_hours,
            'special_requests': data.get('special_requests', ''),
            'table_number': data.get('table_number'),
            'status': data.get('status', 'confirmed')
        }
        
        return True, "Valid reservation data", cleaned_data
    
    @staticmethod
    def filter_reservations(reservations: List[Reservation], filters: Dict[str, Any]) -> List[Reservation]:
        """
        Filter reservations based on criteria
        
        Args:
            reservations: List of Reservation objects
            filters: Dictionary with filter criteria
            
        Returns:
            Filtered list of reservations
        """
        filtered = reservations
        
        # Filter by customer name
        if 'customer_name' in filters and filters['customer_name']:
            customer_filter = filters['customer_name'].lower()
            filtered = [r for r in filtered if customer_filter in r.customer_name.lower()]
        
        # Filter by status
        if 'status' in filters and filters['status']:
            status_filter = filters['status']
            filtered = [r for r in filtered if r.status == status_filter]
        
        # Filter by table number
        if 'table_number' in filters and filters['table_number']:
            table_filter = filters['table_number']
            filtered = [r for r in filtered if r.table_number == table_filter]
        
        # Filter by date range
        if 'start_date' in filters and filters['start_date']:
            start_date = filters['start_date']
            filtered = [r for r in filtered if r.reservation_time.date() >= start_date]
        
        if 'end_date' in filters and filters['end_date']:
            end_date = filters['end_date']
            filtered = [r for r in filtered if r.reservation_time.date() <= end_date]
        
        # Filter by party size range
        if 'min_party_size' in filters:
            min_size = filters['min_party_size']
            filtered = [r for r in filtered if r.party_size >= min_size]
        
        if 'max_party_size' in filters:
            max_size = filters['max_party_size']
            filtered = [r for r in filtered if r.party_size <= max_size]
        
        return filtered
    
    @staticmethod
    def sort_reservations(reservations: List[Reservation], sort_by: str = 'time', 
                         descending: bool = False) -> List[Reservation]:
        """
        Sort reservations
        
        Args:
            reservations: List of Reservation objects
            sort_by: Field to sort by (time, customer, party_size, table)
            descending: Sort in descending order
            
        Returns:
            Sorted list of reservations
        """
        if not reservations:
            return []
        
        sort_key = {
            'time': lambda r: r.reservation_time,
            'customer': lambda r: r.customer_name.lower(),
            'party_size': lambda r: r.party_size,
            'table': lambda r: r.table_number or 0,
            'status': lambda r: r.status,
            'created': lambda r: r.created_at
        }.get(sort_by, lambda r: r.reservation_time)
        
        sorted_list = sorted(reservations, key=sort_key, reverse=descending)
        return sorted_list
    
    @staticmethod
    def paginate_reservations(reservations: List[Reservation], page: int = 1, 
                             per_page: int = 20) -> Dict[str, Any]:
        """
        Paginate reservations list
        
        Args:
            reservations: List of Reservation objects
            page: Page number (1-indexed)
            per_page: Items per page
            
        Returns:
            Dictionary with paginated results
        """
        total = len(reservations)
        total_pages = (total + per_page - 1) // per_page
        
        # Validate page
        if page < 1:
            page = 1
        elif page > total_pages and total_pages > 0:
            page = total_pages
        
        # Calculate slice indices
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # Get page items
        page_items = reservations[start_idx:end_idx]
        
        return {
            'items': page_items,
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages
        }
    
    @staticmethod
    def calculate_statistics(reservations: List[Reservation]) -> Dict[str, Any]:
        """
        Calculate statistics from reservations
        
        Args:
            reservations: List of Reservation objects
            
        Returns:
            Dictionary with statistics
        """
        if not reservations:
            return {
                'total': 0,
                'confirmed': 0,
                'cancelled': 0,
                'completed': 0,
                'average_party_size': 0,
                'peak_hour': None,
                'total_revenue': 0
            }
        
        # Basic counts
        total = len(reservations)
        confirmed = sum(1 for r in reservations if r.status == 'confirmed')
        cancelled = sum(1 for r in reservations if r.status == 'cancelled')
        completed = sum(1 for r in reservations if r.status == 'completed')
        
        # Average party size
        avg_party = sum(r.party_size for r in reservations) / total
        
        # Peak hour analysis
        hour_counts = {h: 0 for h in range(24)}
        for r in reservations:
            if r.status == 'confirmed':
                hour = r.reservation_time.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else None
        
        # Revenue estimation (assuming average spend per person)
        avg_spend_per_person = 50000  # Rp 50,000 per person
        total_revenue = sum(r.party_size * avg_spend_per_person 
                           for r in reservations if r.status in ['confirmed', 'completed'])
        
        return {
            'total': total,
            'confirmed': confirmed,
            'cancelled': cancelled,
            'completed': completed,
            'average_party_size': round(avg_party, 1),
            'peak_hour': peak_hour,
            'total_revenue': total_revenue,
            'hour_distribution': hour_counts
        }
    
    @staticmethod
    def export_reservations(reservations: List[Reservation], format: str = 'json') -> str:
        """
        Export reservations to different formats
        
        Args:
            reservations: List of Reservation objects
            format: Export format (json, csv, html)
            
        Returns:
            String in the requested format
        """
        if format == 'json':
            import json
            data = [r.to_dict() for r in reservations]
            return json.dumps({
                'export_date': datetime.now().isoformat(),
                'count': len(reservations),
                'reservations': data
            }, indent=2, default=str)
        
        elif format == 'csv':
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'ID', 'Customer Name', 'Phone', 'Date', 'Time', 
                'Table', 'Party Size', 'Duration', 'Status', 
                'Special Requests', 'Created At'
            ])
            
            # Write data
            for r in reservations:
                writer.writerow([
                    r.id,
                    r.customer_name,
                    r.customer_phone,
                    r.reservation_time.strftime('%Y-%m-%d'),
                    r.reservation_time.strftime('%H:%M'),
                    r.table_number or '',
                    r.party_size,
                    r.duration_hours,
                    r.status,
                    r.special_requests or '',
                    r.created_at.strftime('%Y-%m-%d %H:%M')
                ])
            
            return output.getvalue()
        
        elif format == 'html':
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Reservation Export</title>
                <style>
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #6f42c1; color: white; }}
                    tr:nth-child(even) {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <h1>Reservation Export</h1>
                <p>Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                <p>Total Reservations: {len(reservations)}</p>
                
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Customer</th>
                        <th>Phone</th>
                        <th>Date/Time</th>
                        <th>Table</th>
                        <th>Party Size</th>
                        <th>Duration</th>
                        <th>Status</th>
                    </tr>
            """
            
            for r in reservations:
                html += f"""
                    <tr>
                        <td>{r.id}</td>
                        <td>{r.customer_name}</td>
                        <td>{r.customer_phone}</td>
                        <td>{r.reservation_time.strftime('%Y-%m-%d %H:%M')}</td>
                        <td>{r.table_number or ''}</td>
                        <td>{r.party_size}</td>
                        <td>{r.duration_hours} hours</td>
                        <td>{r.status}</td>
                    </tr>
                """
            
            html += """
                </table>
            </body>
            </html>
            """
            
            return html
        
        else:
            raise ValueError(f"Unsupported format: {format}")