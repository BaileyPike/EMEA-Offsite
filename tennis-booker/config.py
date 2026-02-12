"""Configuration loader for tennis court booker."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BookingConfig:
    club_url: str = ""
    club_login_url: str = ""
    username: str = ""
    password: str = ""
    preferred_day: str = "saturday"
    preferred_times: list[str] = field(default_factory=lambda: ["18:00"])
    preferred_courts: list[str] = field(default_factory=list)
    duration_minutes: int = 60
    platform: str = "clubspark"
    days_in_advance: int = 14
    timezone: str = "Europe/London"
    notification_webhook_url: str = ""
    ntfy_topic: str = ""

    @classmethod
    def from_env(cls) -> "BookingConfig":
        times_str = os.getenv("PREFERRED_TIMES", "18:00")
        courts_str = os.getenv("PREFERRED_COURTS", "")

        return cls(
            club_url=os.getenv("CLUB_URL", ""),
            club_login_url=os.getenv("CLUB_LOGIN_URL", ""),
            username=os.getenv("USERNAME", ""),
            password=os.getenv("PASSWORD", ""),
            preferred_day=os.getenv("PREFERRED_DAY", "saturday").lower(),
            preferred_times=[t.strip() for t in times_str.split(",") if t.strip()],
            preferred_courts=[c.strip() for c in courts_str.split(",") if c.strip()],
            duration_minutes=int(os.getenv("DURATION_MINUTES", "60")),
            platform=os.getenv("PLATFORM", "clubspark").lower(),
            days_in_advance=int(os.getenv("DAYS_IN_ADVANCE", "14")),
            timezone=os.getenv("TIMEZONE", "Europe/London"),
            notification_webhook_url=os.getenv("NOTIFICATION_WEBHOOK_URL", ""),
            ntfy_topic=os.getenv("NTFY_TOPIC", ""),
        )
