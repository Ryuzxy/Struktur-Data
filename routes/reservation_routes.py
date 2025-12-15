"""
Reservation Routes for Flask
"""
from flask import Blueprint, request, jsonify, render_template
from datetime import datetime, timedelta
from services.reservation_service import ReservationService

reservation_bp = Blueprint('reservations', __name__, url_prefix='/reservations')
service = ReservationService()

# -------------------- HTML Routes --------------------

@reservation_bp.route('/')
def index():
    """Reservation list page"""
    return render_template('reservations/list.html')

@reservation_bp.route('/create')
def create_page():
    """Create reservation page"""
    return render_template('reservations/create.html')

@reservation_bp.route('/schedule')
def schedule_page():
    """Schedule view page"""
    current_date = datetime.now().date()
    return render_template('reservations/schedule.html', date=current_date)

@reservation_bp.route('/list')
def list_page():
    """Reservation list page"""
    return render_template('reservations/list.html')

# -------------------- API Routes --------------------

@reservation_bp.route('/api/all')
def get_all_reservations():
    """Get all reservations"""
    try:
        reservations = service.get_all_reservations()
        return jsonify({
            'success': True,
            'count': len(reservations),
            'reservations': [r.to_dict() for r in reservations]
        }), 200
    except Exception as e:
        print(f"Error getting all reservations: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@reservation_bp.route('/api/daily-schedule/<date_str>')
def get_daily_schedule(date_str):
    """Get daily schedule for a specific date using RBT range search"""
    try:
        # Parse date
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get all reservations for the day
        all_reservations = service.get_all_reservations()
        
        # Filter reservations for this date
        day_reservations = [
            r for r in all_reservations 
            if r.reservation_time.date() == target_date
        ]
        
        # Organize by time slots
        schedule = {}
        for res in day_reservations:
            time_key = res.reservation_time.strftime('%H:%M')
            
            if time_key not in schedule:
                schedule[time_key] = {
                    'reservations': []
                }
            
            schedule[time_key]['reservations'].append({
                'id': res.id,
                'customer': res.customer_name,
                'phone': res.customer_phone,
                'table': res.table_number or 0,
                'party_size': res.party_size,
                'time': res.reservation_time.strftime('%H:%M'),
                'end_time': res.end_time.strftime('%H:%M'),
                'duration': res.duration_hours,
                'status': res.status,
                'special_requests': res.special_requests
            })
        
        # Sort by time
        sorted_schedule = dict(sorted(schedule.items()))
        
        return jsonify({
            'success': True,
            'date': date_str,
            'schedule': sorted_schedule,
            'total_reservations': len(day_reservations),
            'count': len(day_reservations)
        }), 200
        
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }), 400
    except Exception as e:
        print(f"Error getting daily schedule: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@reservation_bp.route('/api/table-status')
def get_table_status():
    """Get current status of all tables"""
    try:
        current_time = datetime.now()
        
        # Initialize all tables as available
        tables = {}
        for table_num in range(1, 16):  # 15 tables
            tables[table_num] = {
                'number': table_num,
                'status': 'available',
                'current_reservation': None
            }
        
        # Get active reservations
        active_reservations = service.get_active_reservations()
        
        for res in active_reservations:
            if res.table_number and res.table_number in tables:
                tables[res.table_number]['status'] = 'occupied'
                tables[res.table_number]['current_reservation'] = {
                    'id': res.id,
                    'customer': res.customer_name,
                    'end_time': res.end_time.isoformat()
                }
        
        return jsonify({
            'success': True,
            'tables': tables
        }), 200
    except Exception as e:
        print(f"Error getting table status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@reservation_bp.route('/api/rbt-metrics')
def get_rbt_metrics():
    """Get Red-Black Tree performance metrics"""
    try:
        # Get RBT metrics from repository
        metrics = service.get_rbt_metrics()
        
        return jsonify({
            'success': True,
            'metrics': metrics
        }), 200
    except Exception as e:
        print(f"Error getting RBT metrics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@reservation_bp.route('/api/available-tables')
def get_available_tables():
    """Get available tables for date/time"""
    try:
        date_str = request.args.get('date')
        time_str = request.args.get('time', '12:00')
        party_size = request.args.get('party_size', 2, type=int)
        duration = request.args.get('duration', 2, type=int)
        
        if not date_str:
            return jsonify({
                'success': False,
                'error': 'Date parameter required'
            }), 400
        
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        time = datetime.strptime(time_str, '%H:%M').time()
        reservation_datetime = datetime.combine(date, time)
        
        available = service.find_available_tables(
            party_size=party_size,
            check_time=reservation_datetime,
            duration_hours=duration
        )
        
        return jsonify({
            'success': True,
            'available_tables': [{'table_number': t} for t in available]
        }), 200
    except Exception as e:
        print(f"Error checking available tables: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@reservation_bp.route('/api/create', methods=['POST'])
def create_reservation():
    """Create new reservation"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['customer_name', 'customer_phone', 'party_size', 
                          'reservation_time', 'table_number']
        missing_fields = [f for f in required_fields if f not in data or data[f] is None]
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Parse datetime safely
        try:
            reservation_time_str = data['reservation_time'].strip()
            if reservation_time_str.endswith('Z'):
                reservation_time_str = reservation_time_str[:-1]
            
            reservation_time = datetime.fromisoformat(reservation_time_str)
        except (ValueError, AttributeError) as e:
            return jsonify({
                'success': False,
                'error': f'Invalid datetime format: {str(e)}'
            }), 400
        
        # Parse numeric fields safely
        try:
            party_size = int(data['party_size'])
            duration_hours = int(data.get('duration_hours', 2))
            table_number = int(data['table_number'])
        except (ValueError, TypeError) as e:
            return jsonify({
                'success': False,
                'error': f'Invalid numeric value: {str(e)}'
            }), 400
        
        # Create reservation
        success, message, reservation = service.create_reservation(
            customer_name=str(data['customer_name']).strip(),
            customer_phone=str(data['customer_phone']).strip(),
            party_size=party_size,
            reservation_time=reservation_time,
            duration_hours=duration_hours,
            special_requests=str(data.get('special_requests', '')).strip(),
            table_number=table_number
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'reservation': reservation.to_dict()
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        import traceback
        print(f"Error creating reservation: {str(e)}")
        print(traceback.format_exc())
        
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@reservation_bp.route('/api/<reservation_id>')
def get_reservation(reservation_id):
    """Get single reservation"""
    try:
        reservation = service.get_reservation(reservation_id)
        if reservation:
            return jsonify({
                'success': True,
                'reservation': reservation.to_dict()
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Reservation not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@reservation_bp.route('/api/<reservation_id>/cancel', methods=['POST'])
def cancel_reservation(reservation_id):
    """Cancel reservation (soft delete)"""
    try:
        success, message = service.cancel_reservation(reservation_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@reservation_bp.route('/api/<reservation_id>', methods=['DELETE'])
def delete_reservation(reservation_id):
    """Delete reservation permanently"""
    try:
        success, message = service.delete_reservation_permanently(reservation_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@reservation_bp.route('/api/statistics')
def get_statistics():
    """Get reservation statistics"""
    try:
        stats = service.get_statistics()
        
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@reservation_bp.route('/api/bulk-update', methods=['POST'])
def bulk_update():
    """Bulk update reservations"""
    try:
        data = request.get_json()
        reservation_ids = data.get('reservation_ids', [])
        updates = data.get('updates', {})
        
        if not reservation_ids:
            return jsonify({
                'success': False,
                'error': 'No reservations selected'
            }), 400
        
        success, message, count = service.bulk_update_reservations(reservation_ids, updates)
        
        return jsonify({
            'success': success,
            'message': message,
            'updated_count': count
        }), 200 if success else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500