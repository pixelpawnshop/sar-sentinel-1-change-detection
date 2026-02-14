import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""
    
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_ENV') == 'development'
    FLASK_HOST = os.getenv('FLASK_HOST', '127.0.0.1')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    
    # Base URL for links in notifications
    BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')
    
    # Google Earth Engine
    GEE_PROJECT_ID = os.getenv('GEE_PROJECT_ID', 'sar-flood-detection')
    
    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'satellite_monitor.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Webhook
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    
    # Monitoring
    CHECK_INTERVAL_HOURS = int(os.getenv('CHECK_INTERVAL_HOURS', 6))
    CHANGE_THRESHOLD_DB = float(os.getenv('CHANGE_THRESHOLD_DB', 3.0))
    
    # Sentinel-1 Configuration
    SENTINEL1_COLLECTION = 'COPERNICUS/S1_GRD'
    INSTRUMENT_MODE = 'IW'  # Interferometric Wide swath
    POLARIZATION = 'VV'  # Default polarization
    
    # Change Detection
    SPECKLE_FILTER_RADIUS = 3  # pixels for focal median filter
    MIN_CHANGE_AREA_SQKM = 0.01  # Minimum area to consider as change
    
    @staticmethod
    def validate():
        """Validate required configuration."""
        if not Config.GEE_PROJECT_ID:
            raise ValueError("GEE_PROJECT_ID is required. Set it in .env file.")
        if not Config.WEBHOOK_URL:
            print("Warning: WEBHOOK_URL not configured. Notifications will be disabled.")
        return True
