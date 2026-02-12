"""Notification helpers for booking results."""

import logging
import requests
from config import BookingConfig

logger = logging.getLogger(__name__)


def send_notification(config: BookingConfig, title: str, message: str) -> None:
    """Send a notification via configured channels."""
    if config.ntfy_topic:
        _send_ntfy(config.ntfy_topic, title, message)
    if config.notification_webhook_url:
        _send_webhook(config.notification_webhook_url, title, message)
    if not config.ntfy_topic and not config.notification_webhook_url:
        logger.info("No notification channels configured. Result: %s - %s", title, message)


def _send_ntfy(topic: str, title: str, message: str) -> None:
    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode("utf-8"),
            headers={"Title": title, "Priority": "high"},
            timeout=10,
        )
        logger.info("ntfy notification sent to topic: %s", topic)
    except Exception as e:
        logger.error("Failed to send ntfy notification: %s", e)


def _send_webhook(url: str, title: str, message: str) -> None:
    try:
        payload = {"text": f"*{title}*\n{message}"}
        requests.post(url, json=payload, timeout=10)
        logger.info("Webhook notification sent")
    except Exception as e:
        logger.error("Failed to send webhook notification: %s", e)
