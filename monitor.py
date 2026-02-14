"""
Automated monitoring service for Sentinel-1 change detection.

This script runs continuously and checks for new satellite images at configured intervals.
When new images are available, it performs change detection and sends notifications.
"""
import time
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

from models import get_session, AOI, Analysis
from gee_manager import GEEManager
from change_detector import ChangeDetector
from notifier import Notifier
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SatelliteMonitor:
    """Monitors AOIs for new satellite imagery and performs change detection."""
    
    def __init__(self):
        """Initialize the monitor."""
        self.gee = GEEManager()
        self.detector = ChangeDetector()
        self.notifier = Notifier()
        logger.info("Satellite Monitor initialized")
    
    def check_all_aois(self):
        """Check all active AOIs for new images and perform change detection."""
        logger.info("=" * 60)
        logger.info("Starting monitoring cycle")
        logger.info("=" * 60)
        
        session = get_session()
        
        try:
            # Get all active AOIs
            aois = session.query(AOI).filter_by(active=True).all()
            logger.info(f"Found {len(aois)} active AOIs to check")
            
            if len(aois) == 0:
                logger.info("No active AOIs found. Skipping cycle.")
                return
            
            for aoi in aois:
                try:
                    self.check_aoi(aoi, session)
                except Exception as e:
                    logger.error(f"Error checking AOI {aoi.id} ({aoi.name}): {e}", exc_info=True)
                    continue
            
            logger.info("Monitoring cycle completed")
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}", exc_info=True)
        finally:
            session.close()
    
    def check_aoi(self, aoi: AOI, session):
        """
        Check a single AOI for new images and perform change detection.
        
        Args:
            aoi: AOI model instance
            session: Database session
        """
        logger.info(f"Checking AOI {aoi.id}: {aoi.name}")
        
        # Parse geometry
        geometry = json.loads(aoi.geometry)
        
        # Get the most recent analysis for this AOI
        last_analysis = (session.query(Analysis)
                        .filter_by(aoi_id=aoi.id)
                        .order_by(Analysis.new_image_date.desc())
                        .first())
        
        if not last_analysis:
            logger.warning(f"  No baseline for AOI {aoi.id}. Skipping (needs initialization)")
            return
        
        # Check for new images since last analysis
        try:
            new_images = self.gee.check_for_new_images(
                geometry,
                last_analysis.new_image_date
            )
        except Exception as e:
            logger.error(f"  Error querying GEE for new images: {e}")
            return
        
        if not new_images:
            logger.info(f"  No new images available (last checked: {last_analysis.new_image_date})")
            aoi.last_checked = datetime.utcnow()
            session.commit()
            return
        
        logger.info(f"  Found {len(new_images)} new image(s)")
        
        # Analyze the most recent new image
        latest_new_image = new_images[0]  # Already sorted by date descending
        logger.info(f"  Analyzing image from {latest_new_image['date']}")
        
        try:
            # Perform change detection
            results = self.detector.detect_changes_for_aoi(
                geometry,
                last_analysis.new_image_date,
                latest_new_image['date'],
                aoi.threshold_db
            )
            
            if 'error' in results:
                logger.error(f"  Change detection error: {results['error']}")
                return
            
            # Save analysis to database
            analysis = Analysis(
                aoi_id=aoi.id,
                reference_date=last_analysis.new_image_date,
                new_image_date=results['new_date_actual'],
                changes_detected=results['changes_detected'],
                change_score=results['avg_change_db'],
                change_area_sqkm=results['change_area_sqkm'],
                change_percentage=results['change_percentage'],
                change_map_url=results.get('change_map_url', ''),
                ref_image_url=results.get('ref_image_url', ''),
                new_image_url=results.get('new_image_url', ''),
                notes=f"Automatic analysis (threshold: {aoi.threshold_db} dB)"
            )
            session.add(analysis)
            
            # Update last checked time
            aoi.last_checked = datetime.utcnow()
            session.commit()
            
            logger.info(f"  Analysis complete:")
            logger.info(f"    Changes detected: {results['changes_detected']}")
            logger.info(f"    Changed area: {results['change_area_sqkm']:.4f} km²")
            logger.info(f"    Change percentage: {results['change_percentage']:.2f}%")
            logger.info(f"    Magnitude: {results['avg_change_db']:.2f} dB")
            
            # Send notification if changes detected
            if results['changes_detected']:
                logger.info(f"  Sending notification...")
                try:
                    self.notifier.send_change_alert(aoi.name, results, aoi.id)
                    logger.info(f"  Notification sent")
                except Exception as e:
                    logger.error(f"  Notification failed: {e}")
            
        except Exception as e:
            logger.error(f"  Error during change detection: {e}", exc_info=True)
            session.rollback()


def main():
    """Main entry point for the monitoring service."""
    logger.info("=" * 60)
    logger.info("Sentinel-1 Change Detection Monitor")
    logger.info("=" * 60)
    logger.info(f"Check interval: {Config.CHECK_INTERVAL_HOURS} hours")
    logger.info(f"Change threshold: {Config.CHANGE_THRESHOLD_DB} dB")
    logger.info(f"Webhook configured: {'Yes' if Config.WEBHOOK_URL else 'No'}")
    logger.info("=" * 60)
    
    # Test webhook if configured
    if Config.WEBHOOK_URL:
        logger.info("Testing webhook connection...")
        notifier = Notifier()
        if notifier.test_connection():
            logger.info("Webhook test successful")
        else:
            logger.warning("Webhook test failed - notifications may not work")
    
    # Create monitor instance
    monitor = SatelliteMonitor()
    
    # Create scheduler
    scheduler = BlockingScheduler()
    
    # Add job to run every N hours
    scheduler.add_job(
        monitor.check_all_aois,
        trigger=IntervalTrigger(hours=Config.CHECK_INTERVAL_HOURS),
        id='check_aois',
        name='Check all AOIs for new images',
        replace_existing=True
    )
    
    logger.info(f"Scheduler started. Will check every {Config.CHECK_INTERVAL_HOURS} hours.")
    logger.info("Press Ctrl+C to stop.")
    
    # Run once immediately on startup
    logger.info("Running initial check...")
    try:
        monitor.check_all_aois()
    except Exception as e:
        logger.error(f"Error in initial check: {e}", exc_info=True)
    
    # Start scheduler
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down monitor...")
        scheduler.shutdown()
        logger.info("Monitor stopped")


if __name__ == '__main__':
    main()
