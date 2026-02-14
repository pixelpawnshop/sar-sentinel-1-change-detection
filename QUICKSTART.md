# Quick Start Guide

Get up and running in 5 minutes.

## Prerequisites

- [ ] Python 3.8+
- [ ] Google Earth Engine account → https://earthengine.google.com/signup/
- [ ] Webhook URL (optional) → Slack: https://api.slack.com/messaging/webhooks or Discord: Server Settings → Webhooks

## Setup

### 1. Install

```powershell
cd c:\coding\osint
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Authenticate

```powershell
earthengine authenticate
```
Browser will open → sign in with Google → authorize.

### 3. Configure

```powershell
Copy-Item .env.example .env
notepad .env
```

**Edit these two required values:**
```env
GEE_PROJECT_ID=your-google-cloud-project-id  # From Google Cloud Console
BASE_URL=http://localhost:5000
```

**Optional (for notifications):**
```env
WEBHOOK_URL=https://your-webhook-url
WEBHOOK_TYPE=slack  # or discord
```

### 4. Initialize & Run

```powershell
# Create database
python -c "from models import init_db; init_db()"

# Start web app
python app.py
```

Open http://localhost:5000

**For automated monitoring,** open second terminal:
```powershell
.\venv\Scripts\Activate.ps1
python monitor.py
```

## Using the App

1. Click polygon tool on map
2. Draw area (max 5000 km²), double-click to finish
3. Name your AOI
4. Wait ~30 seconds for baseline
5. Click "Analyze Now" or let monitor check automatically
6. Click "Time Series" to view historical changes

**Time Series Controls:**
- ▶ Play/Pause, ⏹ Stop
- Speed: 0.5x - 4x
- Scrubber to jump frames
- Space = play/pause, ←/→ = navigate

## Common Issues

| Problem | Solution |
|---------|----------|
| "GEE initialization failed" | Run `earthengine authenticate` |
| Can't access web interface | Check port 5000 is free, try http://localhost:5000 |
| No baseline image | AOI may have no coverage, check logs |
| AOI too large error | Maximum 5000 km² per area |
| False positive changes | SAR sensitive to rain/vegetation, increase threshold to 4-5 dB |

## What's Next?

- **Multiple AOIs**: Draw as many as you want, system monitors all
- **Custom thresholds**: Edit AOI to set sensitivity per location  
- **Schedule as service**: Use Windows Task Scheduler or systemd (Linux)

See `.env.example` for all configuration options.

---

That's it! Monitor global changes with satellite imagery. 🛰️
