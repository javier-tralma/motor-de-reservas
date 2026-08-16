import type { CalendarEventItem } from '../../lib/api/admin';

export interface FullCalendarEventItem {
  id: string;
  title: string;
  start: string;
  end: string;
  color: string;
  backgroundColor: string;
  borderColor: string;
  extendedProps: {
    kind: 'booking' | 'time_off';
    id: string;
    provider_name: string;
    booking_status: string | null;
    booking_status_label: string;
    customer_display_name: string | null;
    customer_short_name?: string | null;
    service_name: string | null;
    reason: string | null;
    accessible_label: string;
  };
}

export function formatShortCustomerName(fullName: string | null | undefined): string {
  if (!fullName || !fullName.trim()) return 'Cliente';
  const parts = fullName.trim().split(/\s+/);
  if (parts.length === 1) return parts[0];
  const firstName = parts[0];
  const lastInitial = parts[1][0]?.toUpperCase();
  return lastInitial ? `${firstName} ${lastInitial}.` : firstName;
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
    const customerShortName = formatShortCustomerName(ev.customer_display_name);
    const serviceText = ev.service_name || 'Servicio';
    const title = `[${statusLabel}] ${providerText}${customerText} - ${serviceText}`;
    const accessible_label = `Reserva ${statusLabel}: ${customerText} - ${serviceText}${
      ev.provider_name ? ` (Profesional: ${ev.provider_name})` : ''
    }`;

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
        backgroundColor = '#176b5b'; // Primary Brand Green
        borderColor = '#125548'; // Primary Brand Green Hover
        break;
    }

    return {
      id: ev.id,
      title,
      start: ev.starts_at,
      end: ev.ends_at,
      color: backgroundColor,
      backgroundColor,
      borderColor,
      extendedProps: {
        kind: 'booking',
        id: ev.id,
        provider_name: ev.provider_name || '',
        booking_status: ev.booking_status,
        booking_status_label: statusLabel,
        customer_display_name: ev.customer_display_name || null,
        customer_short_name: customerShortName,
        service_name: ev.service_name || null,
        reason: null,
        accessible_label,
      },
    };
  }

  // Time off event
  const providerText = ev.provider_name ? ` ${ev.provider_name}` : '';
  const reasonText = ev.reason ? ` — ${ev.reason}` : '';
  const title = `Bloqueo:${providerText}${reasonText}`;
  const accessible_label = `Bloqueo${ev.provider_name ? `: ${ev.provider_name}` : ''}${
    ev.reason ? ` (Motivo: ${ev.reason})` : ''
  }`;
  const backgroundColor = '#b33a3a'; // Danger Red
  const borderColor = '#992222';

  return {
    id: ev.id,
    title,
    start: ev.starts_at,
    end: ev.ends_at,
    color: backgroundColor,
    backgroundColor,
    borderColor,
    extendedProps: {
      kind: 'time_off',
      id: ev.id,
      provider_name: ev.provider_name || '',
      booking_status: null,
      booking_status_label: 'Bloqueo',
      customer_display_name: null,
      customer_short_name: null,
      service_name: null,
      reason: ev.reason || null,
      accessible_label,
    },
  };
}

export function mapCalendarEventsToFullCalendar(events: CalendarEventItem[]): FullCalendarEventItem[] {
  return events.map(mapCalendarEventToFullCalendar);
}
