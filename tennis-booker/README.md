# Avenue Tennis — Auto Court Booker

Automatically logs into [Avenue Tennis](https://www.avenuetennis.co.uk/book-a-court/) via ClubSpark at midnight GMT and books a court the moment slots are released 14 days in advance.

## How It Works

1. A scheduler runs continuously and triggers at **00:00:01 GMT** every night
2. It checks if the date **14 days from now** matches your preferred day (e.g. Saturday)
3. If it matches, it launches a headless browser, logs into ClubSpark, navigates to the target date, and books your preferred court/time
4. Retries up to 3 times with exponential backoff on failure
5. Sends you a push notification with the result

## Quick Start

```bash
cd tennis-booker

# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Configure your settings
cp .env.example .env
# Edit .env — add your ClubSpark email and password, set your preferred day/times

# 3. Inspect the booking page (discover the DOM structure)
python inspect_page.py --login --date 2026-02-28

# 4. Test with a dry run (shows config, no booking)
python main.py --dry-run

# 5. Test an immediate booking
python main.py --now

# 6. Run the scheduler (keeps running, books at midnight daily)
python main.py
```

## Configuration (.env)

Copy `.env.example` to `.env` and fill in your details:

| Variable | Description | Default |
|----------|-------------|---------|
| `CLUB_URL` | ClubSpark booking page | `https://clubspark.lta.org.uk/AvenueTennis/Booking/BookByDate` |
| `USERNAME` | Your ClubSpark login email | - |
| `PASSWORD` | Your ClubSpark password | - |
| `PREFERRED_DAY` | Day of week to book | `saturday` |
| `PREFERRED_TIMES` | Comma-separated times (24h), tried in order | `18:00,19:00,17:00,20:00` |
| `PREFERRED_COURTS` | Court numbers (optional, comma-separated) | any |
| `DURATION_MINUTES` | Booking duration in minutes | `60` |
| `DAYS_IN_ADVANCE` | How many days ahead courts are released | `14` |
| `TIMEZONE` | Timezone for midnight trigger | `Europe/London` |
| `NTFY_TOPIC` | ntfy.sh topic for phone notifications | - |

## Page Inspector

Since ClubSpark's DOM isn't publicly documented, use the inspector to discover the exact page structure for Avenue Tennis:

```bash
# See what the login page looks like
python inspect_page.py

# Log in and inspect the booking sheet
python inspect_page.py --login

# Inspect a specific date
python inspect_page.py --login --date 2026-03-01

# Open the browser visually to manually inspect with DevTools (F12)
python inspect_page.py --login --interactive
```

This saves screenshots and a detailed `page_analysis.json` to the `screenshots/` directory, showing all forms, buttons, tables, time elements, and data attributes on the page.

If the auto-detected selectors don't match Avenue Tennis's page, use the inspector output to update the selectors in `booker.py`.

## Running with Docker

```bash
docker build -t tennis-booker .
docker run -d --name tennis-booker --env-file .env tennis-booker
```

## Notifications

### ntfy.sh (recommended — free push notifications to your phone)
1. Install the [ntfy app](https://ntfy.sh) on your phone
2. Subscribe to a topic (e.g. `my-tennis-alerts`)
3. Set `NTFY_TOPIC=my-tennis-alerts` in your `.env`

### Webhook (Slack, Discord, etc.)
Set `NOTIFICATION_WEBHOOK_URL` to your incoming webhook URL.

## Commands

| Command | Description |
|---------|-------------|
| `python main.py` | Start the scheduler (runs at midnight daily) |
| `python main.py --now` | Run booking immediately (for testing) |
| `python main.py --dry-run` | Show config and target date without booking |
| `python inspect_page.py --login` | Inspect the ClubSpark page structure |
| `python inspect_page.py --interactive` | Open browser visually for manual inspection |

## File Structure

```
tennis-booker/
  main.py             # Entry point (scheduler, --now, --dry-run)
  scheduler.py        # APScheduler cron job — fires at midnight daily
  booker.py           # Playwright browser automation (login → navigate → book → confirm)
  config.py           # Loads settings from .env
  notifications.py    # Push notifications (ntfy.sh / webhooks)
  inspect_page.py     # Page inspector utility — discover DOM selectors
  .env.example        # Template config
  Dockerfile          # For containerised deployment
  requirements.txt    # Python dependencies
```

## Logs & Screenshots

- All activity is logged to `tennis_booker.log` and stdout
- Screenshots are saved to `screenshots/` at each step of the booking flow for debugging
- Key screenshots: `01_login_page`, `03_post_login`, `04_booking_sheet`, `09_final_result`, `10_booking_confirmed`

## Troubleshooting

1. **Login fails**: Run `python inspect_page.py --interactive` to see what the login page looks like. Check your email/password in `.env`.
2. **Can't find time slots**: Run the inspector with `--login --date YYYY-MM-DD` and check `screenshots/page_analysis.json` for the DOM structure. Update selectors in `booker.py` if needed.
3. **Booking overlay doesn't complete**: Check screenshots `07_booking_form` through `09_final_result` to see where the flow stops.
