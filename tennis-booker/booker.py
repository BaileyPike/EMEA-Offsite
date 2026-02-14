"""
Core booking engine for Avenue Tennis via ClubSpark (LTA).

ClubSpark booking flow:
1. Navigate to BookByDate page — this triggers a login redirect if not authenticated
2. ClubSpark redirects to identity.clubspark.com for SSO login
3. After login, redirects back to the booking sheet
4. The booking sheet shows a grid: columns = courts, rows = time slots
5. Click an available slot → booking overlay appears
6. Select duration → click "Continue booking"
7. Confirm and pay (if applicable) → booking confirmed

URL pattern:
  https://clubspark.lta.org.uk/{VenueName}/Booking/BookByDate#?date={YYYY-MM-DD}&role=member
"""

import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PwTimeout
from config import BookingConfig

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = Path("screenshots")
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


def _ensure_screenshots_dir():
    SCREENSHOTS_DIR.mkdir(exist_ok=True)


def _screenshot(page: Page, name: str):
    _ensure_screenshots_dir()
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    logger.info("Screenshot saved: %s", path)


def calculate_target_date(config: BookingConfig) -> datetime:
    """Calculate the target booking date (today + days_in_advance)."""
    tz = ZoneInfo(config.timezone)
    now = datetime.now(tz)
    target = now + timedelta(days=config.days_in_advance)
    return target


def format_date_for_url(target: datetime) -> str:
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
# ClubSpark login
# ---------------------------------------------------------------------------

def _clubspark_login(page: Page, config: BookingConfig) -> bool:
    """
    Log in to ClubSpark via the SSO identity flow.

    ClubSpark redirects unauthenticated users to:
      https://identity.clubspark.com/Account/Login
    or a venue-specific variant. The login form has standard email/password fields.
    """
    target_url = config.club_url
    logger.info("Navigating to: %s", target_url)
    page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)

    # Check if we landed on a login/identity page
    current_url = page.url.lower()
    logger.info("Current URL after navigation: %s", page.url)

    # If we're already on the booking page (logged in via stored cookies), we're done
    if "booking" in current_url and "login" not in current_url and "account" not in current_url:
        logger.info("Already on booking page — appears to be logged in")
        return True

    _screenshot(page, "01_login_page")

    # --- Handle cookie consent banners ---
    for cookie_sel in [
        "#onetrust-accept-btn-handler",
        "button:has-text('Accept')",
        "button:has-text('Accept all')",
        ".cookie-accept",
        "#cookie-accept",
    ]:
        try:
            btn = page.query_selector(cookie_sel)
            if btn and btn.is_visible():
                btn.click()
                logger.info("Dismissed cookie banner")
                time.sleep(0.5)
                break
        except Exception:
            continue

    # --- Find and fill the email field ---
    email_selectors = [
        "#EmailAddress",
        "#Email",
        "#UserName",
        "input[name='EmailAddress']",
        "input[name='Email']",
        "input[name='UserName']",
        "input[name='username']",
        "input[type='email']",
        "input[autocomplete='email']",
        "input[autocomplete='username']",
    ]

    email_input = None
    for selector in email_selectors:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                email_input = el
                logger.info("Found email field: %s", selector)
                break
        except Exception:
            continue

    if not email_input:
        # ClubSpark sometimes has a "Sign in" link/button that must be clicked first
        for sign_in_sel in [
            "a:has-text('Sign in')",
            "a:has-text('Log in')",
            "button:has-text('Sign in')",
            ".sign-in-link",
            "#sign-in-link",
            "a[href*='Account/Login']",
            "a[href*='login']",
        ]:
            try:
                link = page.query_selector(sign_in_sel)
                if link and link.is_visible():
                    link.click()
                    logger.info("Clicked sign-in link: %s", sign_in_sel)
                    page.wait_for_load_state("domcontentloaded", timeout=10000)
                    time.sleep(2)
                    break
            except Exception:
                continue

        # Try again after clicking sign-in
        for selector in email_selectors:
            try:
                el = page.query_selector(selector)
                if el and el.is_visible():
                    email_input = el
                    logger.info("Found email field after sign-in click: %s", selector)
                    break
            except Exception:
                continue

    if not email_input:
        _screenshot(page, "01_login_no_email_field")
        logger.error("Could not find email input field. URL: %s", page.url)
        return False

    email_input.fill(config.username)
    logger.info("Filled email: %s", config.username)

    # --- Find and fill the password field ---
    password_selectors = [
        "#Password",
        "input[name='Password']",
        "input[name='password']",
        "input[type='password']",
    ]
    password_filled = False
    for selector in password_selectors:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.fill(config.password)
                password_filled = True
                logger.info("Filled password field: %s", selector)
                break
        except Exception:
            continue

    if not password_filled:
        _screenshot(page, "01_login_no_password_field")
        logger.error("Could not find password field")
        return False

    _screenshot(page, "02_login_filled")

    # --- Click submit ---
    submit_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "#signin-btn",
        "#login-btn",
        "button:has-text('Sign in')",
        "button:has-text('Log in')",
        "button:has-text('Login')",
        ".btn-primary[type='submit']",
    ]
    for selector in submit_selectors:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click()
                logger.info("Clicked submit: %s", selector)
                break
        except Exception:
            continue

    # Wait for redirect back to booking page
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except PwTimeout:
        logger.warning("Timeout waiting for post-login navigation")

    time.sleep(2)
    _screenshot(page, "03_post_login")
    logger.info("Post-login URL: %s", page.url)

    # Check for login errors
    error_selectors = [
        ".validation-summary-errors",
        ".field-validation-error",
        ".error-message",
        ".alert-danger",
        "text=Invalid",
        "text=incorrect",
    ]
    for selector in error_selectors:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                error_text = el.inner_text()
                logger.error("Login error detected: %s", error_text)
                return False
        except Exception:
            continue

    return True


