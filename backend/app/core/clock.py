"""\"Today\" for the product is the Turkish calendar day, not the server's or UTC's."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

TR = ZoneInfo("Europe/Istanbul")  # needs the tzdata package on Windows


def tr_today(now: datetime | None = None) -> date:
    return (now or datetime.now(timezone.utc)).astimezone(TR).date()


def tr_day_start_utc(now: datetime | None = None) -> datetime:
    return datetime.combine(tr_today(now), datetime.min.time(), tzinfo=TR).astimezone(timezone.utc)
