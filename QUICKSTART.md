# Quick Start Guide

## Prerequisites Check

Before starting, ensure you have:

- [ ] Python 3.8 or higher installed
- [ ] Google Earth Engine account (register at https://earthengine.google.com/signup/)
- [ ] Slack or Discord webhook URL (optional but recommended)

## Setup Steps

### 1. Create Virtual Environment

```powershell
# Navigate to project directory
cd c:\coding\osint

# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

This will install:
- Flask (web framework)
- earthengine-api (satellite data access)
- SQLAlchemy (database)
- APScheduler (automated monitoring)
- And other required packages

### 3. Authenticate with Google Earth Engine

```powershell
earthengine authenticate
```

**What happens:**
1. Browser opens with Google authentication
2. Sign in with your Google account
3. Authorize Earth Engine access
4. Credentials stored locally

**Note:** This is a one-time setup. Credentials persist.

### 4. Create Configuration File

```powershell
# Copy example config
Copy-Item .env.example .env

# Edit the file
notepad .env
```

**Minimum required settings:**

```env
WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
FLASK_SECRET_KEY=change-this-to-random-string
```

**Optional settings:**

```env
# How often to check for new images (hours)
CHECK_INTERVAL_HOURS=6

# Change detection sensitivity (dB)
# Lower = more sensitive, more false positives
# Higher = less sensitive, may miss changes
CHANGE_THRESHOLD_DB=3.0

# Database file path
DATABASE_PATH=satellite_monitor.db
```

### 5. Initialize Database

```powershell
python -c "from models import init_db; init_db(); print('✓ Database initialized')"
```

### 6. Verify Setup

```powershell
# Test GEE connection
python -c "import ee; ee.Initialize(); print('✓ GEE connection successful')"

# Test webhook (if configured)
python -c "from notifier import Notifier; Notifier().test_connection()"
```

## Running the Application

### Option A: Web Interface Only

Perfect for testing and manual analysis:

```powershell
python app.py
```

Open browser to http://localhost:5000

### Option B: Full System (Web + Automated Monitoring)

For production use with automatic checks:

**Terminal 1 - Web Application:**
```powershell
.\venv\Scripts\Activate.ps1
python app.py
```

**Terminal 2 - Monitor Service:**
```powershell
.\venv\Scripts\Activate.ps1
python monitor.py
```

The monitor runs continuously and checks every 6 hours (or your configured interval).

## First Usage

1. **Open** http://localhost:5000
2. **Click** the polygon draw tool (square icon on map)
3. **Draw** an area on the map (click corners, double-click to finish)
4. **Name** your AOI when prompted
5. **Wait** ~30 seconds for baseline initialization
6. **Monitor** will check automatically, or click "Analyze Now"

## Testing with Known Changes

Want to see it work immediately? Try these locations with known changes:

### Construction Sites
- **Dubai, UAE**: Rapid development areas
- **Coordinates**: 25.2048, 55.2708

### Deforestation
- **Amazon rainforest**: Active logging areas
- **Coordinates**: -3.4653, -62.2159

### Urban Development
- **Beijing, China**: Suburban expansion
- **Coordinates**: 39.9042, 116.4074

**How to test:**
1. Draw AOI over one of these locations
2. Click "Analyze Now" after baseline is set
3. Compare with historical imagery

## Troubleshooting

### "ee.Authenticate() not called"

Solution:
```powershell
earthengine authenticate
```

### Package Installation Fails

Try:
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Can't Access Web Interface

1. Check if port 5000 is available
2. Try: `python app.py` (should see "Running on http://0.0.0.0:5000")
3. Access via http://localhost:5000

### No Baseline Image Created

Common causes:
- AOI in ocean/polar region (no Sentinel-1 coverage)
- Very recent, no data yet
- GEE authentication issue

Check logs in terminal for specific error.

### False Positives

SAR is sensitive to:
- Rain/moisture
- Vegetation growth
- Seasonal changes

Try:
1. Increase threshold to 4-5 dB
2. Focus on urban/built areas
3. Mark false positives in results dashboard

## Next Steps

### Customize Thresholds

Each AOI can have custom sensitivity:
1. Go to AOI in web interface
2. Click edit
3. Set custom threshold

### Add More AOIs

You can monitor multiple locations simultaneously. The system handles them all automatically.

### Schedule as Service

#### Windows (Task Scheduler):

1. Open Task Scheduler
2. Create Basic Task
3. Action: Start a program
4. Program: `C:\coding\osint\venv\Scripts\python.exe`
5. Arguments: `C:\coding\osint\monitor.py`
6. Working directory: `C:\coding\osint`

#### Linux (systemd):

Create `/etc/systemd/system/sentinel-monitor.service`:

```ini
[Unit]
Description=Sentinel-1 Change Detection Monitor
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/osint
ExecStart=/path/to/osint/venv/bin/python monitor.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable sentinel-monitor
sudo systemctl start sentinel-monitor
```

## Architecture Overview

```
┌─────────────────┐
│  Web Browser    │
│  (Leaflet Map)  │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  Flask App      │
│  (app.py)       │
└────────┬────────┘
         │
         ├──────────┬──────────┬──────────┐
         ▼          ▼          ▼          ▼
    ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │Database│ │  GEE   │ │Monitor │ │Notifier│
    │SQLite  │ │Manager │ │Service │ │Webhook │
    └────────┘ └────┬───┘ └────┬───┘ └────┬───┘
                    │          │          │
                    ▼          ▼          ▼
              ┌──────────────────────────────┐
              │  Google Earth Engine (Cloud) │
              │  - Sentinel-1 Data           │
              │  - Image Processing          │
              │  - Change Detection          │
              └──────────────────────────────┘
```

## Performance Expectations

- **Baseline creation**: 30-60 seconds
- **Change detection**: 10-30 seconds per analysis
- **Monitoring frequency**: Every 6 hours (configurable)
- **Sentinel-1 revisit**: 6 days globally, 3 days in some regions
- **Expected changes**: ~2 new images per AOI per month

## Getting Help

1. **Check logs**: Terminal output shows detailed error messages
2. **Review code**: All files are documented with comments
3. **GEE documentation**: https://developers.google.com/earth-engine
4. **Sentinel-1 info**: https://sentinel.esa.int/web/sentinel/missions/sentinel-1

## What's Next?

Potential enhancements:
- Multi-temporal analysis (require change in multiple dates)
- Different change detection algorithms (coherence, statistical)
- Integration with other data sources (weather, land cover)
- Email notifications
- API for external integrations
- Machine learning for false positive reduction
- Historical analysis (bulk process past dates)

Happy monitoring! 🛰️
