# Sentinel-1 Change Detection Monitor

An automated OSINT geospatial application that monitors user-defined Areas of Interest (AOIs) for changes using Sentinel-1 SAR satellite imagery. When changes are detected, you receive instant notifications via Slack or Discord.

## Features

- 🗺️ **Interactive Web Interface** - Draw AOIs on a map with Leaflet.js
- 🛰️ **Automated Monitoring** - Checks for new Sentinel-1 images every 6 hours
- 🔍 **SAR Change Detection** - Uses log-ratio algorithm to detect physical changes
- 📊 **Results Dashboard** - View analysis history and change visualizations
- 🔔 **Instant Notifications** - Slack/Discord webhooks when changes detected
- ☁️ **Cloud Processing** - Google Earth Engine handles heavy computation
- 🌍 **Global Coverage** - Monitor anywhere on Earth with 6-day revisit

## How It Works

1. **Draw AOIs** on the interactive map
2. **System establishes baseline** using most recent Sentinel-1 image
3. **Automated monitoring** checks for new images every 6 hours
4. **Change detection** compares new images to previous baseline
5. **Notifications sent** when significant changes detected
6. **Results viewable** in web dashboard with change maps

## Technology Stack

- **Backend**: Python 3, Flask, SQLAlchemy
- **Satellite Data**: Google Earth Engine (Sentinel-1 GRD)
- **Frontend**: Leaflet.js, Leaflet.Draw
- **Database**: SQLite
- **Notifications**: Webhook integration (Slack/Discord)
- **Scheduling**: APScheduler

## Prerequisites

1. **Python 3.8+**
2. **Google Earth Engine account** (free for research/personal use)
   - Register at https://earthengine.google.com/signup/
3. **Slack or Discord webhook** (optional, for notifications)

## Installation

### 1. Clone and Install Dependencies

```powershell
cd c:\coding\osint
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Authenticate with Google Earth Engine

```powershell
earthengine authenticate
```

This will open a browser for authentication and store credentials locally.

### 3. Configure Environment

```powershell
Copy-Item .env.example .env
```

Edit `.env` file:

```env
# For Slack:
WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# For Discord:
WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/WEBHOOK/URL

# Application settings
FLASK_SECRET_KEY=your-random-secret-key
CHANGE_THRESHOLD_DB=3.0
CHECK_INTERVAL_HOURS=6
```

**Getting Webhook URLs:**
- **Slack**: https://api.slack.com/messaging/webhooks
- **Discord**: Server Settings → Integrations → Webhooks → New Webhook

### 4. Initialize Database

```powershell
python -c "from models import init_db; init_db(); print('Database initialized')"
```

## Usage

### Start the Web Application

```powershell
python app.py
```

Access at http://localhost:5000

### Start the Monitoring Service

In a separate terminal:

```powershell
.\venv\Scripts\Activate.ps1
python monitor.py
```

This runs continuously, checking for new images every 6 hours.

### Using the Application

1. **Draw AOI**: Click the polygon tool on the map and draw your area
2. **Name it**: Enter a descriptive name when prompted
3. **Wait**: System establishes baseline automatically (may take 30-60 seconds)
4. **Monitor**: Service checks for new images every 6 hours
5. **Get Alerted**: Receive notification when changes detected
6. **View Results**: Click "Results" button to see analysis history

### Manual Analysis

To trigger immediate analysis (don't wait for automated check):

1. Click **Analyze Now** button on any AOI
2. System checks for newest available image
3. Results displayed immediately

## Change Detection Explained

The system uses **log-ratio change detection**:

- Compares SAR backscatter intensity between two dates
- **Red areas** = Decreased backscatter (deforestation, demolition, flooding)
- **Blue areas** = Increased backscatter (construction, new infrastructure)
- **Threshold**: Default 3 dB (adjustable per AOI)

### Use Cases

- **Construction monitoring** - Track building development
- **Deforestation detection** - Monitor forest loss
- **Infrastructure changes** - Ports, airports, military sites
- **Disaster assessment** - Flood extent, earthquake damage
- **Conflict monitoring** - Building destruction, new fortifications

## Configuration

### Adjust Sensitivity

Higher threshold = fewer false positives, may miss small changes
Lower threshold = more sensitive, more false positives

```python
# In web UI: Edit AOI → Set custom threshold
# Or in .env:
CHANGE_THRESHOLD_DB=3.0  # Default
```

### Monitoring Frequency

```env
CHECK_INTERVAL_HOURS=6  # Check every 6 hours (default)
```

Sentinel-1 revisit is 6 days globally, 3 days in some areas. Checking more frequently than every 6 hours won't find more images but won't hurt.

## Project Structure

```
osint/
├── app.py                 # Flask web application
├── monitor.py             # Automated monitoring service
├── models.py              # Database models (SQLAlchemy)
├── config.py              # Configuration management
├── gee_manager.py         # Google Earth Engine interface
├── change_detector.py     # Change detection algorithms
├── notifier.py            # Webhook notification system
├── templates/
│   ├── index.html         # Main map interface
│   └── results.html       # Analysis results dashboard
├── requirements.txt       # Python dependencies
├── .env.example           # Example configuration
└── satellite_monitor.db   # SQLite database (created on first run)
```

## Troubleshooting

### "GEE initialization failed"

Run authentication again:
```powershell
earthengine authenticate
```

### "No baseline image"

Wait for initialization after creating AOI. Check logs - if AOI is in remote area with no recent Sentinel-1 coverage, it may take time.

### False Positives

SAR change detection can trigger on:
- Rainfall/soil moisture changes
- Seasonal vegetation growth
- Agricultural activities
- Water surface roughness (wind)

Solutions:
- Increase threshold (try 4-5 dB)
- Mark false positives in results page
- Focus on built environments (less vegetation)

### No Notifications

1. Test webhook: Edit `notifier.py` and run:
   ```python
   from notifier import Notifier
   n = Notifier()
   n.test_connection()
   ```
2. Check webhook URL format in `.env`
3. Verify webhook hasn't been deleted in Slack/Discord

## Performance Notes

- **Processing time**: 10-30 seconds per AOI per analysis (cloud-based)
- **Database**: SQLite sufficient for <100 AOIs
- **GEE quota**: Free tier supports ~10 AOIs easily
- **Storage**: Minimal (no raw images stored locally)

## Upgrading to Multi-User

For production with multiple users:

1. Switch to PostgreSQL with PostGIS
2. Add user authentication (Flask-Login)
3. Deploy with Gunicorn + Nginx
4. Use cloud scheduler (AWS Lambda, Azure Functions)
5. Add API rate limiting

## References

- [Sentinel-1 Documentation](https://sentinel.esa.int/web/sentinel/missions/sentinel-1)
- [Google Earth Engine](https://earthengine.google.com/)
- [SAR Change Detection Tutorial](https://developers.google.com/earth-engine/tutorials/community/detecting-changes-in-sentinel-1-imagery-pt-1)
- [Mort Canty's SAR Tools](https://github.com/mortcanty/SARDocker)

## License

This is an educational/research project. Ensure compliance with:
- Google Earth Engine Terms of Service
- Copernicus Sentinel Data Terms
- Your jurisdiction's laws regarding OSINT activities

## Security Notes

For production use:
- Use proper secrets management (not .env files)
- Add authentication/authorization
- Rate limit API endpoints
- Validate all user inputs
- Use HTTPS
- Don't expose internal URLs in notifications

---

**Made for OSINT researchers, geospatial analysts, and curious minds.**

For questions or issues, check the code comments or modify to your needs!
