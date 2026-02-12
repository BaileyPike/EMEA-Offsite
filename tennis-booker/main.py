#!/usr/bin/env python3
"""
Tennis Court Auto-Booker

Automatically books tennis courts at midnight when slots are released.

Usage:
    python main.py              # Run the scheduler (books at midnight daily)
    python main.py --now        # Book immediately (for testing)
    python main.py --dry-run    # Show what would be booked without booking
"""

import argparse
import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from config import BookingConfig
from booker import run_booking, calculate_target_date
from notifications import send_notification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("tennis_booker.log"),
    ],
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Tennis Court Auto-Booker")
    parser.add_argument(
        "--now",
        action="store_true",
        help="Run the booking immediately instead of waiting for midnight",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show target date and preferences without actually booking",
    )
    args = parser.parse_args()

    config = BookingConfig.from_env()

    if not config.club_url:
        logger.error("CLUB_URL not set. Copy .env.example to .env and configure it.")
        sys.exit(1)
    if not config.username or not config.password:
        logger.error("USERNAME/PASSWORD not set. Configure your .env file.")
        sys.exit(1)

    target = calculate_target_date(config)
    tz = ZoneInfo(config.timezone)
    now = datetime.now(tz)

    print(f"\n{'='*50}")
    print(f"  Tennis Court Auto-Booker")
    print(f"{'='*50}")
    print(f"  Current time:    {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"  Target date:     {target.strftime('%A %d %B %Y')}")
    print(f"  Preferred day:   {config.preferred_day.capitalize()}")
    print(f"  Preferred times: {', '.join(config.preferred_times)}")
    print(f"  Courts:          {', '.join(config.preferred_courts) or 'Any'}")
    print(f"  Duration:        {config.duration_minutes} minutes")
    print(f"  Platform:        {config.platform}")
    print(f"  Days in advance: {config.days_in_advance}")
    print(f"{'='*50}\n")

    if args.dry_run:
        target_day = target.strftime("%A").lower()
        if target_day == config.preferred_day:
            print(f"DRY RUN: Would attempt to book on {target.strftime('%A %d %B %Y')}")
        else:
            print(
                f"DRY RUN: Target date is {target.strftime('%A')}, "
                f"not {config.preferred_day.capitalize()}. Would skip."
            )
        return

    if args.now:
        logger.info("Running booking immediately (--now flag)")
        result = run_booking(config)
        logger.info("Result: %s", result)

        if result.success:
            send_notification(
                config,
                "Tennis Court Booked!",
                f"Court {result.court} at {result.time_slot} on {target.strftime('%A %d %B')}",
            )
        else:
            send_notification(
                config,
                "Tennis Booking Failed",
                f"Could not book: {result.message}",
            )
        return

    # Default: run the scheduler
    from scheduler import run_scheduler
    run_scheduler()


if __name__ == "__main__":
    main()
