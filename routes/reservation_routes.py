"""
Reservation Routes for Flask
"""
from flask import Blueprint, request, jsonify, render_template
from datetime import datetime
from services.reservation_service import ReservationService

reservation_bp = Blueprint('reservations', __name__, url_prefix='/reservations')
service = ReservationService()

# -------------------- HTML Routes --------------------

@reservation_bp.route('/')
def index():
    """Reservation dashboard"""
    return render_template('reservations/index.html')

@reservation_bp.route('/create')
def create_page():
    """Create reservation page"""
    return render_template('reservations/create.html')

@reservation_bp.route('/schedule')
def schedule_page():
    """Daily schedule page"""
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    return render_template('reservations/schedule.html', date=date)

@reservation_bp.route('/list')
def list_page():
    """Reservation list page"""
    return render_template('reservations/list.html')

# -------------------- API Routes --------------------

@reservation_bp.route('/api/create', methods=['POST'])
def create_reservation():
    """Create new reservation"""
    try:
        data = request.get_json()
        
        # Parse datetime
        reservation_time = datetime.fromisoformat(data['reservation_time'].replace('Z', '+00:00'))
        
        # Create reservation
        success, message, reservation = service.create_reservation(
            customer_name=data['customer_name'],
            customer_phone=data['customer_phone'],
            party_size=int(data['party_size']),
            reservation_time=reservation_time,
            duration_hours=int(data.get('duration_hours', 2)),
            special_requests=data.get('special_requests', '')
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@reservation_bp.route('/api/<reservation_id>')
def get_reservation(reservation_id):
    """Get reservation by ID"""
    reservation = service.get_reservation(reservation_id)
    
    if reservation:
        return jsonify({
            'success': True,
            'reservation': reservation.to_dict()
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Reservation not found'
        }), 404

@reservation_bp.route('/api/<reservation_id>', methods=['PUT'])
def update_reservation(reservation_id):
    """Update reservation"""
    try:
        data = request.get_json()
        updates = {}
        
        # Parse fields that need conversion
        if 'reservation_time' in data:
            updates['reservation_time'] = datetime.fromisoformat(
                data['reservation_time'].replace('Z', '+00:00')
            )
        
        if 'duration_hours' in data:
            updates['duration_hours'] = int(data['duration_hours'])
        
        if 'party_size' in data:
            updates['party_size'] = int(data['party_size'])
        
        # Add other fields
        for field in ['customer_name', 'customer_phone', 'special_requests', 'status']:
            if field in data:
                updates[field] = data[field]
        
        success, message = service.update_reservation(reservation_id, **updates)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
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

@reservation_bp.route('/api/<reservation_id>/cancel', methods=['POST'])
def cancel_reservation(reservation_id):
    """Cancel reservation"""
    success, message = service.cancel_reservation(reservation_id)
    
    if success:
        return jsonify({
            'success': True,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'error': message
        }), 404

@reservation_bp.route('/api/by-date/<date_str>')
def get_reservations_by_date(date_str):
    """Get reservations by date"""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        reservations = service.get_reservations_by_date(date)
        
        return jsonify({
            'success': True,
            'date': date_str,
            'reservations': [r.to_dict() for r in reservations],
            'count': len(reservations)
        })
        
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }), 400

@reservation_bp.route('/api/by-customer/<customer_name>')
def get_reservations_by_customer(customer_name):
    """Get reservations by customer name"""
    reservations = service.get_reservations_by_customer(customer_name)
    
    return jsonify({
        'success': True,
        'customer': customer_name,
        'reservations': [r.to_dict() for r in reservations],
        'count': len(reservations)
    })

@reservation_bp.route('/api/upcoming')
def get_upcoming_reservations():
    """Get upcoming reservations"""
    hours_ahead = request.args.get('hours', default=24, type=int)
    reservations = service.get_upcoming_reservations(hours_ahead)
    
    return jsonify({
        'success': True,
        'reservations': [r.to_dict() for r in reservations],
        'count': len(reservations)
    })

@reservation_bp.route('/api/active')
def get_active_reservations():
    """Get currently active reservations"""
    reservations = service.get_active_reservations()
    
    return jsonify({
        'success': True,
        'reservations': [r.to_dict() for r in reservations],
        'count': len(reservations)
    })

@reservation_bp.route('/api/available-tables')
def get_available_tables():
    """Find available tables"""
    try:
        party_size = request.args.get('party_size', default=2, type=int)
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        time_str = request.args.get('time', '12:00')
        duration = request.args.get('duration', default=2, type=int)
        
        # Combine date and time
        datetime_str = f"{date_str}T{time_str}"
        reservation_time = datetime.fromisoformat(datetime_str)
        
        tables = service.find_available_tables(party_size, reservation_time, duration)
        
        return jsonify({
            'success': True,
            'party_size': party_size,
            'time': reservation_time.isoformat(),
            'duration': duration,
            'available_tables': tables,
            'count': len(tables)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@reservation_bp.route('/api/table-status')
def get_table_status():
    """Get table status"""
    status = service.get_table_status()
    
    return jsonify({
        'success': True,
        'tables': status
    })

@reservation_bp.route('/api/suggest-alternatives')
def suggest_alternative_times():
    """Suggest alternative times"""
    try:
        party_size = request.args.get('party_size', default=2, type=int)
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        time_str = request.args.get('time', '12:00')
        duration = request.args.get('duration', default=2, type=int)
        
        # Combine date and time
        datetime_str = f"{date_str}T{time_str}"
        desired_time = datetime.fromisoformat(datetime_str)
        
        alternatives = service.suggest_alternative_times(
            desired_time, party_size, duration
        )
        
        # Format alternatives for response
        formatted_alternatives = []
        for alt in alternatives:
            formatted_alternatives.append({
                'time': alt['time'].strftime('%Y-%m-%d %H:%M'),
                'available_tables': alt['available_tables'],
                'table_numbers': alt['table_numbers']
            })
        
        return jsonify({
            'success': True,
            'desired_time': desired_time.strftime('%Y-%m-%d %H:%M'),
            'alternatives': formatted_alternatives
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@reservation_bp.route('/api/statistics')
def get_statistics():
    """Get reservation statistics"""
    stats = service.get_statistics()
    
    return jsonify({
        'success': True,
        'statistics': stats
    })

@reservation_bp.route('/api/daily-schedule/<date_str>')
def get_daily_schedule(date_str):
    """Get daily schedule"""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        schedule = service.get_daily_schedule(date)
        
        return jsonify({
            'success': True,
            'date': date_str,
            'schedule': schedule
        })
        
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }), 400

@reservation_bp.route('/api/rbt-metrics')
def get_rbt_metrics():
    """Get RBT performance metrics"""
    metrics = service.get_rbt_performance_metrics()
    
    return jsonify({
        'success': True,
        'metrics': metrics
    })

@reservation_bp.route('/api/rbt-structure')
def get_rbt_structure():
    """Get RBT structure for visualization"""
    structure = service.export_rbt_structure()
    
    return jsonify({
        'success': True,
        'structure': structure
    })