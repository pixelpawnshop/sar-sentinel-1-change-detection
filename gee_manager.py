"""
Google Earth Engine interface for Sentinel-1 data access and processing.
"""
import ee
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from config import Config


class GEEManager:
    """Manages Google Earth Engine operations for Sentinel-1 data."""
    
    def __init__(self):
        """Initialize GEE connection."""
        try:
            ee.Initialize(project='sar-flood-detection')
        except Exception as e:
            print(f"GEE initialization failed: {e}")
            print("Run 'earthengine authenticate' to set up credentials.")
            print("Then register at: https://code.earthengine.google.com/")
            raise
    
    def get_sentinel1_collection(self, geometry: Dict, start_date: str, end_date: str, 
                                 orbit_direction: Optional[str] = None,
                                 relative_orbit: Optional[int] = None,
                                 platform: Optional[str] = None) -> ee.ImageCollection:
        """
        Get Sentinel-1 image collection for an AOI and date range.
        
        Args:
            geometry: GeoJSON geometry dict
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
            orbit_direction: Optional orbit direction filter ('ASCENDING' or 'DESCENDING')
            relative_orbit: Optional relative orbit number (1-175)
            platform: Optional platform filter ('A' or 'C')
            
        Returns:
            ee.ImageCollection: Filtered Sentinel-1 collection
        """
        # Convert GeoJSON to ee.Geometry
        aoi = ee.Geometry(geometry)
        
        # Query Sentinel-1 collection
        collection = (ee.ImageCollection(Config.SENTINEL1_COLLECTION)
            .filterBounds(aoi)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.eq('instrumentMode', Config.INSTRUMENT_MODE))
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', Config.POLARIZATION))
            .select(Config.POLARIZATION)
        )
        
        # Apply orbit filters for consistent geometry
        if orbit_direction:
            collection = collection.filter(ee.Filter.eq('orbitProperties_pass', orbit_direction))
        if relative_orbit is not None:
            collection = collection.filter(ee.Filter.eq('relativeOrbitNumber_start', relative_orbit))
        if platform:
            collection = collection.filter(ee.Filter.eq('platform_number', platform))
        
        return collection
    
    def get_latest_image(self, geometry: Dict, days_back: int = 30) -> Optional[Dict]:
        """
        Get the most recent Sentinel-1 image for an AOI.
        
        Args:
            geometry: GeoJSON geometry dict
            days_back: How many days back to search
            
        Returns:
            Dict with image info or None if no images found
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        collection = self.get_sentinel1_collection(
            geometry,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # Get the most recent image
        image_list = collection.sort('system:time_start', False).limit(1)
        
        size = image_list.size().getInfo()
        if size == 0:
            return None
        
        image = ee.Image(image_list.first())
        image_date = datetime.fromtimestamp(image.get('system:time_start').getInfo() / 1000)
        
        return {
            'image': image,
            'date': image_date,
            'image_id': image.get('system:index').getInfo(),
            'orbit_direction': image.get('orbitProperties_pass').getInfo(),
            'relative_orbit_number': image.get('relativeOrbitNumber_start').getInfo(),
            'platform_number': image.get('platform_number').getInfo()
        }
    
    def get_image_by_date_range(self, geometry: Dict, target_date: datetime, 
                                 tolerance_days: int = 3) -> Optional[Dict]:
        """
        Get Sentinel-1 image closest to target date within tolerance.
        
        Args:
            geometry: GeoJSON geometry dict
            target_date: Target datetime
            tolerance_days: Max days away from target
            
        Returns:
            Dict with image info or None
        """
        start_date = target_date - timedelta(days=tolerance_days)
        end_date = target_date + timedelta(days=tolerance_days)
        
        collection = self.get_sentinel1_collection(
            geometry,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # Get the image closest to target date
        target_millis = int(target_date.timestamp() * 1000)
        
        sorted_collection = collection.map(
            lambda img: img.set('time_diff',
                ee.Number(img.get('system:time_start')).subtract(target_millis).abs()
            )
        ).sort('time_diff')
        
        size = sorted_collection.size().getInfo()
        if size == 0:
            return None
        
        image = ee.Image(sorted_collection.first())
        image_date = datetime.fromtimestamp(image.get('system:time_start').getInfo() / 1000)
        
        return {
            'image': image,
            'date': image_date,
            'image_id': image.get('system:index').getInfo(),
            'orbit_direction': image.get('orbitProperties_pass').getInfo(),
            'relative_orbit_number': image.get('relativeOrbitNumber_start').getInfo(),
            'platform_number': image.get('platform_number').getInfo()
        }
    
    def check_for_new_images(self, geometry: Dict, last_checked: datetime,
                            orbit_direction: Optional[str] = None,
                            relative_orbit: Optional[int] = None,
                            platform: Optional[str] = None) -> List[Dict]:
        """
        Check if new images are available since last check.
        
        Args:
            geometry: GeoJSON geometry dict
            last_checked: Last check datetime
            orbit_direction: Optional orbit direction filter
            relative_orbit: Optional relative orbit number
            platform: Optional platform filter
            
        Returns:
            List of new image info dicts
        """
        collection = self.get_sentinel1_collection(
            geometry,
            last_checked.strftime('%Y-%m-%d'),
            datetime.utcnow().strftime('%Y-%m-%d'),
            orbit_direction=orbit_direction,
            relative_orbit=relative_orbit,
            platform=platform
        )
        
        # Sort by date
        collection = collection.sort('system:time_start', False)
        
        # Get image list
        image_list = collection.toList(collection.size())
        size = collection.size().getInfo()
        
        new_images = []
        for i in range(size):
            image = ee.Image(image_list.get(i))
            image_date = datetime.fromtimestamp(image.get('system:time_start').getInfo() / 1000)
            
            # Only include if after last checked
            if image_date > last_checked:
                new_images.append({
                    'image': image,
                    'date': image_date,
                    'image_id': image.get('system:index').getInfo(),
                    'orbit_direction': image.get('orbitProperties_pass').getInfo(),
                    'relative_orbit_number': image.get('relativeOrbitNumber_start').getInfo(),
                    'platform_number': image.get('platform_number').getInfo()
                })
        
        return new_images
    
    def apply_speckle_filter(self, image: ee.Image) -> ee.Image:
        """
        Apply speckle filtering to reduce noise.
        
        Args:
            image: Input SAR image
            
        Returns:
            Filtered image
        """
        # Use focal median filter (effective for SAR speckle)
        filtered = image.focal_median(
            radius=Config.SPECKLE_FILTER_RADIUS,
            kernelType='square',
            units='pixels'
        )
        return filtered
    
    def clip_to_aoi(self, image: ee.Image, geometry: Dict) -> ee.Image:
        """
        Clip image to AOI geometry.
        
        Args:
            image: Input image
            geometry: GeoJSON geometry dict
            
        Returns:
            Clipped image
        """
        aoi = ee.Geometry(geometry)
        return image.clip(aoi)
    
    def get_images_for_timeseries(self, geometry: Dict, start_date: str, end_date: str,
                                   orbit_direction: Optional[str] = None,
                                   relative_orbit: Optional[int] = None,
                                   platform: Optional[str] = None,
                                   max_images: int = 50) -> List[Dict]:
        """
        Get Sentinel-1 images for time series analysis.
        
        Args:
            geometry: GeoJSON geometry dict
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
            orbit_direction: Optional orbit direction filter
            relative_orbit: Optional relative orbit number
            platform: Optional platform filter
            max_images: Maximum number of images to return (default 50)
            
        Returns:
            List of dicts with image metadata and thumbnail URLs
        """
        # Get collection with orbit filtering
        collection = self.get_sentinel1_collection(
            geometry,
            start_date,
            end_date,
            orbit_direction=orbit_direction,
            relative_orbit=relative_orbit,
            platform=platform
        )
        
        # Sort by date (oldest first for time series)
        collection = collection.sort('system:time_start', True)
        
        # Check total count
        total_count = collection.size().getInfo()
        
        if total_count == 0:
            return []
        
        # Limit to max_images
        if total_count > max_images:
            collection = collection.limit(max_images)
            actual_count = max_images
        else:
            actual_count = total_count
        
        # Convert to list for iteration
        image_list = collection.toList(actual_count)
        
        # Process each image
        images = []
        aoi = ee.Geometry(geometry)
        
        for i in range(actual_count):
            try:
                image = ee.Image(image_list.get(i))
                
                # Get metadata
                image_id = image.get('system:index').getInfo()
                timestamp = image.get('system:time_start').getInfo()
                image_date = datetime.fromtimestamp(timestamp / 1000)
                orbit_dir = image.get('orbitProperties_pass').getInfo()
                rel_orbit = image.get('relativeOrbitNumber_start').getInfo()
                platform_num = image.get('platform_number').getInfo()
                
                # Apply speckle filter
                filtered = self.apply_speckle_filter(image)
                clipped = filtered.clip(aoi)
                
                # Generate thumbnail URL (VV polarization, grayscale)
                vv_band = clipped.select('VV')
                
                # Visualization parameters for SAR (dB scale)
                # Dimensions capped at 1200px to stay under GEE's 50MB limit
                vis_params = {
                    'bands': ['VV'],
                    'min': -25,
                    'max': 5,
                    'dimensions': 1200,
                    'format': 'png',
                    'crs': 'EPSG:3857'
                }
                
                thumbnail_url = vv_band.getThumbURL(vis_params)
                
                images.append({
                    'image_id': image_id,
                    'date': image_date.isoformat(),
                    'date_formatted': image_date.strftime('%Y-%m-%d %H:%M UTC'),
                    'thumbnail_url': thumbnail_url,
                    'orbit_direction': orbit_dir,
                    'relative_orbit': rel_orbit,
                    'platform': f'Sentinel-1{platform_num}',
                    'index': i
                })
                
            except Exception as e:
                print(f"Error processing image {i}: {e}")
                continue
        
        return images
