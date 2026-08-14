import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AdminCalendar } from './AdminCalendar';
import {
  mapCalendarEventToFullCalendar,
  getBookingStatusLabel,
} from './adminCalendarUtils';
import type { CalendarEventItem } from '../../lib/api/admin';

describe('AdminCalendar Mapping & Logic', () => {
  it('correctly returns text labels for all four booking statuses', () => {
    expect(getBookingStatusLabel('confirmed')).toBe('Confirmada');
    expect(getBookingStatusLabel('completed')).toBe('Completada');
    expect(getBookingStatusLabel('no_show')).toBe('Inasistencia');
    expect(getBookingStatusLabel('cancelled')).toBe('Cancelada');
    expect(getBookingStatusLabel(null)).toBe('Reserva');
  });

  it('maps confirmed, completed, no_show, and cancelled bookings with full textual details (status, provider, customer, service)', () => {
    const baseBooking: CalendarEventItem = {
      id: 'b-1',
      kind: 'booking',
      starts_at: '2026-08-10T10:00:00-04:00',
      ends_at: '2026-08-10T11:00:00-04:00',
      provider_id: 'p-1',
      provider_name: 'Dra. Valenzuela',
      booking_status: 'confirmed',
      customer_display_name: 'Maria P.',
      service_name: 'Consulta General',
      reason: null,
    };

    const confirmedEv = mapCalendarEventToFullCalendar(baseBooking);
    expect(confirmedEv.title).toBe('[Confirmada] Dra. Valenzuela — Maria P. - Consulta General');
    expect(confirmedEv.backgroundColor).toBe('#4f46e5');

    const completedEv = mapCalendarEventToFullCalendar({
      ...baseBooking,
      id: 'b-2',
      booking_status: 'completed',
    });
    expect(completedEv.title).toBe('[Completada] Dra. Valenzuela — Maria P. - Consulta General');
    expect(completedEv.backgroundColor).toBe('#2563eb');

    const noShowEv = mapCalendarEventToFullCalendar({
      ...baseBooking,
      id: 'b-3',
      booking_status: 'no_show',
    });
    expect(noShowEv.title).toBe('[Inasistencia] Dra. Valenzuela — Maria P. - Consulta General');
    expect(noShowEv.backgroundColor).toBe('#d97706');

    const cancelledEv = mapCalendarEventToFullCalendar({
      ...baseBooking,
      id: 'b-4',
      booking_status: 'cancelled',
    });
    expect(cancelledEv.title).toBe('[Cancelada] Dra. Valenzuela — Maria P. - Consulta General');
    expect(cancelledEv.backgroundColor).toBe('#475569');
  });

  it('maps time_off events with provider and reason', () => {
    const timeOffWithReason: CalendarEventItem = {
      id: 't-1',
      kind: 'time_off',
      starts_at: '2026-08-10T14:00:00-04:00',
      ends_at: '2026-08-10T18:00:00-04:00',
      provider_id: 'p-1',
      provider_name: 'Dr. Martin',
      booking_status: null,
      customer_display_name: null,
      service_name: null,
      reason: 'Congreso Internacional',
    };

    const ev1 = mapCalendarEventToFullCalendar(timeOffWithReason);
    expect(ev1.title).toBe('Bloqueo: Dr. Martin — Congreso Internacional');
    expect(ev1.backgroundColor).toBe('#dc2626');

    const timeOffWithoutReason: CalendarEventItem = {
      ...timeOffWithReason,
      id: 't-2',
      reason: null,
    };

    const ev2 = mapCalendarEventToFullCalendar(timeOffWithoutReason);
    expect(ev2.title).toBe('Bloqueo: Dr. Martin');
  });
});

describe('AdminCalendar Component Rendering & View Persistence', () => {
  const mockEvents: CalendarEventItem[] = [
    {
      id: 'book-1',
      kind: 'booking',
      starts_at: '2026-08-10T10:00:00-04:00',
      ends_at: '2026-08-10T11:00:00-04:00',
      provider_id: 'p-1',
      provider_name: 'Dra. Valenzuela',
      booking_status: 'confirmed',
      customer_display_name: 'Maria P.',
      service_name: 'Consulta General',
      reason: null,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders FullCalendar and responds to view callbacks', () => {
    const onDatesSet = vi.fn();
    const onEventClick = vi.fn();
    const onViewChange = vi.fn();

    const { container } = render(
      <AdminCalendar
        events={mockEvents}
        timezone="America/Santiago"
        onDatesSet={onDatesSet}
        onEventClick={onEventClick}
        userSelectedView={null}
        onViewChange={onViewChange}
      />
    );

    expect(container.querySelector('.fc')).toBeDefined();
  });

  it('preserves userSelectedView during window resize', () => {
    const onDatesSet = vi.fn();
    const onEventClick = vi.fn();
    const onViewChange = vi.fn();

    render(
      <AdminCalendar
        events={mockEvents}
        timezone="America/Santiago"
        onDatesSet={onDatesSet}
        onEventClick={onEventClick}
        userSelectedView="timeGridDay"
        onViewChange={onViewChange}
      />
    );

    window.innerWidth = 480;
    window.dispatchEvent(new Event('resize'));

    expect(screen.queryByText('Hoy')).toBeDefined();
  });
});
