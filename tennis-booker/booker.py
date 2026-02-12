"""Core booking engine using Playwright browser automation."""

import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PwTimeout
from config import BookingConfig

logger = logging.getLogger(__name__)

# Maximum number of retries for each booking attempt
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


def calculate_target_date(config: BookingConfig) -> datetime:
    """Calculate the target booking date (today + days_in_advance)."""
    tz = ZoneInfo(config.timezone)
    now = datetime.now(tz)
    target = now + timedelta(days=config.days_in_advance)
    return target


def format_date_for_url(target: datetime) -> str:
    """Format date as YYYY-MM-DD for URL parameters."""
    return target.strftime("%Y-%m-%d")


class BookingResult:
    def __init__(self, success: bool, message: str, court: str = "", time_slot: str = ""):
        self.success = success
        self.message = message
        self.court = court
        self.time_slot = time_slot

    def __str__(self):
        if self.success:
            return f"BOOKED: Court {self.court} at {self.time_slot} - {self.message}"
        return f"FAILED: {self.message}"


# ---------------------------------------------------------------------------
# ClubSpark booking flow
# ---------------------------------------------------------------------------

def _clubspark_login(page: Page, config: BookingConfig) -> bool:
    """Log in to ClubSpark."""
    logger.info("Navigating to ClubSpark login...")
    login_url = config.club_login_url or config.club_url
    page.goto(login_url, wait_until="networkidle", timeout=30000)

    # ClubSpark typically redirects to an SSO / identity page
    # Look for common login form selectors
    login_selectors = [
        "#EmailAddress",  # ClubSpark email field
        "#UserName",      # Alternative
        "input[name='Email']",
        "input[type='email']",
        "input[name='username']",
    ]

    email_input = None
    for selector in login_selectors:
        try:
            email_input = page.wait_for_selector(selector, timeout=5000)
            if email_input:
                break
        except PwTimeout:
            continue

    if not email_input:
        # Maybe we're already logged in or login page looks different
        if "booking" in page.url.lower() or "book" in page.url.lower():
            logger.info("Appears to already be on booking page, may be logged in")
            return True
        logger.error("Could not find login form. Current URL: %s", page.url)
        page.screenshot(path="debug_login_page.png")
        return False

    email_input.fill(config.username)

    # Find and fill password
    password_selectors = [
        "#Password",
        "input[name='Password']",
        "input[type='password']",
    ]
    for selector in password_selectors:
        try:
            pwd_input = page.wait_for_selector(selector, timeout=3000)
            if pwd_input:
                pwd_input.fill(config.password)
                break
        except PwTimeout:
            continue

    # Click login/submit button
    submit_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "#signin-btn",
        ".btn-primary",
        "button:has-text('Sign in')",
        "button:has-text('Log in')",
        "button:has-text('Login')",
    ]
    for selector in submit_selectors:
        try:
            btn = page.wait_for_selector(selector, timeout=3000)
            if btn:
                btn.click()
                break
        except PwTimeout:
            continue

    # Wait for navigation after login
    page.wait_for_load_state("networkidle", timeout=15000)
    logger.info("Login completed. Current URL: %s", page.url)
    return True


def _clubspark_book(page: Page, config: BookingConfig, target_date: datetime) -> BookingResult:
    """Attempt to book a court on ClubSpark for the target date."""
    date_str = format_date_for_url(target_date)
    day_name = target_date.strftime("%A")

    # Navigate to booking page for the target date
    booking_url = f"{config.club_url}?date={date_str}"
    logger.info("Navigating to booking page: %s", booking_url)
    page.goto(booking_url, wait_until="networkidle", timeout=30000)

    # Wait for the booking grid/slots to load
    time.sleep(2)
    page.wait_for_load_state("networkidle", timeout=15000)

    # Try each preferred time in order
    for preferred_time in config.preferred_times:
        logger.info("Looking for %s slot on %s (%s)...", preferred_time, day_name, date_str)

        # Try each preferred court for this time
        courts_to_try = config.preferred_courts if config.preferred_courts else [""]

        for court in courts_to_try:
            result = _try_book_slot_clubspark(page, config, preferred_time, court, target_date)
            if result.success:
                return result

    return BookingResult(False, f"No available slots found for {day_name} {date_str}")


