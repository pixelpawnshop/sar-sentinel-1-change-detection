# Sentinel-1 Change Detection Monitor

Automated monitoring of Areas of Interest (AOIs) for physical changes using Sentinel-1 SAR satellite imagery. Get instant notifications via Slack/Discord when changes are detected.

## What It Does

- Draw areas on a map to monitor
- System checks for new satellite images automatically
- Detects physical changes (construction, deforestation, flooding, etc.)
- Sends notifications when significant changes occur
- View time series analysis with playback controls
- All processing done in cloud (Google Earth Engine)

## Quick Start

### Prerequisites

1. Python 3.8+
2. Google Earth Engine account (free) - https://earthengine.google.com/signup/
3. Webhook URL from Slack or Discord (optional)

### Installation

```powershell
# Clone and setup
cd c:\coding\osint
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Authenticate with Google Earth Engine
earthengine authenticate

# Configure
Copy-Item .env.example .env
notepad .env  # Edit with your settings
```

**Required in `.env`:**
```env
GEE_PROJECT_ID=your-google-cloud-project-id
BASE_URL=http://localhost:5000
WEBHOOK_URL=https://your-webhook-url  # Optional
```

```powershell
# Initialize database
python -c "from models import init_db; init_db()"

# Run
python app.py
```

Open http://localhost:5000 and start drawing AOIs on the map.

## Usage

1. Draw AOI on map (max 5000 km²)
2. System establishes baseline (~30 seconds)
3. Click "Analyze Now" for manual check or run `python monitor.py` for automated monitoring
4. View results and time series analysis

https://github.com/user-attachments/assets/08568f8b-4f99-40ce-9f77-85cddcb8d3bd

**Automated Monitoring:** Run `python monitor.py` in separate terminal for continuous checks.

## Key Features

- **Change Detection**: Red = decrease (deforestation, flooding), Blue = increase (construction)
- **Time Series**: View up to 50 historical images with playback controls
- **Smart Scaling**: Large AOIs automatically use smaller thumbnails
- **Notifications**: Slack/Discord webhooks when changes detected

https://github.com/user-attachments/assets/b1634b67-efcd-4bc2-a9e7-49d681d744ba

<img width="372" height="579" alt="Screenshot 2026-02-14 181529" src="https://github.com/user-attachments/assets/559b33b4-c7f4-4a3c-8a2d-3b2cf3309ae8" />

## Troubleshooting

**"GEE initialization failed"** → Run `earthengine authenticate`  
**"No baseline image"** → AOI may be in area with no coverage or needs more time  
**False positives** → SAR sensitive to rain, vegetation. Try higher threshold (4-5 dB)  
**Large AOI errors** → Maximum 5000 km² per area

## Advanced

See `.env.example` for all configuration options including:
- Monitoring frequency (`CHECK_INTERVAL_HOURS`)
- Change thresholds (`MIN_CHANGE_AREA_KM2`, `MIN_CHANGE_PCT`)
- Server settings (`FLASK_HOST`, `FLASK_PORT`)

## License & Security

MIT License - see [LICENSE](LICENSE)

**Important:** Never commit `.env` file. Keep webhook URLs private. For production use, add authentication, HTTPS, and proper secrets management.

---

Made for OSINT researchers and geospatial analysts. Questions? Check code comments or modify to your needs.
