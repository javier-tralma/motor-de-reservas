import uuid
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import pytest

from app.domain.availability import AvailabilityEngine


class MockRule:
    def __init__(self, provider_id, weekday, start_time, end_time):
        self.provider_id = provider_id
        self.weekday = weekday
        self.start_time = start_time
        self.end_time = end_time


class MockTimeOff:
    def __init__(self, provider_id, starts_at, ends_at):
        self.provider_id = provider_id
        self.starts_at = starts_at
        self.ends_at = ends_at


class MockBooking:
    def __init__(self, provider_id, starts_at, ends_at):
        self.provider_id = provider_id
        self.starts_at = starts_at
        self.ends_at = ends_at


@pytest.fixture
def engine():
    def mock_now(tz="UTC"):
        # Use 12:00 UTC so that local time is definitely the same day (09:00 or 08:00 in Santiago)
        return datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)

    return AvailabilityEngine(get_now_fn=mock_now)


def calculate(
    engine,
    target_date,
    rules=None,
    time_offs=None,
    bookings=None,
    notice=0,
    horizon=30,
    interval=30,
    duration=60,
    tz="America/Santiago",
):
    return engine.calculate_availability(
        target_date=target_date,
        timezone_str=tz,
        minimum_notice_minutes=notice,
        horizon_days=horizon,
        slot_interval_minutes=interval,
        service_duration_minutes=duration,
        rules=rules or [],
        time_offs=time_offs or [],
        bookings=bookings or [],
    )


def test_overlap_adjacent(engine):
    p = uuid.uuid4()
    tz = ZoneInfo("America/Santiago")
    b = MockBooking(
        p,
        datetime(2023, 1, 2, 11, 0, tzinfo=tz).astimezone(timezone.utc),
        datetime(2023, 1, 2, 12, 0, tzinfo=tz).astimezone(timezone.utc),
    )
    slots = calculate(engine, date(2023, 1, 2), rules=[MockRule(p, 0, time(10, 0), time(12, 0))], bookings=[b])
    assert len(slots) == 1
    assert slots[0].starts_at.time() == time(10, 0)


def test_overlap_contained(engine):
    p = uuid.uuid4()
    tz = ZoneInfo("America/Santiago")
    b = MockBooking(
        p,
        datetime(2023, 1, 2, 10, 30, tzinfo=tz).astimezone(timezone.utc),
        datetime(2023, 1, 2, 11, 0, tzinfo=tz).astimezone(timezone.utc),
    )
    slots = calculate(engine, date(2023, 1, 2), rules=[MockRule(p, 0, time(10, 0), time(12, 0))], bookings=[b])
    assert len(slots) == 1
    assert slots[0].starts_at.time() == time(11, 0)


def test_overlap_identical(engine):
    p = uuid.uuid4()
    tz = ZoneInfo("America/Santiago")
    b = MockBooking(
        p,
        datetime(2023, 1, 2, 10, 0, tzinfo=tz).astimezone(timezone.utc),
        datetime(2023, 1, 2, 11, 0, tzinfo=tz).astimezone(timezone.utc),
    )
    slots = calculate(engine, date(2023, 1, 2), rules=[MockRule(p, 0, time(10, 0), time(11, 0))], bookings=[b])
    assert len(slots) == 0


def test_duration_fits_exactly(engine):
    p = uuid.uuid4()
    slots = calculate(engine, date(2023, 1, 2), rules=[MockRule(p, 0, time(10, 0), time(11, 0))], duration=60)
    assert len(slots) == 1
    assert slots[0].starts_at.time() == time(10, 0)


def test_duration_exceeds(engine):
    p = uuid.uuid4()
    slots = calculate(engine, date(2023, 1, 2), rules=[MockRule(p, 0, time(10, 0), time(10, 59))], duration=60)
    assert len(slots) == 0


def test_granularity_does_not_divide(engine):
    p = uuid.uuid4()
    slots = calculate(
        engine, date(2023, 1, 2), rules=[MockRule(p, 0, time(10, 0), time(11, 0))], interval=15, duration=45
    )
    assert len(slots) == 2
    assert slots[0].starts_at.time() == time(10, 0)
    assert slots[1].starts_at.time() == time(10, 15)


def test_dst_nonexistent(engine):
    p = uuid.uuid4()
    slots = calculate(
        engine, date(2024, 9, 8), rules=[MockRule(p, 6, time(0, 0), time(2, 0))], interval=30, duration=30, horizon=1000
    )
    assert len(slots) == 2
    assert slots[0].starts_at.time() == time(1, 0)
    assert slots[1].starts_at.time() == time(1, 30)


def test_dst_ambiguous_uses_fold(engine):
    p = uuid.uuid4()
    slots = calculate(
        engine,
        date(2024, 4, 6),
        rules=[MockRule(p, 5, time(23, 0), time(23, 59))],
        interval=60,
        duration=59,
        horizon=1000,
    )
    assert len(slots) == 1
    assert slots[0].starts_at.fold == 0