def _try_book_slot_clubspark(
    page: Page, config: BookingConfig, time_slot: str, court: str, target_date: datetime
) -> BookingResult:
    """Try to click and book a specific time/court combination on ClubSpark."""
    date_str = format_date_for_url(target_date)

    # ClubSpark uses various selectors for available slots. Common patterns:
    # - Links/buttons with the time text
    # - Data attributes with date/time info
    # - Table cells in a booking grid

    slot_selectors = [
        # Direct time text matching
        f"a:has-text('{time_slot}')",
        f"button:has-text('{time_slot}')",
        f"[data-time='{time_slot}']",
        f"[data-start-time='{time_slot}']",
        # ClubSpark specific: resource/time grid cells
        f".booking-slot[data-time='{time_slot}']",
        f".available[data-time='{time_slot}']",
        f"td.available:has-text('{time_slot}')",
        # Time without leading zero
        f"a:has-text('{time_slot.lstrip('0')}')",
    ]

    if court:
        # Add court-specific selectors
        slot_selectors = [
            f"[data-court='{court}'] a:has-text('{time_slot}')",
            f"[data-resource-name='Court {court}'] a:has-text('{time_slot}')",
            f".court-{court} a:has-text('{time_slot}')",
        ] + slot_selectors

    for selector in slot_selectors:
        try:
            slot = page.query_selector(selector)
            if slot and slot.is_visible():
                logger.info("Found slot: %s (court %s) — clicking...", time_slot, court or "any")
                slot.click()
                time.sleep(1)

                # Handle the booking confirmation flow
                return _confirm_booking_clubspark(page, config, time_slot, court)
        except Exception as e:
            logger.debug("Selector %s didn't match: %s", selector, e)
            continue

    court_label = f" on Court {court}" if court else ""
    logger.info("Slot %s%s not available", time_slot, court_label)
    return BookingResult(False, f"Slot {time_slot}{court_label} not found or not available")


def _confirm_booking_clubspark(page: Page, config: BookingConfig, time_slot: str, court: str) -> BookingResult:
    """Handle the ClubSpark booking confirmation dialog/page."""
    try:
        page.wait_for_load_state("networkidle", timeout=10000)

        # Select duration if there's a duration picker
        duration_selectors = [
            f"[data-duration='{config.duration_minutes}']",
            f"option[value='{config.duration_minutes}']",
            f"button:has-text('{config.duration_minutes} min')",
        ]
        for selector in duration_selectors:
            try:
                el = page.query_selector(selector)
                if el and el.is_visible():
                    el.click()
                    time.sleep(0.5)
                    break
            except Exception:
                continue

        # Look for confirm/book/pay button
        confirm_selectors = [
            "button:has-text('Confirm')",
            "button:has-text('Book')",
            "button:has-text('Complete')",
            "button:has-text('Pay')",
            "button:has-text('Reserve')",
            "input[value='Confirm']",
            ".btn-confirm",
            "#confirmBooking",
            "#btnBook",
        ]

        for selector in confirm_selectors:
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    logger.info("Clicking confirm button: %s", selector)
                    btn.click()
                    page.wait_for_load_state("networkidle", timeout=15000)
                    break
            except Exception:
                continue

        # Check for success indicators
        success_indicators = [
            "text=Booking confirmed",
            "text=booking has been made",
            "text=Successfully booked",
            "text=Confirmation",
            ".booking-confirmation",
            ".success",
        ]

        for indicator in success_indicators:
            try:
                el = page.query_selector(indicator)
                if el:
                    court_label = court or "unknown"
                    logger.info("Booking confirmed! Court %s at %s", court_label, time_slot)
                    page.screenshot(path="booking_confirmation.png")
                    return BookingResult(
                        True,
                        "Booking confirmed successfully",
                        court=court_label,
                        time_slot=time_slot,
                    )
            except Exception:
                continue

        # If we clicked confirm but can't verify — take a screenshot for manual check
        page.screenshot(path="booking_result.png")
        logger.warning("Clicked confirm but could not verify success. Check booking_result.png")
        return BookingResult(
            False,
            "Clicked confirm but could not verify booking. Check screenshots.",
            court=court or "unknown",
            time_slot=time_slot,
        )

    except Exception as e:
        page.screenshot(path="booking_error.png")
        logger.error("Error during booking confirmation: %s", e)
        return BookingResult(False, f"Confirmation error: {e}")


