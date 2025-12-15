"""
Main Flask Application for BroderPro Café Management System
"""
from flask import Flask, render_template, jsonify
from datetime import datetime
import config
from pathlib import Path

# Import Blueprints
from routes.reservation_routes import reservation_bp
from services.reservation_service import ReservationService

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.config.from_object(config.Config)
    
    # Ensure data directory exists
    Path('data').mkdir(exist_ok=True)
    Path('templates').mkdir(exist_ok=True)

    # Register Blueprints
    app.register_blueprint(reservation_bp)
    
    # Initialize services
    app.reservation_service = ReservationService()
    
    # -------------------- Main Routes --------------------
    
    @app.route('/')
    def index():
        """Main dashboard"""
        try:
            stats = app.reservation_service.get_statistics()
            return render_template('dashboard.html', stats=stats)
        except Exception as e:
            print(f"Error loading dashboard: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Return with empty stats on error
            empty_stats = {
                'total_reservations': 0,
                'today_count': 0,
                'rbt_size': 0,
                'rbt_height': 0,
                'table_count': 15,
                'average_party_size': 0,
                'available_tables_now': 0,
                'rbt_operations': {
                    'insert_count': 0,
                    'search_count': 0,
                    'range_search_count': 0,
                    'delete_count': 0
                }
            }
            return render_template('dashboard.html', stats=empty_stats)
    
    @app.route('/dashboard')
    def dashboard():
        """Dashboard page"""
        stats = app.reservation_service.get_statistics()
        return render_template('dashboard.html', stats=stats)
    
    @app.route('/rbt-visualizer')
    def rbt_visualizer():
        """Red-Black Tree visualizer"""
        rbt_structure = app.reservation_service.export_rbt_structure()
        return render_template('rbt_visualizer.html', rbt_structure=rbt_structure)
    
    @app.route('/api/health')
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'BroderPro Café Management',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        })
    
    @app.route('/api/system-info')
    def system_info():
        """System information"""
        rbt_metrics = app.reservation_service.get_rbt_performance_metrics()
        
        return jsonify({
            'system': {
                'name': 'BroderPro Café Management System',
                'version': '1.0.0',
                'algorithm': 'Red-Black Tree',
                'description': 'Sistem manajemen pesanan dan reservasi café berbasis Red-Black Tree'
            },
            'performance': {
                'reservation_count': len(app.reservation_service.repository.reservations),
                'rbt_nodes': rbt_metrics['total_nodes'],
                'rbt_height': rbt_metrics['tree_height'],
                'rbt_valid': rbt_metrics['is_valid']
            },
            'config': {
                'opening_hour': config.Config.OPENING_HOUR,
                'closing_hour': config.Config.CLOSING_HOUR,
                'max_party_size': config.Config.MAX_PARTY_SIZE,
                'max_tables': config.Config.MAX_TABLES
            }
        })
        f
    
    @app.context_processor
    def inject_now():
        return {"now": datetime.now}
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=config.Config.DEBUG, host='0.0.0.0', port=5000)