def test_system_timezone_isolation():
    def mock_now(tz="UTC"):
        return datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)

    engine = AvailabilityEngine(get_now_fn=mock_now)
    p = uuid.uuid4()
    slots = calculate(engine, date(2023, 1, 2), rules=[MockRule(p, 0, time(10, 0), time(12, 0))])
    assert len(slots) == 3


def test_notice_edge(engine):
    p = uuid.uuid4()
    # Now = 12:00 UTC. Notice = 10 hours. Notice limit = 22:00 UTC.
    # 18:30 Santiago (Summer) is 21:30 UTC. Rejected.
    # 19:00 Santiago (Summer) is 22:00 UTC. Exact match -> Accepted.
    # 19:30 Santiago (Summer) is 22:30 UTC. Accepted but duration 60m exceeds 20:00 -> Rejected.
    # So we should get 19:00 only.
    slots = calculate(engine, date(2023, 1, 1), rules=[MockRule(p, 6, time(18, 30), time(20, 0))], notice=600)
    assert len(slots) == 1
    assert slots[0].starts_at.time() == time(19, 0)


def test_horizon_empty(engine):
    p = uuid.uuid4()
    # Now is 2023-01-01. Target is 2023-02-01. Horizon is 30. Diff is 31 days. So empty.
    slots = calculate(engine, date(2023, 2, 1), rules=[MockRule(p, 2, time(10, 0), time(12, 0))], horizon=30)
    assert len(slots) == 0


def test_horizon_edge(engine):
    p = uuid.uuid4()
    # Now is 2023-01-01. Target is 2023-01-31. Horizon is 30. Diff is 30 days. So fits.
    slots = calculate(engine, date(2023, 1, 31), rules=[MockRule(p, 1, time(10, 0), time(12, 0))], horizon=30)
    assert len(slots) == 3


def test_past_date(engine):
    p = uuid.uuid4()
    slots = calculate(engine, date(2022, 12, 31), rules=[MockRule(p, 5, time(10, 0), time(12, 0))])
    assert len(slots) == 0


def test_empty_candidates(engine):
    slots = calculate(engine, date(2023, 1, 2), rules=[])
    assert slots == []


def test_isolation_providers(engine):
    p1 = uuid.uuid4()
    p2 = uuid.uuid4()
    tz = ZoneInfo("America/Santiago")
    b = MockBooking(
        p1,
        datetime(2023, 1, 2, 10, 0, tzinfo=tz).astimezone(timezone.utc),
        datetime(2023, 1, 2, 12, 0, tzinfo=tz).astimezone(timezone.utc),
    )
    slots = calculate(
        engine,
        date(2023, 1, 2),
        rules=[MockRule(p1, 0, time(10, 0), time(12, 0)), MockRule(p2, 0, time(10, 0), time(12, 0))],
        bookings=[b],
    )
    assert len(slots) == 3
    for s in slots:
        assert s.provider_id == p2


def test_multiple_intervals(engine):
    p = uuid.uuid4()
    slots = calculate(
        engine,
        date(2023, 1, 2),
        rules=[MockRule(p, 0, time(9, 0), time(13, 0)), MockRule(p, 0, time(14, 0), time(18, 0))],
    )
    assert len(slots) == 14
    assert slots[0].starts_at.time() == time(9, 0)
    assert slots[7].starts_at.time() == time(14, 0)


def test_timeoff_partial(engine):
    p = uuid.uuid4()
    tz = ZoneInfo("America/Santiago")
    t = MockTimeOff(
        p,
        datetime(2023, 1, 2, 10, 30, tzinfo=tz).astimezone(timezone.utc),
        datetime(2023, 1, 2, 11, 0, tzinfo=tz).astimezone(timezone.utc),
    )
    slots = calculate(engine, date(2023, 1, 2), rules=[MockRule(p, 0, time(10, 0), time(12, 0))], time_offs=[t])
    assert len(slots) == 1
    assert slots[0].starts_at.time() == time(11, 0)


def test_timeoff_multiday(engine):
    p = uuid.uuid4()
    tz = ZoneInfo("America/Santiago")
    t = MockTimeOff(
        p,
        datetime(2023, 1, 1, 0, 0, tzinfo=tz).astimezone(timezone.utc),
        datetime(2023, 1, 3, 0, 0, tzinfo=tz).astimezone(timezone.utc),
    )
    slots = calculate(engine, date(2023, 1, 2), rules=[MockRule(p, 0, time(10, 0), time(12, 0))], time_offs=[t])
    assert len(slots) == 0


def test_night_booking_blocks(engine):
    p = uuid.uuid4()
    tz = ZoneInfo("America/Santiago")
    b = MockBooking(
        p,
        datetime(2023, 1, 2, 22, 30, tzinfo=tz).astimezone(timezone.utc),
        datetime(2023, 1, 2, 23, 30, tzinfo=tz).astimezone(timezone.utc),
    )
    slots = calculate(engine, date(2023, 1, 2), rules=[MockRule(p, 0, time(22, 0), time(23, 59))], bookings=[b])
    assert len(slots) == 0
