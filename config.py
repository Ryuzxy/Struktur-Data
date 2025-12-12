import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    
    # RBT Configuration
    RBT_MAX_RESERVATIONS = int(os.environ.get('RBT_MAX_RESERVATIONS', '1000'))
    
    # Business Rules
    OPENING_HOUR = 8  # 8 AM
    CLOSING_HOUR = 22  # 10 PM
    RESERVATION_DURATION = 2  # hours
    MAX_PARTY_SIZE = 20
    MAX_TABLES = 15
    
    # Time Settings
    TIMEZONE = 'Asia/Jakarta'
    
config = Config()