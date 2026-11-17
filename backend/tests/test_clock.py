from datetime import date, datetime, timezone

from app.core.clock import tr_day_start_utc, tr_today


def test_turkish_day_boundary():
    late = datetime(2026, 11, 14, 21, 30, tzinfo=timezone.utc)  # 00:30 on the 15th in Istanbul (UTC+3)
    assert tr_today(late) == date(2026, 11, 15)
    assert tr_day_start_utc(late) == datetime(2026, 11, 14, 21, 0, tzinfo=timezone.utc)
    early = datetime(2026, 11, 14, 20, 59, tzinfo=timezone.utc)  # 23:59 on the 14th
    assert tr_today(early) == date(2026, 11, 14)
    assert tr_day_start_utc(early) == datetime(2026, 11, 13, 21, 0, tzinfo=timezone.utc)
