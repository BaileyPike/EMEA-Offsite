#!/usr/bin/env python3
"""
Page Inspector — helps you discover the ClubSpark DOM structure for Avenue Tennis.

Run this BEFORE using the booker to:
1. See what the login page looks like
2. See what the booking sheet looks like
3. Identify the exact CSS selectors for time slots, courts, and buttons

Usage:
    python inspect_page.py                    # Inspect without logging in
    python inspect_page.py --login            # Log in first, then inspect booking page
    python inspect_page.py --date 2026-03-01  # Inspect a specific date
    python inspect_page.py --interactive      # Open browser visually (not headless)

All screenshots and a DOM dump are saved to the screenshots/ directory.
"""

import argparse
import json
import logging
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from config import BookingConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = Path("screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def inspect_page(config: BookingConfig, login: bool = False, date: str = "", interactive: bool = False):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not interactive)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        url = config.club_url
        if date:
            url = f"{url}#?date={date}&role=member"

        logger.info("Navigating to: %s", url)
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        page.screenshot(path=str(SCREENSHOTS_DIR / "inspect_01_initial.png"), full_page=True)
        logger.info("Screenshot saved: inspect_01_initial.png")
        logger.info("Current URL: %s", page.url)

        if login and ("login" in page.url.lower() or "account" in page.url.lower() or "identity" in page.url.lower()):
            logger.info("On login page — attempting login...")
            _do_login(page, config)
            page.screenshot(path=str(SCREENSHOTS_DIR / "inspect_02_post_login.png"), full_page=True)

            # Navigate to booking page with date
            if date:
                booking_url = f"{config.club_url}#?date={date}&role=member"
            else:
                booking_url = config.club_url
            page.goto(booking_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
            page.screenshot(path=str(SCREENSHOTS_DIR / "inspect_03_booking_page.png"), full_page=True)

        # Dump the page structure
        _dump_page_info(page)

        if interactive:
            logger.info("\n=== INTERACTIVE MODE ===")
            logger.info("Browser is open. Inspect the page with DevTools (F12).")
            logger.info("Press Ctrl+C in this terminal to close.\n")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

        browser.close()


def _do_login(page, config):
    """Quick login for inspection purposes."""
    for sel in ["#onetrust-accept-btn-handler", "button:has-text('Accept')"]:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                time.sleep(0.5)
                break
        except Exception:
            continue

    for sel in ["#EmailAddress", "#Email", "#UserName", "input[type='email']", "input[name='EmailAddress']"]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.fill(config.username)
                break
        except Exception:
            continue

    for sel in ["#Password", "input[type='password']"]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.fill(config.password)
                break
        except Exception:
            continue

    for sel in ["button[type='submit']", "input[type='submit']", "button:has-text('Sign in')"]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click()
                break
        except Exception:
            continue

    page.wait_for_load_state("networkidle", timeout=20000)
    time.sleep(2)
    logger.info("Post-login URL: %s", page.url)


def _dump_page_info(page):
    """Extract and save useful DOM information."""
    logger.info("\n{'='*60}")
    logger.info("PAGE ANALYSIS")
    logger.info("{'='*60}")
    logger.info("URL: %s", page.url)
    logger.info("Title: %s", page.title())

    # Extract all interactive elements
    info = page.evaluate("""() => {
        const result = {
            forms: [],
            inputs: [],
            buttons: [],
            links_with_booking: [],
            tables: [],
            elements_with_data_attrs: [],
            elements_with_time: [],
            elements_with_available: [],
        };

        // Forms
        document.querySelectorAll('form').forEach(f => {
            result.forms.push({
                id: f.id, action: f.action, method: f.method,
                classes: f.className
            });
        });

        // Inputs
        document.querySelectorAll('input, select, textarea').forEach(el => {
            result.inputs.push({
                tag: el.tagName, type: el.type, name: el.name,
                id: el.id, placeholder: el.placeholder,
                classes: el.className
            });
        });

        // Buttons
        document.querySelectorAll('button, input[type="submit"], a.btn').forEach(el => {
            result.buttons.push({
                tag: el.tagName, text: el.textContent?.trim().substring(0, 50),
                id: el.id, classes: el.className, type: el.type,
                href: el.href || ''
            });
        });

        // Links related to booking
        document.querySelectorAll('a').forEach(a => {
            const text = a.textContent?.trim().toLowerCase() || '';
            const href = a.href?.toLowerCase() || '';
            if (text.includes('book') || text.includes('sign') || text.includes('log') ||
                href.includes('book') || href.includes('login')) {
                result.links_with_booking.push({
                    text: a.textContent?.trim().substring(0, 50),
                    href: a.href, classes: a.className, id: a.id
                });
            }
        });

        // Tables (booking grid)
        document.querySelectorAll('table').forEach(t => {
            const headers = Array.from(t.querySelectorAll('th')).map(th => th.textContent?.trim());
            const firstRow = t.querySelector('tr:nth-child(2)');
            const firstRowCells = firstRow ?
                Array.from(firstRow.querySelectorAll('td')).map(td => ({
                    text: td.textContent?.trim().substring(0, 30),
                    classes: td.className,
                    dataAttrs: Object.fromEntries(
                        Array.from(td.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])
                    )
                })) : [];
            result.tables.push({
                id: t.id, classes: t.className,
                headers: headers, sampleRow: firstRowCells,
                rowCount: t.querySelectorAll('tr').length
            });
        });

        // Elements with data- attributes related to booking
        document.querySelectorAll('[data-time], [data-start], [data-court], [data-resource], [data-date], [data-duration]').forEach(el => {
            result.elements_with_data_attrs.push({
                tag: el.tagName, classes: el.className,
                text: el.textContent?.trim().substring(0, 30),
                dataAttrs: Object.fromEntries(
                    Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])
                )
            });
        });

        // Elements containing time-like text (HH:MM)
        document.querySelectorAll('td, a, div, span, button').forEach(el => {
            const text = el.textContent?.trim() || '';
            if (/^\\d{1,2}:\\d{2}/.test(text) && text.length < 20) {
                result.elements_with_time.push({
                    tag: el.tagName, text: text, classes: el.className,
                    id: el.id, clickable: el.tagName === 'A' || el.tagName === 'BUTTON'
                });
            }
        });

        // Elements with 'available' in class
        document.querySelectorAll('[class*="available"], [class*="Available"]').forEach(el => {
            result.elements_with_available.push({
                tag: el.tagName, classes: el.className,
                text: el.textContent?.trim().substring(0, 50),
            });
        });

        return result;
    }""")

    # Save to file
    output_path = SCREENSHOTS_DIR / "page_analysis.json"
    with open(output_path, "w") as f:
        json.dump(info, f, indent=2)
    logger.info("Full page analysis saved to: %s", output_path)

    # Print summary
    print(f"\n{'='*60}")
    print("PAGE STRUCTURE SUMMARY")
    print(f"{'='*60}")
    print(f"  Forms found:              {len(info['forms'])}")
    print(f"  Input fields:             {len(info['inputs'])}")
    print(f"  Buttons:                  {len(info['buttons'])}")
    print(f"  Booking-related links:    {len(info['links_with_booking'])}")
    print(f"  Tables (booking grids):   {len(info['tables'])}")
    print(f"  Elements with data-attrs: {len(info['elements_with_data_attrs'])}")
    print(f"  Elements with times:      {len(info['elements_with_time'])}")
    print(f"  'Available' elements:     {len(info['elements_with_available'])}")

    if info["tables"]:
        print(f"\n--- Tables ---")
        for i, table in enumerate(info["tables"]):
            print(f"  Table {i+1}: id='{table['id']}' class='{table['classes']}'")
            print(f"    Headers: {table['headers']}")
            print(f"    Rows: {table['rowCount']}")
            if table["sampleRow"]:
                print(f"    Sample cell: {table['sampleRow'][0]}")

    if info["elements_with_time"][:10]:
        print(f"\n--- Time Elements (first 10) ---")
        for el in info["elements_with_time"][:10]:
            print(f"  <{el['tag'].lower()}> '{el['text']}' class='{el['classes']}'")

    if info["buttons"][:10]:
        print(f"\n--- Buttons (first 10) ---")
        for btn in info["buttons"][:10]:
            print(f"  <{btn['tag'].lower()}> '{btn['text']}' id='{btn['id']}' class='{btn['classes']}'")

    print(f"\nFull details in: {output_path}")
    print(f"Screenshots in: {SCREENSHOTS_DIR}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect ClubSpark booking page structure")
    parser.add_argument("--login", action="store_true", help="Log in before inspecting")
    parser.add_argument("--date", type=str, default="", help="Date to inspect (YYYY-MM-DD)")
    parser.add_argument("--interactive", action="store_true", help="Open browser visually")
    args = parser.parse_args()

    config = BookingConfig.from_env()
    if not config.club_url:
        print("ERROR: Set CLUB_URL in .env first")
        exit(1)

    inspect_page(config, login=args.login, date=args.date, interactive=args.interactive)
