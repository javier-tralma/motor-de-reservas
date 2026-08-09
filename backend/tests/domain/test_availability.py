import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.availability import AvailabilityEngine
from app.domain.time_utils import create_aware_datetime, intervals_overlap


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


def test_intervals_overlap():
    tz = ZoneInfo("UTC")
    base = datetime(2023, 1, 1, 10, 0, tzinfo=tz)

    # [10:00, 11:00) vs [11:00, 12:00) - Adjacent, no overlap
    assert not intervals_overlap(base, base + timedelta(hours=1), base + timedelta(hours=1), base + timedelta(hours=2))

    # [10:00, 11:00) vs [10:30, 11:30) - Overlap
    assert intervals_overlap(
        base, base + timedelta(hours=1), base + timedelta(minutes=30), base + timedelta(hours=1, minutes=30)
    )  # noqa: E501


def test_create_aware_datetime_dst():
    # Chile shifts to DST (spring forward) typically in September.
    # Ex: 2023-09-02 23:59:59 -> 2023-09-03 01:00:00
    d = date(2023, 9, 3)
    t = time(0, 30)  # This time does not exist (clocks spring forward from 00:00 to 01:00)

    import pytest

    from app.domain.time_utils import NonExistentTimeError

    with pytest.raises(NonExistentTimeError):
        create_aware_datetime(d, t, "America/Santiago")


def test_availability_engine():
    provider_1 = uuid.uuid4()
    provider_2 = uuid.uuid4()

    def mock_now(tz):
        return datetime(2023, 1, 1, 8, 0, tzinfo=ZoneInfo(tz))

    engine = AvailabilityEngine(get_now_fn=mock_now)

    rules = [MockRule(provider_1, 0, time(9, 0), time(12, 0)), MockRule(provider_2, 0, time(10, 0), time(14, 0))]

    tz_santiago = ZoneInfo("America/Santiago")

    time_offs = [
        MockTimeOff(
            provider_1,
            datetime(2023, 1, 2, 9, 30, tzinfo=tz_santiago),
            datetime(2023, 1, 2, 10, 30, tzinfo=tz_santiago),
        )
    ]  # noqa: E501

    bookings = [
        MockBooking(
            provider_2, datetime(2023, 1, 2, 11, 0, tzinfo=tz_santiago), datetime(2023, 1, 2, 12, 0, tzinfo=tz_santiago)
        )
    ]  # noqa: E501

    # Lunes 2 de Enero de 2023
    target_date = date(2023, 1, 2)

    slots = engine.calculate_availability(
        target_date=target_date,
        timezone_str="America/Santiago",
        minimum_notice_minutes=60,
        horizon_days=30,
        slot_interval_minutes=30,
        service_duration_minutes=60,
        rules=rules,
        time_offs=time_offs,
        bookings=bookings,
    )

    # Reglas Provider 1: [9:00 - 12:00]
    # TimeOff [9:30 - 10:30]
    # Candidates duration=60, int=30:
    # 9:00-10:00 (Cruza con TimeOff 9:30-10:30) -> NO
    # 9:30-10:30 (Cruza con TimeOff) -> NO
    # 10:00-11:00 (Cruza con TimeOff? TimeOff termina a las 10:30, así que se solapan) -> NO
    # 10:30-11:30 -> SI
    # 11:00-12:00 -> SI

    # Reglas Provider 2: [10:00 - 14:00]
    # Bookings [11:00 - 12:00]
    # 10:00-11:00 -> SI
    # 10:30-11:30 -> NO (solapa booking)
    # 11:00-12:00 -> NO (solapa booking)
    # 11:30-12:30 -> NO (solapa booking)
    # 12:00-13:00 -> SI
    # 12:30-13:30 -> SI
    # 13:00-14:00 -> SI

    p1_slots = [s for s in slots if s.provider_id == provider_1]
    p2_slots = [s for s in slots if s.provider_id == provider_2]

    assert len(p1_slots) == 2
    assert p1_slots[0].starts_at.time() == time(10, 30)
    assert p1_slots[1].starts_at.time() == time(11, 0)

    assert len(p2_slots) == 4
    assert p2_slots[0].starts_at.time() == time(10, 0)
    assert p2_slots[1].starts_at.time() == time(12, 0)
    assert p2_slots[2].starts_at.time() == time(12, 30)
    assert p2_slots[3].starts_at.time() == time(13, 0)