# ---------------------------------------------------------------------------
# ClubSpark booking
# ---------------------------------------------------------------------------

def _clubspark_book(page: Page, config: BookingConfig, target_date: datetime) -> BookingResult:
    """Navigate to the target date and attempt to book a court."""
    date_str = format_date_for_url(target_date)
    day_name = target_date.strftime("%A")

    # ClubSpark BookByDate uses a hash fragment for the date
    # Format: /Booking/BookByDate#?date=2026-02-28&role=member
    booking_url = f"{config.club_url}#?date={date_str}&role=member"
    logger.info("Navigating to booking page: %s", booking_url)
    page.goto(booking_url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    # Wait for the booking sheet to render (it's JS-heavy)
    _wait_for_booking_sheet(page)
    _screenshot(page, "04_booking_sheet")

    # Try each preferred time in order
    for preferred_time in config.preferred_times:
        logger.info("Trying to book %s on %s (%s)...", preferred_time, day_name, date_str)

        courts_to_try = config.preferred_courts if config.preferred_courts else [None]

        for court in courts_to_try:
            result = _try_book_slot(page, config, preferred_time, court, target_date)
            if result.success:
                return result

            # After a failed attempt, go back to the booking sheet
            page.goto(booking_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            _wait_for_booking_sheet(page)

    return BookingResult(False, f"No available slots found for {day_name} {date_str}")


def _wait_for_booking_sheet(page: Page, timeout: int = 15000):
    """Wait for the ClubSpark booking grid to load."""
    sheet_selectors = [
        ".booking-sheet",
        ".booking-grid",
        ".booking-calendar",
        "#booking-sheet",
        "table.booking",
        ".resource-booking",
        "[class*='booking']",
        "[class*='schedule']",
        "table",
    ]
    for selector in sheet_selectors:
        try:
            page.wait_for_selector(selector, timeout=timeout // len(sheet_selectors))
            logger.info("Booking sheet loaded (matched: %s)", selector)
            return
        except PwTimeout:
            continue

    logger.warning("Could not detect booking sheet — proceeding anyway")


def _try_book_slot(
    page: Page, config: BookingConfig, time_slot: str, court: str | None, target_date: datetime
) -> BookingResult:
    """Try to click an available time slot and complete the booking."""

    # Convert time formats: "18:00" -> also try "6:00 PM", "6pm", "18:00:00"
    hour, minute = time_slot.split(":")
    hour_int = int(hour)
    am_pm = "AM" if hour_int < 12 else "PM"
    hour_12 = hour_int if hour_int <= 12 else hour_int - 12
    if hour_12 == 0:
        hour_12 = 12
    time_12h = f"{hour_12}:{minute} {am_pm}"
    time_12h_no_space = f"{hour_12}:{minute}{am_pm}"

    time_variants = [time_slot, time_12h, time_12h_no_space, f"{time_slot}:00"]

    court_label = f"Court {court}" if court else "any court"
    logger.info("Searching for slot: %s (%s)", time_slot, court_label)

    # Strategy 1: Find clickable slot elements containing the time text
    for time_text in time_variants:
        # Try various element types that could represent a bookable slot
        selectors = [
            f"a:has-text('{time_text}')",
            f"td:has-text('{time_text}')",
            f"div:has-text('{time_text}')",
            f"button:has-text('{time_text}')",
            f"[data-time='{time_slot}']",
            f"[data-start='{time_slot}']",
            f"[data-start-time='{time_slot}']",
        ]

        for selector in selectors:
            try:
                elements = page.query_selector_all(selector)
                for el in elements:
                    if not el.is_visible():
                        continue

                    # Check if this element is inside the right court column
                    if court:
                        parent_html = el.evaluate(
                            "el => el.closest('td, [class*=\"court\"], [data-resource]')?.outerHTML || ''"
                        )
                        if court.lower() not in parent_html.lower() and f"court {court}" not in parent_html.lower():
                            continue

                    # Check the element isn't disabled/unavailable
                    classes = el.get_attribute("class") or ""
                    if any(word in classes.lower() for word in ["unavailable", "disabled", "booked", "closed"]):
                        continue

                    logger.info("Found available slot element — clicking...")
                    _screenshot(page, "05_before_click")
                    el.click()
                    time.sleep(2)
                    _screenshot(page, "06_after_click")

                    return _complete_booking(page, config, time_slot, court)
            except Exception as e:
                logger.debug("Selector %s: %s", selector, e)
                continue

    # Strategy 2: Look for all clickable available slots and match by position/text
    try:
        all_available = page.query_selector_all(
            "td.available, .slot.available, .booking-slot:not(.booked), "
            "a.available, [class*='available']:not([class*='unavailable'])"
        )
        for el in all_available:
            text = el.inner_text().strip()
            for time_text in time_variants:
                if time_text in text:
                    if court:
                        parent_text = el.evaluate("el => el.closest('tr, [class*=\"court\"]')?.textContent || ''")
                        if court.lower() not in parent_text.lower():
                            continue
                    logger.info("Found available slot via class matching: %s", text)
                    el.click()
                    time.sleep(2)
                    return _complete_booking(page, config, time_slot, court)
    except Exception as e:
        logger.debug("Strategy 2 failed: %s", e)

    logger.info("Slot %s on %s not found or not available", time_slot, court_label)
    return BookingResult(False, f"Slot {time_slot} on {court_label} not found")


def _complete_booking(page: Page, config: BookingConfig, time_slot: str, court: str | None) -> BookingResult:
    """Complete the booking after clicking a time slot."""
    try:
        page.wait_for_load_state("domcontentloaded", timeout=10000)
    except PwTimeout:
        pass
    time.sleep(1)

    court_label = court or "unknown"

    # --- Step 1: Handle the booking overlay / form ---
    # ClubSpark shows a booking overlay with duration selection

    # Select duration via dropdown
    duration_str = str(config.duration_minutes)
    try:
        # Look for a select/dropdown for duration
        duration_dropdown = page.query_selector(
            "select[name*='duration' i], select[name*='Duration' i], "
            "select[id*='duration' i], select#Duration, select.duration-select"
        )
        if duration_dropdown and duration_dropdown.is_visible():
            duration_dropdown.select_option(value=duration_str)
            logger.info("Selected duration: %s minutes", duration_str)
            time.sleep(0.5)
    except Exception as e:
        logger.debug("Duration dropdown: %s", e)

    # Also try clicking duration buttons/options
    for sel in [
        f"[data-duration='{duration_str}']",
        f"button:has-text('{duration_str} min')",
        f"label:has-text('{duration_str} min')",
        f"option:has-text('{duration_str}')",
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click()
                time.sleep(0.5)
                break
        except Exception:
            continue

    _screenshot(page, "07_booking_form")

    # --- Step 2: Click "Continue booking" or equivalent ---
    continue_selectors = [
        "button:has-text('Continue booking')",
        "button:has-text('Continue')",
        "a:has-text('Continue booking')",
        "a:has-text('Continue')",
        "input[value*='Continue']",
        ".continue-booking",
        "#continue-booking",
        "button.btn-primary",
    ]

    for selector in continue_selectors:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                logger.info("Clicking continue: %s", selector)
                btn.click()
                time.sleep(2)
                break
        except Exception:
            continue

    _screenshot(page, "08_after_continue")

    # --- Step 3: Confirm and pay (or just confirm for free courts) ---
    confirm_selectors = [
        "button:has-text('Confirm and pay')",
        "button:has-text('Confirm & pay')",
        "button:has-text('Confirm booking')",
        "button:has-text('Confirm')",
        "button:has-text('Complete booking')",
        "button:has-text('Book')",
        "button:has-text('Pay now')",
        "button:has-text('Reserve')",
        "input[value*='Confirm']",
        "input[value*='Book']",
        "#confirmBooking",
        "#btnBook",
        "#btnConfirm",
        ".btn-confirm",
        "button.btn-primary",
    ]

    confirmed = False
    for selector in confirm_selectors:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                logger.info("Clicking confirm: %s", selector)
                btn.click()
                confirmed = True
                break
        except Exception:
            continue

    if confirmed:
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PwTimeout:
            pass
        time.sleep(2)

    _screenshot(page, "09_final_result")

    # --- Step 4: Verify success ---
    page_text = page.inner_text("body").lower()
    success_phrases = [
        "booking confirmed",
        "booking has been made",
        "successfully booked",
        "booking complete",
        "confirmation",
        "your booking",
        "court booked",
        "booking reference",
    ]

    for phrase in success_phrases:
        if phrase in page_text:
            logger.info("Booking SUCCESS — detected: '%s'", phrase)
            _screenshot(page, "10_booking_confirmed")
            return BookingResult(
                True,
                f"Booking confirmed (detected: '{phrase}')",
                court=court_label,
                time_slot=time_slot,
            )

    # Check for error/failure phrases
    failure_phrases = ["already booked", "no longer available", "unavailable", "cannot book", "error"]
    for phrase in failure_phrases:
        if phrase in page_text:
            logger.warning("Booking failed — detected: '%s'", phrase)
            return BookingResult(False, f"Booking failed: '{phrase}'", court=court_label, time_slot=time_slot)

    if confirmed:
        logger.warning("Clicked confirm but couldn't verify success. Check screenshots.")
        return BookingResult(
            True,
            "Clicked confirm — check screenshots to verify",
            court=court_label,
            time_slot=time_slot,
        )

    return BookingResult(False, "Could not complete booking flow", court=court_label, time_slot=time_slot)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_booking(config: BookingConfig) -> BookingResult:
    """Execute the full booking flow with retries."""
    target_date = calculate_target_date(config)
    logger.info(
        "Target booking date: %s (%s)",
        target_date.strftime("%A %d %B %Y"),
        format_date_for_url(target_date),
    )
    logger.info("Preferred times: %s", ", ".join(config.preferred_times))
    logger.info("Platform: %s", config.platform)

    for attempt in range(1, MAX_RETRIES + 1):
        logger.info("=== Attempt %d of %d ===", attempt, MAX_RETRIES)
        try:
            result = _execute_booking(config, target_date)
            if result.success:
                return result
            logger.warning("Attempt %d failed: %s", attempt, result.message)
        except Exception as e:
            logger.error("Attempt %d error: %s", attempt, e, exc_info=True)

        if attempt < MAX_RETRIES:
            wait = RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
            logger.info("Waiting %ds before retry...", wait)
            time.sleep(wait)

    return BookingResult(False, f"All {MAX_RETRIES} booking attempts failed")


def _execute_booking(config: BookingConfig, target_date: datetime) -> BookingResult:
    """Single booking execution with a fresh browser context."""
    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            logged_in = _clubspark_login(page, config)
            if not logged_in:
                return BookingResult(False, "Login failed — check credentials and screenshots")
            return _clubspark_book(page, config, target_date)
        except Exception as e:
            _screenshot(page, "error_state")
            raise
        finally:
            browser.close()
