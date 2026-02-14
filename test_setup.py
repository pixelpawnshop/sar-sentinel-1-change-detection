"""
Test script to verify installation and configuration.

Run this after setup to ensure everything is working correctly.
"""
import sys


def test_imports():
    """Test that all required packages are installed."""
    print("Testing package imports...")
    
    required = [
        'flask',
        'ee',  # earthengine-api
        'requests',
        'apscheduler',
        'sqlalchemy',
        'geopandas',
        'shapely',
        'dotenv'
    ]
    
    failed = []
    for package in required:
        try:
            __import__(package)
            print(f"  {package}")
        except ImportError:
            print(f"  {package} - NOT FOUND")
            failed.append(package)
    
    if failed:
        print(f"\nMissing packages: {', '.join(failed)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("All packages installed\n")
    return True


def test_gee():
    """Test Google Earth Engine authentication."""
    print("Testing Google Earth Engine connection...")
    
    try:
        import ee
        ee.Initialize(project='sar-flood-detection')
        
        # Try a simple operation
        point = ee.Geometry.Point([0, 0])
        image = ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(point).first()
        
        print("  GEE authentication successful")
        print("  Can access Sentinel-1 data")
        print("Google Earth Engine ready\n")
        return True
    except Exception as e:
        print(f"  GEE Error: {e}")
        print("\nGEE authentication failed")
        print("Run: earthengine authenticate")
        return False


def test_database():
    """Test database initialization."""
    print("Testing database...")
    
    try:
        from models import init_db, get_session, AOI
        
        # Initialize
        init_db()
        print("  Database schema created")
        
        # Test connection
        session = get_session()
        aois = session.query(AOI).all()
        session.close()
        print(f"  Database accessible ({len(aois)} AOIs)")
        
        print("Database ready\n")
        return True
    except Exception as e:
        print(f"  Database Error: {e}")
        print("\nDatabase test failed")
        return False


def test_config():
    """Test configuration."""
    print("Testing configuration...")
    
    try:
        from config import Config
        Config.validate()
        
        print(f"  Database: {Config.DATABASE_PATH}")
        print(f"  Check interval: {Config.CHECK_INTERVAL_HOURS} hours")
        print(f"  Change threshold: {Config.CHANGE_THRESHOLD_DB} dB")
        print(f"  Webhook configured: {'Yes' if Config.WEBHOOK_URL else 'No'}")
        
        if not Config.WEBHOOK_URL:
            print("  Warning: No webhook URL - notifications disabled")
        
        print("Configuration loaded\n")
        return True
    except Exception as e:
        print(f"  Config Error: {e}")
        print("\nConfiguration test failed")
        return False


def test_webhook():
    """Test webhook notification."""
    print("Testing webhook notification...")
    
    try:
        from notifier import Notifier
        from config import Config
        
        if not Config.WEBHOOK_URL:
            print("  Skipped (no webhook configured)")
            print("  Configure WEBHOOK_URL in .env for notifications\n")
            return True
        
        notifier = Notifier()
        success = notifier.test_connection()
        
        if success:
            print("  Webhook test message sent")
            print("  Check your Slack/Discord channel")
            print("Notifications ready\n")
            return True
        else:
            print("  Webhook test failed")
            print("  Check WEBHOOK_URL in .env\n")
            return False
    except Exception as e:
        print(f"  ✗ Webhook Error: {e}\n")
        return False


def test_gee_query():
    """Test actual GEE query functionality."""
    print("Testing GEE query functionality...")
    
    try:
        from gee_manager import GEEManager
        import json
        
        gee = GEEManager()
        
        # Test with a simple point (London)
        test_geometry = {
            "type": "Point",
            "coordinates": [-0.1276, 51.5074]
        }
        
        print("  Querying Sentinel-1 data for London...")
        latest = gee.get_latest_image(test_geometry, days_back=30)
        
        if latest:
            print(f"  Found image from {latest['date']}")
            print(f"  Image ID: {latest['image_id']}")
            print("GEE queries working\n")
            return True
        else:
            print("  No recent images (might be normal)")
            print("Query infrastructure working\n")
            return True
    except Exception as e:
        print(f"  GEE Query Error: {e}")
        print("GEE queries failed\n")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Sentinel-1 Change Detection Monitor - System Test")
    print("=" * 60)
    print()
    
    results = []
    
    # Run tests
    results.append(("Package Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Database", test_database()))
    results.append(("Google Earth Engine", test_gee()))
    results.append(("GEE Queries", test_gee_query()))
    results.append(("Webhook", test_webhook()))
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{status:8} {name}")
    
    print()
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    if passed == total:
        print(f"All tests passed ({passed}/{total})")
        print("\nYou're ready to go!")
        print("Start the application with: python app.py")
        print("Start monitoring with: python monitor.py")
        return 0
    else:
        print(f"Some tests failed ({passed}/{total} passed)")
        print("\nPlease fix the issues above before proceeding.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
