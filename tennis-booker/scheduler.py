"""Scheduler that triggers court booking at midnight in the configured timezone."""

import logging
import signal
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

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


def booking_job() -> None:
    """Job that runs at midnight to book a court."""
    config = BookingConfig.from_env()
    target = calculate_target_date(config)
    day_name = config.preferred_day.capitalize()

    # Only book if the target date falls on the preferred day
    target_day = target.strftime("%A").lower()
    if target_day != config.preferred_day:
        logger.info(
            "Target date %s is a %s, not %s. Skipping.",
            target.strftime("%Y-%m-%d"),
            target.strftime("%A"),
            day_name,
        )
        return

    logger.info("Target date %s is a %s — proceeding with booking!", target.strftime("%Y-%m-%d"), day_name)

    result = run_booking(config)
    logger.info("Booking result: %s", result)

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
            f"Could not book a court for {target.strftime('%A %d %B')}: {result.message}",
        )


def run_scheduler() -> None:
    """Start the scheduler to run the booking job at midnight every day."""
    config = BookingConfig.from_env()
    tz = ZoneInfo(config.timezone)

    scheduler = BlockingScheduler(timezone=tz)

    # Run at 00:00:01 every day (1 second past midnight to ensure date rollover)
    trigger = CronTrigger(hour=0, minute=0, second=1, timezone=tz)
    scheduler.add_job(booking_job, trigger, id="tennis_booking", name="Tennis Court Booking")

    # Graceful shutdown
    def shutdown(signum, frame):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    next_run = scheduler.get_jobs()[0].next_run_time if scheduler.get_jobs() else "unknown"
    logger.info("Scheduler started. Timezone: %s", config.timezone)
    logger.info("Next run: %s", next_run)
    logger.info(
        "Will book for: %s, %d days in advance",
        config.preferred_day.capitalize(),
        config.days_in_advance,
    )
    logger.info("Preferred times: %s", ", ".join(config.preferred_times))

    scheduler.start()


if __name__ == "__main__":
    run_scheduler()
