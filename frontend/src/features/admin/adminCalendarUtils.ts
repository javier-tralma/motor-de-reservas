import type { CalendarEventItem } from '../../lib/api/admin';

export interface FullCalendarEventItem {
  id: string;
  title: string;
  start: string;
  end: string;
  backgroundColor: string;
  borderColor: string;
  extendedProps: {
    kind: 'booking' | 'time_off';
    id: string;
    provider_name: string;
    booking_status: string | null;
  };
}

export function getBookingStatusLabel(status: string | null): string {
  switch (status) {
    case 'confirmed':
      return 'Confirmada';
    case 'completed':
      return 'Completada';
    case 'no_show':
      return 'Inasistencia';
    case 'cancelled':
      return 'Cancelada';
    default:
      return status || 'Reserva';
  }
}

export function mapCalendarEventToFullCalendar(ev: CalendarEventItem): FullCalendarEventItem {
  const isBooking = ev.kind === 'booking';

  if (isBooking) {
    const statusLabel = getBookingStatusLabel(ev.booking_status);
    const providerText = ev.provider_name ? `${ev.provider_name} — ` : '';
    const customerText = ev.customer_display_name || 'Cliente';
    const serviceText = ev.service_name || 'Servicio';
    const title = `[${statusLabel}] ${providerText}${customerText} - ${serviceText}`;

    let backgroundColor: string;
    let borderColor: string;

    switch (ev.booking_status) {
      case 'cancelled':
        backgroundColor = '#475569'; // Slate 600
        borderColor = '#334155'; // Slate 700
        break;
      case 'completed':
        backgroundColor = '#2563eb'; // Blue 600
        borderColor = '#1d4ed8'; // Blue 700
        break;
      case 'no_show':
        backgroundColor = '#d97706'; // Amber 600
        borderColor = '#b45309'; // Amber 700
        break;
      case 'confirmed':
      default:
        backgroundColor = '#4f46e5'; // Indigo 600
        borderColor = '#4338ca'; // Indigo 700
        break;
    }

    return {
      id: ev.id,
      title,
      start: ev.starts_at,
      end: ev.ends_at,
      backgroundColor,
      borderColor,
      extendedProps: {
        kind: 'booking',
        id: ev.id,
        provider_name: ev.provider_name || '',
        booking_status: ev.booking_status,
      },
    };
  }

  // Time off event
  const providerText = ev.provider_name ? ` ${ev.provider_name}` : '';
  const reasonText = ev.reason ? ` — ${ev.reason}` : '';
  const title = `Bloqueo:${providerText}${reasonText}`;

  return {
    id: ev.id,
    title,
    start: ev.starts_at,
    end: ev.ends_at,
    backgroundColor: '#dc2626', // Red 600
    borderColor: '#b91c1c', // Red 700
    extendedProps: {
      kind: 'time_off',
      id: ev.id,
      provider_name: ev.provider_name || '',
      booking_status: null,
    },
  };
}

export function mapCalendarEventsToFullCalendar(events: CalendarEventItem[]): FullCalendarEventItem[] {
  return events.map(mapCalendarEventToFullCalendar);
}
