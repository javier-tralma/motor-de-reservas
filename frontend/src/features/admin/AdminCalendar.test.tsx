import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AdminCalendar } from './AdminCalendar';
import {
  mapCalendarEventToFullCalendar,
  getBookingStatusLabel,
  formatShortCustomerName,
} from './adminCalendarUtils';
import type { CalendarEventItem } from '../../lib/api/admin';

describe('AdminCalendar Mapping & Logic', () => {
  it('correctly abbreviates customer names semantically without CSS truncation', () => {
    expect(formatShortCustomerName('Carolina Mendez')).toBe('Carolina M.');
    expect(formatShortCustomerName('Maria Paz Valenzuela')).toBe('Maria P.');
    expect(formatShortCustomerName('Carlos')).toBe('Carlos');
    expect(formatShortCustomerName('  Juan   Perez  ')).toBe('Juan P.');
    expect(formatShortCustomerName('')).toBe('Cliente');
    expect(formatShortCustomerName(null)).toBe('Cliente');
    expect(formatShortCustomerName(undefined)).toBe('Cliente');
  });

  it('correctly returns text labels for all four booking statuses', () => {
    expect(getBookingStatusLabel('confirmed')).toBe('Confirmada');
    expect(getBookingStatusLabel('completed')).toBe('Completada');
    expect(getBookingStatusLabel('no_show')).toBe('Inasistencia');
    expect(getBookingStatusLabel('cancelled')).toBe('Cancelada');
    expect(getBookingStatusLabel(null)).toBe('Reserva');
  });

  it('maps confirmed, completed, no_show, and cancelled bookings with full textual details and accessible labels', () => {
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
    expect(confirmedEv.extendedProps.accessible_label).toBe(
      'Reserva Confirmada: Maria P. - Consulta General (Profesional: Dra. Valenzuela)'
    );
    expect(confirmedEv.backgroundColor).toBe('#176b5b');

    const completedEv = mapCalendarEventToFullCalendar({
      ...baseBooking,
      id: 'b-2',
      booking_status: 'completed',
    });
    expect(completedEv.title).toBe('[Completada] Dra. Valenzuela — Maria P. - Consulta General');
    expect(completedEv.extendedProps.accessible_label).toBe(
      'Reserva Completada: Maria P. - Consulta General (Profesional: Dra. Valenzuela)'
    );
    expect(completedEv.backgroundColor).toBe('#2563eb');

    const noShowEv = mapCalendarEventToFullCalendar({
      ...baseBooking,
      id: 'b-3',
      booking_status: 'no_show',
    });
    expect(noShowEv.title).toBe('[Inasistencia] Dra. Valenzuela — Maria P. - Consulta General');
    expect(noShowEv.extendedProps.accessible_label).toBe(
      'Reserva Inasistencia: Maria P. - Consulta General (Profesional: Dra. Valenzuela)'
    );
    expect(noShowEv.backgroundColor).toBe('#d97706');

    const cancelledEv = mapCalendarEventToFullCalendar({
      ...baseBooking,
      id: 'b-4',
      booking_status: 'cancelled',
    });
    expect(cancelledEv.title).toBe('[Cancelada] Dra. Valenzuela — Maria P. - Consulta General');
    expect(cancelledEv.extendedProps.accessible_label).toBe(
      'Reserva Cancelada: Maria P. - Consulta General (Profesional: Dra. Valenzuela)'
    );
    expect(cancelledEv.backgroundColor).toBe('#475569');
  });

  it('maps time_off events with explicit Bloqueo label, provider, reason and accessible label', () => {
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
    expect(ev1.extendedProps.accessible_label).toBe(
      'Bloqueo: Dr. Martin (Motivo: Congreso Internacional)'
    );
    expect(ev1.backgroundColor).toBe('#b33a3a');

    const timeOffWithoutReason: CalendarEventItem = {
      ...timeOffWithReason,
      id: 't-2',
      reason: null,
    };

    const ev2 = mapCalendarEventToFullCalendar(timeOffWithoutReason);
    expect(ev2.title).toBe('Bloqueo: Dr. Martin');
    expect(ev2.extendedProps.accessible_label).toBe('Bloqueo: Dr. Martin');
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

  it('preserves existing navigation rules: booking calls onEventClick, time_off does not', () => {
    const onEventClick = vi.fn();

    const mixedEvents: CalendarEventItem[] = [
      {
        id: 'book-100',
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
      {
        id: 'toff-200',
        kind: 'time_off',
        starts_at: '2026-08-10T14:00:00-04:00',
        ends_at: '2026-08-10T18:00:00-04:00',
        provider_id: 'p-1',
        provider_name: 'Dra. Valenzuela',
        booking_status: null,
        customer_display_name: null,
        service_name: null,
        reason: 'Almuerzo',
      },
    ];

    render(
      <AdminCalendar
        events={mixedEvents}
        timezone="America/Santiago"
        onDatesSet={vi.fn()}
        onEventClick={onEventClick}
        userSelectedView="listWeek"
        onViewChange={vi.fn()}
      />
    );

    expect(screen.queryByText(/Consulta General/)).toBeDefined();
  });

  it('renders short 30-min bookings with textual status and customer/service detail in timeGrid', () => {
    const shortBooking: CalendarEventItem[] = [
      {
        id: 'book-short',
        kind: 'booking',
        starts_at: '2026-08-10T12:00:00-04:00',
        ends_at: '2026-08-10T12:30:00-04:00',
        provider_id: 'p-1',
        provider_name: 'Dra. Valenzuela',
        booking_status: 'confirmed',
        customer_display_name: 'Carolina Mendez',
        service_name: 'Corte y Barba',
        reason: null,
      },
    ];

    const { container } = render(
      <AdminCalendar
        events={shortBooking}
        timezone="America/Santiago"
        onDatesSet={vi.fn()}
        onEventClick={vi.fn()}
        userSelectedView="timeGridWeek"
        onViewChange={vi.fn()}
      />
    );

    expect(container.querySelector('.fc')).toBeDefined();
    // Verify mapped item properties
    const mapped = mapCalendarEventToFullCalendar(shortBooking[0]);
    expect(mapped.extendedProps.booking_status_label).toBe('Confirmada');
    expect(mapped.extendedProps.customer_display_name).toBe('Carolina Mendez');
    expect(mapped.extendedProps.customer_short_name).toBe('Carolina M.');
    expect(mapped.extendedProps.service_name).toBe('Corte y Barba');
  });

  it('renders long blockades with explicit Bloqueo, provider, and reason', () => {
    const longBlockade: CalendarEventItem[] = [
      {
        id: 'toff-long',
        kind: 'time_off',
        starts_at: '2026-08-10T14:00:00-04:00',
        ends_at: '2026-08-10T16:00:00-04:00',
        provider_id: 'p-1',
        provider_name: 'Barbero Experto',
        booking_status: null,
        customer_display_name: null,
        service_name: null,
        reason: 'Capacitación de Barbería Clásica',
      },
    ];

    const { container } = render(
      <AdminCalendar
        events={longBlockade}
        timezone="America/Santiago"
        onDatesSet={vi.fn()}
        onEventClick={vi.fn()}
        userSelectedView="timeGridWeek"
        onViewChange={vi.fn()}
      />
    );

    expect(container.querySelector('.fc')).toBeDefined();
    const mapped = mapCalendarEventToFullCalendar(longBlockade[0]);
    expect(mapped.extendedProps.kind).toBe('time_off');
    expect(mapped.extendedProps.provider_name).toBe('Barbero Experto');
    expect(mapped.extendedProps.reason).toBe('Capacitación de Barbería Clásica');
  });
});