# ---------------------------------------------------------------------------
# Generic booking flow (fallback for non-ClubSpark platforms)
# ---------------------------------------------------------------------------

def _generic_login(page: Page, config: BookingConfig) -> bool:
    """Attempt a generic login using common form patterns."""
    logger.info("Attempting generic login at: %s", config.club_login_url or config.club_url)
    page.goto(config.club_login_url or config.club_url, wait_until="networkidle", timeout=30000)

    # Try to find and fill email/username
    for selector in ["input[type='email']", "input[name='email']", "input[name='username']", "#email", "#username"]:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.fill(config.username)
                break
        except Exception:
            continue

    # Try to find and fill password
    for selector in ["input[type='password']", "#password"]:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.fill(config.password)
                break
        except Exception:
            continue

    # Submit
    for selector in ["button[type='submit']", "input[type='submit']", "button:has-text('Log in')", "button:has-text('Sign in')"]:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.click()
                break
        except Exception:
            continue

    page.wait_for_load_state("networkidle", timeout=15000)
    logger.info("Generic login completed. URL: %s", page.url)
    return True


def _generic_book(page: Page, config: BookingConfig, target_date: datetime) -> BookingResult:
    """Generic booking attempt — navigates to date and tries to click time slots."""
    date_str = format_date_for_url(target_date)
    booking_url = f"{config.club_url}?date={date_str}"
    page.goto(booking_url, wait_until="networkidle", timeout=30000)
    time.sleep(2)

    for preferred_time in config.preferred_times:
        for selector in [
            f"a:has-text('{preferred_time}')",
            f"button:has-text('{preferred_time}')",
            f"[data-time='{preferred_time}']",
            f"td:has-text('{preferred_time}')",
        ]:
            try:
                el = page.query_selector(selector)
                if el and el.is_visible():
                    el.click()
                    time.sleep(1)
                    # Try to confirm
                    for btn_sel in ["button:has-text('Confirm')", "button:has-text('Book')", "button[type='submit']"]:
                        try:
                            btn = page.query_selector(btn_sel)
                            if btn and btn.is_visible():
                                btn.click()
                                page.wait_for_load_state("networkidle", timeout=10000)
                                page.screenshot(path="booking_result.png")
                                return BookingResult(True, "Booking submitted (verify manually)", time_slot=preferred_time)
                        except Exception:
                            continue
            except Exception:
                continue

    return BookingResult(False, "No available slots found with generic strategy")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_booking(config: BookingConfig) -> BookingResult:
    """Execute the full booking flow: launch browser -> login -> book."""
    target_date = calculate_target_date(config)
    logger.info(
        "Target booking date: %s (%s)",
        target_date.strftime("%A %d %B %Y"),
        format_date_for_url(target_date),
    )
    logger.info("Preferred times: %s", ", ".join(config.preferred_times))
    logger.info("Platform: %s", config.platform)

    for attempt in range(1, MAX_RETRIES + 1):
        logger.info("--- Attempt %d of %d ---", attempt, MAX_RETRIES)
        try:
            result = _execute_booking(config, target_date)
            if result.success:
                return result
            logger.warning("Attempt %d failed: %s", attempt, result.message)
        except Exception as e:
            logger.error("Attempt %d error: %s", attempt, e)

        if attempt < MAX_RETRIES:
            wait = RETRY_DELAY_SECONDS * attempt
            logger.info("Waiting %ds before retry...", wait)
            time.sleep(wait)

    return BookingResult(False, f"All {MAX_RETRIES} booking attempts failed")


def _execute_booking(config: BookingConfig, target_date: datetime) -> BookingResult:
    """Single booking execution with a fresh browser context."""
    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            if config.platform == "clubspark":
                logged_in = _clubspark_login(page, config)
                if not logged_in:
                    return BookingResult(False, "Login failed")
                return _clubspark_book(page, config, target_date)
            else:
                logged_in = _generic_login(page, config)
                if not logged_in:
                    return BookingResult(False, "Login failed")
                return _generic_book(page, config, target_date)
        finally:
            page.screenshot(path="debug_final_state.png")
            browser.close()
