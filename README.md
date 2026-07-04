# CineWatch MVP

Automatically monitors BookMyShow and sends Telegram alerts when bookings open or preferred theatres/formats appear.

---

## Quick Start (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Set your Telegram credentials
export TELEGRAM_BOT_TOKEN=your_token
export TELEGRAM_CHAT_ID=your_chat_id

# 3. Run
python main.py
```

---

## Docker Deployment (Recommended)

```bash
# 1. Clone / copy project to your VM
# 2. Edit docker-compose.yml — fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
# 3. Start
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

The container restarts automatically on crash and on VM reboot (`restart: unless-stopped`).

---

## Configuration

All settings are in `config.py` or environment variables:

| Variable | Default | Description |
|---|---|---|
| `MOVIE_NAME` | Spider-Man: Brand New Day | Movie to monitor |
| `CITY` | Hyderabad | City on BookMyShow |
| `CHECK_INTERVAL_SECONDS` | 300 | Polling interval (seconds) |
| `HEADLESS` | true | Run browser headlessly |
| `TELEGRAM_BOT_TOKEN` | *(required)* | From @BotFather |
| `TELEGRAM_CHAT_ID` | *(required)* | Your personal chat ID |
| `SNAPSHOT_FILE` | snapshot.json | Where state is stored |

### Change Preferred Theatres / Formats

Edit `config.py`:
```python
PREFERRED_THEATRES = ["Prasads", "Allu Cineplex"]
PREFERRED_FORMATS  = ["PCX", "Barco", "3D", "Dolby"]
```

---

## How to Get Telegram Credentials

1. Open Telegram → search **@BotFather**
2. Send `/newbot` → follow prompts → copy the **token**
3. Start a chat with your new bot
4. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in browser
5. Send any message to the bot, refresh the URL → find `"chat":{"id": YOUR_CHAT_ID}`

---

## Project Structure

```
cinewatch/
├── main.py          # Entry point
├── config.py        # All configuration
├── scheduler.py     # APScheduler polling loop
├── scraper.py       # Playwright → BookMyShow
├── parser.py        # Raw data → normalized snapshot
├── comparator.py    # Snapshot diff → change events
├── notifier.py      # Telegram notifications
├── storage.py       # Read/write snapshot.json
├── logger.py        # Logging setup
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Change Events

| Event | Trigger |
|---|---|
| `BOOKING_OPEN` | "Book Tickets" button appears |
| `NEW_THEATRE` | Any new theatre listed |
| `PREFERRED_THEATRE` | Prasads / Allu Cineplex appears |
| `NEW_FORMAT` | Any new screen format |
| `PREFERRED_FORMAT` | PCX / Barco / 3D / Dolby appears |
| `NEW_SHOW` | New show time slot |
| `NO_CHANGE` | Nothing changed, sleep |

---

## Deploying to a Free Cloud VM

### Oracle Cloud Free Tier (Recommended)
1. Create an **Always Free** VM (Ampere A1, Ubuntu 22.04)
2. SSH in
3. Install Docker:
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER && newgrp docker
   ```
4. Copy project files to VM
5. `docker compose up -d`

Your PC can be completely OFF. The VM keeps running.
