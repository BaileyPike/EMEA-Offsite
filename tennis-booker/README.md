# Tennis Court Auto-Booker

Automatically logs into your tennis club booking system at midnight and books a court the moment slots are released (typically 14 days in advance).

## How It Works

1. A scheduler runs continuously and triggers at **00:00:01** in your configured timezone
2. It checks if the date 14 days from now matches your preferred day (e.g. Saturday)
3. If it matches, it launches a headless browser, logs into your club's booking system, and books a court at your preferred time
4. Retries up to 3 times on failure
5. Sends you a push notification with the result

## Quick Start

```bash
cd tennis-booker

# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Configure your settings
cp .env.example .env
# Edit .env with your club URL, credentials, and preferences

# 3. Test with a dry run
python main.py --dry-run

# 4. Test an immediate booking
python main.py --now

# 5. Run the scheduler (keeps running, books at midnight)
python main.py
```

## Configuration (.env)

| Variable | Description | Example |
|----------|-------------|---------|
| `CLUB_URL` | Your club's booking page URL | `https://clubspark.lta.org.uk/MyClub/Booking` |
| `CLUB_LOGIN_URL` | Login page URL (if different) | `https://clubspark.lta.org.uk/MyClub/Booking/BookByDate` |
| `USERNAME` | Your login email | `you@email.com` |
| `PASSWORD` | Your login password | `yourpassword` |
| `PREFERRED_DAY` | Day of week to book | `saturday` |
| `PREFERRED_TIMES` | Comma-separated times (24h), tried in order | `18:00,19:00,17:00` |
| `PREFERRED_COURTS` | Comma-separated court numbers (optional) | `1,2,3` |
| `DURATION_MINUTES` | Booking duration | `60` |
| `PLATFORM` | Booking platform | `clubspark` or `generic` |
| `DAYS_IN_ADVANCE` | How many days ahead courts open | `14` |
| `TIMEZONE` | Your timezone | `Europe/London` |
| `NTFY_TOPIC` | ntfy.sh topic for push notifications | `my-tennis-alerts` |

## Supported Platforms

- **ClubSpark** (default) — used by most LTA-affiliated clubs in the UK
- **Generic** — fallback that works with common login/booking form patterns

## Running with Docker

```bash
docker build -t tennis-booker .
docker run -d --name tennis-booker --env-file .env tennis-booker
```

## Notifications

### ntfy.sh (recommended — free push notifications)
1. Install the [ntfy app](https://ntfy.sh) on your phone
2. Subscribe to a topic (e.g. `my-tennis-alerts`)
3. Set `NTFY_TOPIC=my-tennis-alerts` in your `.env`

### Webhook (Slack, Discord, etc.)
Set `NOTIFICATION_WEBHOOK_URL` to your webhook URL.

## Commands

| Command | Description |
|---------|-------------|
| `python main.py` | Start the scheduler (runs at midnight daily) |
| `python main.py --now` | Run a booking attempt immediately |
| `python main.py --dry-run` | Show config and target date without booking |

## Customisation

If your club uses a different booking system, you may need to adjust the CSS selectors in `booker.py`. Run with `--now` and check the `debug_*.png` screenshots to see what the bot sees, then update the selectors accordingly.

## Logs

All activity is logged to `tennis_booker.log` and stdout.
