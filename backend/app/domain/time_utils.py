from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


class NonExistentTimeError(Exception):
    pass


def create_aware_datetime(d: date, t: time, tz_name: str, fold: int = 0) -> datetime:
    """
    Creates a timezone-aware datetime from a date and a time.
    Handles ambiguous/nonexistent times safely using a round-trip check.
    """
    tz = ZoneInfo(tz_name)
    dt_local_unaware = datetime.combine(d, t)
    dt_local_unaware = dt_local_unaware.replace(fold=fold)

    # 1. Anclar a la zona horaria local
    dt_aware = dt_local_unaware.replace(tzinfo=tz)

    # 2. Convertir a UTC
    dt_utc = dt_aware.astimezone(timezone.utc)

    # 3. Round-trip de vuelta a local
    dt_roundtrip = dt_utc.astimezone(tz)

    # Si la hora cambió al volver, es inexistente (gap)
    # Comparamos ignorando el tzinfo para ver si la hora de reloj es la misma
    if dt_roundtrip.replace(tzinfo=None) != dt_local_unaware:
        raise NonExistentTimeError(f"Non-existent time {dt_local_unaware} in timezone {tz_name}")

    return dt_aware


def get_local_day_bounds_utc(local_date: date, tz_name: str) -> tuple[datetime, datetime]:
    """
    Devuelve la ventana UTC exacta [start_utc, end_utc) que abarca el día civil completo.
    Maneja el caso donde las 00:00 del día son inexistentes en la zona local.
    """
    tz = ZoneInfo(tz_name)

    # Inicio del día
    start_unaware = datetime.combine(local_date, time(0, 0))
    start_aware = start_unaware.replace(tzinfo=tz)
    start_utc = start_aware.astimezone(timezone.utc)

    # Comprobación de existencia para start
    if start_utc.astimezone(tz).replace(tzinfo=None) != start_unaware:
        # 00:00 no existe. Significa que hubo un salto adelante a la medianoche.
        # El día realmente empieza en el instante UTC equivalente al final del día anterior.
        prev_day_end_unaware = datetime.combine(local_date - timedelta(days=1), time(23, 59, 59, 999999))
        start_utc = prev_day_end_unaware.replace(tzinfo=tz).astimezone(timezone.utc) + timedelta(microseconds=1)

    # Fin del día (inicio del día siguiente)
    end_unaware = datetime.combine(local_date + timedelta(days=1), time(0, 0))
    end_aware = end_unaware.replace(tzinfo=tz)
    end_utc = end_aware.astimezone(timezone.utc)

    # Comprobación de existencia para end
    if end_utc.astimezone(tz).replace(tzinfo=None) != end_unaware:
        # El 00:00 del día siguiente no existe.
        curr_day_end_unaware = datetime.combine(local_date, time(23, 59, 59, 999999))
        end_utc = curr_day_end_unaware.replace(tzinfo=tz).astimezone(timezone.utc) + timedelta(microseconds=1)

    return start_utc, end_utc


def get_dst_gap_start_utc(local_date: date, tz_name: str, t: time) -> datetime:
    """
    Returns the exact UTC instant when the DST gap started.
    If a time falls into a gap, the gap started exactly at the last valid time before the jump.
    """
    tz = ZoneInfo(tz_name)
    # The gap is usually 1 hour. So if we subtract 1 hour from the unaware time, we are safely before the gap
    unaware_before = datetime.combine(local_date, t) - timedelta(hours=1)
    aware_before = unaware_before.replace(tzinfo=tz)
    aware_before.astimezone(timezone.utc)
    # The gap start is the instant the jump happens.
    # To find it, we can just look at the timezone transitions.
    # Actually, in Python 3, aware_before.astimezone(timezone.utc) is safe.
    # A simpler way is to use the unaware time.
    # But since we want the EXACT moment, we use the previous day.
    # If the jump is from 00:00 to 01:00, unaware_before is 23:00.

    # We can do binary search or just use the tzinfo tzname transitions.
    # But for a simple implementation, if time `t` is invalid, the gap must be the jump that made it invalid.
    # Let's just find the first valid time going backwards minute by minute.
    curr = datetime.combine(local_date, t)
    while True:
        curr -= timedelta(minutes=1)
        try:
            return create_aware_datetime(curr.date(), curr.time(), tz_name).astimezone(timezone.utc) + timedelta(
                minutes=1
            )
        except NonExistentTimeError:
            continue


def add_duration(dt: datetime, minutes: int) -> datetime:
    """
    Suma minutos a un instante de tiempo, siempre en UTC para evitar DST jumps,
    y devuelve la hora en la zona original.
    """
    tz = dt.tzinfo
    dt_utc = dt.astimezone(timezone.utc)
    dt_utc_end = dt_utc + timedelta(minutes=minutes)
    return dt_utc_end.astimezone(tz)


def get_now(tz_name: str = "UTC") -> datetime:
    """Returns the current aware datetime in the specified timezone."""
    return datetime.now(ZoneInfo(tz_name))


def intervals_overlap(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
    """
    Checks if two [start, end) intervals overlap.
    Solape ocurre si a_start < b_end and b_start < a_end
    """
    return start1 < end2 and start2 < end1


def format_local_iso(dt: datetime, tz_name: str) -> str:
    """
    Convierte un instante timezone-aware (típicamente UTC) a la zona horaria del negocio
    y lo serializa como cadena ISO 8601 con su offset explícito (ej. 2026-08-15T09:00:00-04:00).
    Si el datetime es naive (por ejemplo de PostgreSQL), se normaliza explícitamente como UTC antes de convertir.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    tz = ZoneInfo(tz_name)
    return dt.astimezone(tz).isoformat()
