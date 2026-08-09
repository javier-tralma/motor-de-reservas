from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.domain.time_utils import (
    NonExistentTimeError,
    create_aware_datetime,
    get_dst_gap_start_utc,
    get_local_day_bounds_utc,
)


def test_get_local_day_bounds_normal_day():
    d = date(2023, 1, 15)
    tz = "America/Santiago"
    start_utc, end_utc = get_local_day_bounds_utc(d, tz)

    assert start_utc.astimezone(ZoneInfo(tz)) == datetime(2023, 1, 15, 0, 0, tzinfo=ZoneInfo(tz))
    assert end_utc.astimezone(ZoneInfo(tz)) == datetime(2023, 1, 16, 0, 0, tzinfo=ZoneInfo(tz))
    assert (end_utc - start_utc) == timedelta(hours=24)


def test_get_local_day_bounds_dst_gap():
    d = date(2024, 9, 8)
    tz = "America/Santiago"
    start_utc, end_utc = get_local_day_bounds_utc(d, tz)

    assert start_utc.astimezone(ZoneInfo(tz)) == datetime(2024, 9, 8, 1, 0, tzinfo=ZoneInfo(tz))
    assert end_utc.astimezone(ZoneInfo(tz)) == datetime(2024, 9, 9, 0, 0, tzinfo=ZoneInfo(tz))
    assert (end_utc - start_utc) == timedelta(hours=23)


def test_get_local_day_bounds_dst_fallback():
    d = date(2024, 4, 6)
    tz = "America/Santiago"
    start_utc, end_utc = get_local_day_bounds_utc(d, tz)
    assert (end_utc - start_utc) == timedelta(hours=25)


def test_create_aware_datetime_nonexistent():
    with pytest.raises(NonExistentTimeError):
        create_aware_datetime(date(2024, 9, 8), time(0, 30), "America/Santiago")


def test_get_dst_gap_start_utc():
    gap_start = get_dst_gap_start_utc(date(2024, 9, 8), "America/Santiago", time(0, 30))
    expected = datetime(2024, 9, 8, 1, 0, tzinfo=ZoneInfo("America/Santiago")).astimezone(timezone.utc)
    assert gap_start == expected


def test_create_aware_datetime_ambiguous():
    # In America/Santiago, on 2024-04-06 at 23:59:59, clocks fall back to 23:00:00.
    # So 23:30 occurs twice.
    # fold=0 means the first occurrence (UTC-3).
    # fold=1 means the second occurrence (UTC-4).
    d = date(2024, 4, 6)
    t = time(23, 30)

    dt_fold_0 = create_aware_datetime(d, t, "America/Santiago", fold=0)
    dt_fold_1 = create_aware_datetime(d, t, "America/Santiago", fold=1)

    assert dt_fold_0.utcoffset() == timedelta(hours=-3)
    assert dt_fold_1.utcoffset() == timedelta(hours=-4)
    assert (dt_fold_1.astimezone(timezone.utc) - dt_fold_0.astimezone(timezone.utc)) == timedelta(hours=1)


def test_system_tz_handling():
    import os
    import time as time_mod

    # Store original TZ
    orig_tz = os.environ.get("TZ")

    try:
        # Set to something completely different
        os.environ["TZ"] = "Asia/Tokyo"
        time_mod.tzset()

        # Test that our time utils still work correctly for America/Santiago
        # despite the system timezone being Asia/Tokyo
        start_utc, end_utc = get_local_day_bounds_utc(date(2023, 1, 15), "America/Santiago")

        # The bounds should be exactly as if the system was anything else
        assert start_utc == datetime(2023, 1, 15, 3, 0, tzinfo=timezone.utc)  # 00:00 UTC-3 is 03:00 UTC
        assert end_utc == datetime(2023, 1, 16, 3, 0, tzinfo=timezone.utc)

    finally:
        # Restore
        if orig_tz is not None:
            os.environ["TZ"] = orig_tz
        else:
            del os.environ["TZ"]
        time_mod.tzset()
