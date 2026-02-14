"""
Flask web application for Sentinel-1 change detection monitoring.
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
from models import init_db, get_session, AOI, Analysis
from config import Config
from gee_manager import GEEManager
from change_detector import ChangeDetector

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Initialize database
init_db()


@app.route('/')
def index():
    """Main page with map interface."""
    return render_template('index.html')


@app.route('/api/aois', methods=['GET'])
def get_aois():
    """Get all AOIs."""
    session = get_session()
    try:
        aois = session.query(AOI).all()
        return jsonify([{
            'id': aoi.id,
            'name': aoi.name,
            'geometry': json.loads(aoi.geometry),
            'created_date': aoi.created_date.isoformat(),
            'active': aoi.active,
            'last_checked': aoi.last_checked.isoformat() if aoi.last_checked else None,
            'threshold_db': aoi.threshold_db,
            'orbit_direction': aoi.orbit_direction,
            'relative_orbit_number': aoi.relative_orbit_number,
            'platform_number': aoi.platform_number
        } for aoi in aois])
    finally:
        session.close()


@app.route('/api/aois', methods=['POST'])
def create_aoi():
    """Create a new AOI."""
    data = request.get_json()
    
    if not data.get('name') or not data.get('geometry'):
        return jsonify({'error': 'Name and geometry required'}), 400
    
    session = get_session()
    try:
        # Create new AOI
        aoi = AOI(
            name=data['name'],
            geometry=json.dumps(data['geometry']),
            threshold_db=data.get('threshold_db', Config.CHANGE_THRESHOLD_DB)
        )
        session.add(aoi)
        session.commit()
        
        # Initialize baseline
        try:
            gee = GEEManager()
            latest = gee.get_latest_image(data['geometry'])
            
            if latest:
                # Store baseline orbit properties for consistent change detection
                aoi.orbit_direction = latest.get('orbit_direction')
                aoi.relative_orbit_number = latest.get('relative_orbit_number')
                aoi.platform_number = latest.get('platform_number')
                
                # Create initial baseline analysis
                analysis = Analysis(
                    aoi_id=aoi.id,
                    reference_date=latest['date'],
                    new_image_date=latest['date'],
                    analysis_date=datetime.utcnow(),
                    changes_detected=False,
                    change_score=0.0,
                    notes='Baseline image',
                    ref_image_url='',
                    new_image_url=''
                )
                session.add(analysis)
                aoi.last_checked = latest['date']
                session.commit()
        except Exception as e:
            print(f"Warning: Could not initialize baseline: {e}")
        
        return jsonify({
            'id': aoi.id,
            'name': aoi.name,
            'geometry': json.loads(aoi.geometry),
            'created_date': aoi.created_date.isoformat(),
            'active': aoi.active
        }), 201
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/aois/<int:aoi_id>', methods=['PUT'])
def update_aoi(aoi_id):
    """Update an AOI."""
    data = request.get_json()
    session = get_session()
    
    try:
        aoi = session.get(AOI, aoi_id)
        if not aoi:
            return jsonify({'error': 'AOI not found'}), 404
        
        if 'name' in data:
            aoi.name = data['name']
        if 'active' in data:
            aoi.active = data['active']
        if 'threshold_db' in data:
            aoi.threshold_db = data['threshold_db']
        
        session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/aois/<int:aoi_id>', methods=['DELETE'])
def delete_aoi(aoi_id):
    """Delete an AOI and its analyses."""
    session = get_session()
    
    try:
        aoi = session.get(AOI, aoi_id)
        if not aoi:
            return jsonify({'error': 'AOI not found'}), 404
        
        session.delete(aoi)
        session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/aois/<int:aoi_id>/analyze', methods=['POST'])
def manual_analyze(aoi_id):
    """Manually trigger analysis for an AOI."""
    session = get_session()
    
    try:
        aoi = session.get(AOI, aoi_id)
        if not aoi:
            return jsonify({'error': 'AOI not found'}), 404
        
        # Get geometry
        geometry = json.loads(aoi.geometry)
        
        # Get latest analysis to use as reference
        last_analysis = (session.query(Analysis)
                        .filter_by(aoi_id=aoi_id)
                        .order_by(Analysis.new_image_date.desc())
                        .first())
        
        if not last_analysis:
            return jsonify({'error': 'No baseline image. Wait for initialization.'}), 400
        
        # Check for new images with orbit filtering for consistent geometry
        gee = GEEManager()
        new_images = gee.check_for_new_images(
            geometry, 
            last_analysis.new_image_date,
            orbit_direction=aoi.orbit_direction,
            relative_orbit=aoi.relative_orbit_number
            # Platform filtering optional - allow S1A/S1C mixing on same orbit
        )
        
        if not new_images:
            return jsonify({'message': 'No new images available'}), 200
        
        # Analyze the most recent new image
        detector = ChangeDetector()
        results = detector.detect_changes_for_aoi(
            geometry,
            last_analysis.new_image_date,
            new_images[0]['date'],
            aoi.threshold_db
        )
        
        # Save analysis
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
            new_image_url=results.get('new_image_url', '')
        )
        session.add(analysis)
        aoi.last_checked = datetime.utcnow()
        session.commit()
        
        return jsonify({
            'success': True,
            'analysis_id': analysis.id,
            'changes_detected': results['changes_detected'],
            'results': results
        })
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/analyses/<int:aoi_id>')
def get_analyses(aoi_id):
    """Get all analyses for an AOI."""
    session = get_session()
    
    try:
        analyses = (session.query(Analysis)
                   .filter_by(aoi_id=aoi_id)
                   .order_by(Analysis.new_image_date.desc())
                   .all())
        
        return jsonify([{
            'id': a.id,
            'reference_date': a.reference_date.isoformat(),
            'new_image_date': a.new_image_date.isoformat(),
            'analysis_date': a.analysis_date.isoformat(),
            'changes_detected': a.changes_detected,
            'change_score': a.change_score,
            'change_area_sqkm': a.change_area_sqkm,
            'change_percentage': a.change_percentage,
            'change_map_url': a.change_map_url,
            'ref_image_url': a.ref_image_url,
            'new_image_url': a.new_image_url,
            'false_positive': a.false_positive,
            'notes': a.notes
        } for a in analyses])
    finally:
        session.close()


@app.route('/results/<int:aoi_id>')
def results(aoi_id):
    """Results page for an AOI."""
    return render_template('results.html', aoi_id=aoi_id)


@app.route('/timeseries/<int:aoi_id>')
def timeseries(aoi_id):
    """Time series analysis page for an AOI."""
    return render_template('timeseries.html', aoi_id=aoi_id)


@app.route('/api/timeseries/<int:aoi_id>')
def get_timeseries_images(aoi_id):
    """Get Sentinel-1 images for time series analysis."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date required'}), 400
    
    session = get_session()
    try:
        aoi = session.get(AOI, aoi_id)
        if not aoi:
            return jsonify({'error': 'AOI not found'}), 404
        
        geometry = json.loads(aoi.geometry)
        
        # Get images using GEE
        gee = GEEManager()
        images = gee.get_images_for_timeseries(
            geometry,
            start_date,
            end_date,
            orbit_direction=aoi.orbit_direction,
            relative_orbit=aoi.relative_orbit_number,
            platform=aoi.platform_number,
            max_images=50
        )
        
        return jsonify({
            'success': True,
            'aoi_name': aoi.name,
            'orbit_config': {
                'orbit_direction': aoi.orbit_direction,
                'relative_orbit': aoi.relative_orbit_number,
                'platform': aoi.platform_number
            },
            'total_images': len(images),
            'images': images
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/analyses/<int:analysis_id>/feedback', methods=['POST'])
def mark_false_positive(analysis_id):
    """Mark an analysis as false positive."""
    data = request.get_json()
    session = get_session()
    
    try:
        analysis = session.get(Analysis, analysis_id)
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        analysis.false_positive = data.get('false_positive', True)
        analysis.user_notes = data.get('notes', '')
        session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


if __name__ == '__main__':
    Config.validate()
    app.run(debug=Config.DEBUG, host=Config.FLASK_HOST, port=Config.FLASK_PORT)
