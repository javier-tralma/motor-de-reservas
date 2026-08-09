import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Optional

from .time_utils import create_aware_datetime, get_now, intervals_overlap


@dataclass
class Slot:
    starts_at: datetime
    ends_at: datetime
    provider_id: uuid.UUID


@dataclass
class AvailabilityRequest:
    business_id: uuid.UUID
    service_id: uuid.UUID
    target_date: date
    provider_id: Optional[uuid.UUID] = None


class AvailabilityEngine:
    def __init__(self, get_now_fn=None):
        self.get_now_fn = get_now_fn or get_now

    def calculate_availability(
        self,
        target_date: date,
        timezone_str: str,
        minimum_notice_minutes: int,
        horizon_days: int,
        slot_interval_minutes: int,
        service_duration_minutes: int,
        rules: List,  # Lista de dicts o objetos con provider_id, start_time, end_time, weekday
        time_offs: List,  # Lista de dicts o objetos con provider_id, starts_at, ends_at
        bookings: List,  # Lista de dicts o objetos con provider_id, starts_at, ends_at
    ) -> List[Slot]:

        from datetime import timezone
        from zoneinfo import ZoneInfo

        now = self.get_now_fn("UTC")
        local_tz = ZoneInfo(timezone_str)
        local_now = now.astimezone(local_tz)

        # 1. Validar fecha
        if target_date < local_now.date():
            return []

        if target_date > local_now.date() + timedelta(days=horizon_days):
            return []

        weekday = target_date.weekday()

        # 2. Filtrar reglas del día
        day_rules = [r for r in rules if r.weekday == weekday]
        if not day_rules:
            return []

        from .time_utils import NonExistentTimeError, get_dst_gap_start_utc

        # 3. Generar slots candidatos
        candidates: List[Slot] = []
        for rule in day_rules:
            # Según invariante P0, start_time < end_time.
            # Convertimos el fin del turno a UTC. Si cae en un salto DST (hora inexistente),
            # truncamos el fin del turno al instante exacto del salto.
            try:
                rule_end_dt = create_aware_datetime(target_date, rule.end_time, timezone_str, fold=0)
                rule_end_utc = rule_end_dt.astimezone(timezone.utc)
            except NonExistentTimeError:
                rule_end_utc = get_dst_gap_start_utc(target_date, timezone_str, rule.end_time)

            current_local = datetime.combine(target_date, rule.start_time)

            while True:
                # Obtenemos el instante UTC de inicio. Si la hora no existe, avanzamos.
                try:
                    slot_start_aware = create_aware_datetime(
                        current_local.date(), current_local.time(), timezone_str, fold=0
                    )
                    slot_start_utc = slot_start_aware.astimezone(timezone.utc)
                except NonExistentTimeError:
                    current_local += timedelta(minutes=slot_interval_minutes)
                    # Si al sumar el intervalo cruzamos de día y la regla no, rompemos
                    if current_local.date() > target_date:
                        break
                    continue

                slot_end_utc = slot_start_utc + timedelta(minutes=service_duration_minutes)

                # Si el slot termina después del fin del turno UTC, terminamos esta regla.
                if slot_end_utc > rule_end_utc:
                    break

                if slot_start_utc >= now + timedelta(minutes=minimum_notice_minutes):
                    candidates.append(
                        Slot(
                            starts_at=slot_start_aware,
                            ends_at=slot_end_utc.astimezone(local_tz),
                            provider_id=rule.provider_id,
                        )
                    )

                current_local += timedelta(minutes=slot_interval_minutes)

        # 4. Filtrar por solapamientos
        available_slots = []
        for slot in candidates:
            has_conflict = False

            # Check time offs
            for to in time_offs:
                if to.provider_id == slot.provider_id:
                    if intervals_overlap(slot.starts_at, slot.ends_at, to.starts_at, to.ends_at):
                        has_conflict = True
                        break

            if has_conflict:
                continue

            # Check bookings
            for b in bookings:
                if b.provider_id == slot.provider_id:
                    if intervals_overlap(slot.starts_at, slot.ends_at, b.starts_at, b.ends_at):
                        has_conflict = True
                        break

            if not has_conflict:
                available_slots.append(slot)

        # 5. Ordenar
        available_slots.sort(key=lambda s: (s.starts_at, s.provider_id))

        return available_slots
