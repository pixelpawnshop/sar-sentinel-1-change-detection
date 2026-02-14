"""
Sentinel-1 change detection algorithms using Google Earth Engine.
"""
import ee
from typing import Dict, Tuple
from config import Config
from gee_manager import GEEManager


class ChangeDetector:
    """Implements SAR change detection algorithms."""
    
    def __init__(self):
        """Initialize change detector."""
        self.gee = GEEManager()
    
    def log_ratio_change_detection(self, 
                                   reference_image: ee.Image, 
                                   new_image: ee.Image,
                                   geometry: Dict,
                                   threshold_db: float = None) -> Dict:
        """
        Perform log-ratio change detection on two SAR images.
        
        The log-ratio method compares intensities:
        change = 10 * log10(new / reference)
        
        Positive values = increase in backscatter (new construction, flooding)
        Negative values = decrease in backscatter (deforestation, demolition)
        
        Args:
            reference_image: Earlier image (baseline)
            new_image: Later image (to compare)
            geometry: AOI geometry for clipping
            threshold_db: Change threshold in dB (default from config)
            
        Returns:
            Dict with change statistics and visualization URL
        """
        if threshold_db is None:
            threshold_db = Config.CHANGE_THRESHOLD_DB
        
        aoi = ee.Geometry(geometry)
        
        # Orbit compatibility check for reduced false positives
        try:
            ref_orbit = reference_image.get('orbitProperties_pass').getInfo()
            new_orbit = new_image.get('orbitProperties_pass').getInfo()
            
            if ref_orbit != new_orbit:
                print(f"WARNING: Orbit direction mismatch! Reference: {ref_orbit}, New: {new_orbit}")
                print(f"   This may cause false positives due to different viewing geometry.")
        except Exception as e:
            # Handle cases where orbit properties might not be available
            print(f"Note: Could not verify orbit consistency: {e}")
        
        # Apply speckle filtering
        ref_filtered = self.gee.apply_speckle_filter(reference_image)
        new_filtered = self.gee.apply_speckle_filter(new_image)
        
        # Clip to AOI
        ref_clipped = self.gee.clip_to_aoi(ref_filtered, geometry)
        new_clipped = self.gee.clip_to_aoi(new_filtered, geometry)
        
        # Calculate log-ratio
        # Add small value to avoid log(0)
        epsilon = 1e-10
        ref_safe = ref_clipped.add(epsilon)
        new_safe = new_clipped.add(epsilon)
        
        # Log ratio in dB: 10 * log10(new / ref)
        log_ratio = new_safe.divide(ref_safe).log10().multiply(10)
        
        # Create change mask (absolute change > threshold)
        change_mask = log_ratio.abs().gt(threshold_db)
        
        # Calculate statistics within AOI
        aoi_area = aoi.area().divide(1e6).getInfo()  # Convert to km²
        
        # Get change statistics
        stats = change_mask.reduceRegion(
            reducer=ee.Reducer.sum().combine(
                reducer2=ee.Reducer.mean(),
                sharedInputs=True
            ),
            geometry=aoi,
            scale=10,  # Sentinel-1 GRD resolution
            maxPixels=1e9
        ).getInfo()
        
        # Calculate changed pixels and area
        # Each pixel is 10m x 10m = 100 m² = 0.0001 km²
        pixel_area_sqkm = 0.0001
        
        # Get the polarization band name (VV or VH)
        band_name = Config.POLARIZATION
        changed_pixels = stats.get(f'{band_name}_sum', 0)
        change_area_sqkm = changed_pixels * pixel_area_sqkm
        change_percentage = (change_area_sqkm / aoi_area * 100) if aoi_area > 0 else 0
        
        # Calculate average change magnitude
        avg_change_db = log_ratio.abs().reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=10,
            maxPixels=1e9
        ).getInfo().get(band_name, 0)
        
        # Determine if significant changes detected
        changes_detected = change_area_sqkm >= Config.MIN_CHANGE_AREA_SQKM
        
        # Generate visualization
        change_map_url = self._generate_change_visualization(
            log_ratio, change_mask, aoi, threshold_db
        )
        
        # Generate individual image thumbnails for comparison
        ref_image_url = self._generate_sar_thumbnail(ref_clipped, aoi)
        new_image_url = self._generate_sar_thumbnail(new_clipped, aoi)
        
        return {
            'changes_detected': changes_detected,
            'change_area_sqkm': round(change_area_sqkm, 4),
            'change_percentage': round(change_percentage, 2),
            'avg_change_db': round(avg_change_db, 2),
            'change_map_url': change_map_url,
            'ref_image_url': ref_image_url,
            'new_image_url': new_image_url,
            'aoi_area_sqkm': round(aoi_area, 2),
            'threshold_db': threshold_db
        }
    
    def _generate_sar_thumbnail(self, image: ee.Image, aoi: ee.Geometry) -> str:
        """
        Generate a grayscale thumbnail of SAR image.
        
        Args:
            image: SAR image
            aoi: Area of interest geometry
            
        Returns:
            URL string for thumbnail image
        """
        # Get band name
        band_name = Config.POLARIZATION
        
        # Normalize for visualization (SAR backscatter values typically -30 to 10 dB)
        vis_params = {
            'min': -25,
            'max': 5,
            'dimensions': 512,
            'region': aoi,
            'format': 'png',
            'crs': 'EPSG:3857'  # Web Mercator for consistent projection
        }
        
        try:
            url = image.select(band_name).getThumbURL(vis_params)
            return url
        except Exception as e:
            print(f"Error generating SAR thumbnail: {e}")
            return ""
    
    def _generate_change_visualization(self, 
                                       log_ratio: ee.Image, 
                                       change_mask: ee.Image,
                                       aoi: ee.Geometry,
                                       threshold_db: float) -> str:
        """
        Generate a visualization URL for the change detection results.
        
        Args:
            log_ratio: Log-ratio change image
            change_mask: Binary change mask
            aoi: Area of interest geometry
            threshold_db: Threshold used
            
        Returns:
            URL string for thumbnail image
        """
        # Create RGB visualization
        # Red = decrease, Blue = increase, Green = no change
        decrease = log_ratio.lt(-threshold_db).multiply(255)
        increase = log_ratio.gt(threshold_db).multiply(255)
        
        # Combine into RGB
        vis_image = ee.Image.rgb(
            decrease,  # Red channel
            ee.Image(0),  # Green channel (no change)
            increase   # Blue channel
        )
        
        # Get thumbnail URL
        vis_params = {
            'min': 0,
            'max': 255,
            'dimensions': 512,
            'region': aoi,
            'format': 'png',
            'crs': 'EPSG:3857'  # Web Mercator for consistent projection
        }
        
        try:
            url = vis_image.getThumbURL(vis_params)
            return url
        except Exception as e:
            print(f"Error generating visualization: {e}")
            return ""
    
    def detect_changes_for_aoi(self, 
                               aoi_geometry: Dict,
                               reference_date: 'datetime',
                               new_date: 'datetime',
                               threshold_db: float = None) -> Dict:
        """
        High-level method to detect changes between two dates for an AOI.
        
        Args:
            aoi_geometry: GeoJSON geometry
            reference_date: Date of baseline image
            new_date: Date of new image to compare
            threshold_db: Optional custom threshold
            
        Returns:
            Change detection results dict
        """
        # Get images for the two dates
        ref_info = self.gee.get_image_by_date_range(aoi_geometry, reference_date)
        new_info = self.gee.get_image_by_date_range(aoi_geometry, new_date)
        
        if not ref_info or not new_info:
            return {
                'error': 'Could not find images for specified dates',
                'changes_detected': False
            }
        
        # Perform change detection
        results = self.log_ratio_change_detection(
            ref_info['image'],
            new_info['image'],
            aoi_geometry,
            threshold_db
        )
        
        # Add image dates to results
        results['reference_date_actual'] = ref_info['date']
        results['new_date_actual'] = new_info['date']
        results['reference_image_id'] = ref_info['image_id']
        results['new_image_id'] = new_info['image_id']
        
        return results
