import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AdminCalendarPage } from './AdminCalendarPage';
import { mapCalendarEventsToFullCalendar } from './adminCalendarUtils';
import { getAdminCalendarEvents, getAdminProviders, type CalendarEventsData } from '../../lib/api/admin';
import { ApiError } from '../../lib/api/client';
import { formatCivilDateInTimezone } from '../../lib/format/date';

// 1. Vitest top-level mock (fixes top-level hoist warning)
vi.mock('./AdminCalendar', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  AdminCalendar: ({ onDatesSet, onEventClick, events, timezone }: any) => {
    const fcEvents = mapCalendarEventsToFullCalendar(events || []);
    return (
      <div data-testid="mock-admin-calendar" data-timezone={timezone}>
        <button
          data-testid="simulate-dates-set"
          onClick={() => onDatesSet('2026-08-10', '2026-08-15')}
        >
          Set Dates
        </button>
        <button
          data-testid="simulate-range-1"
          onClick={() => onDatesSet('2026-08-01', '2026-08-07')}
        >
          Range 1
        </button>
        <button
          data-testid="simulate-range-2"
          onClick={() => onDatesSet('2026-08-08', '2026-08-14')}
        >
          Range 2
        </button>
        <div data-testid="events-container">
          {fcEvents.map((ev) => (
            <div
              key={ev.id}
              data-testid={`event-${ev.id}`}
              onClick={() => onEventClick(ev.extendedProps.kind, ev.id)}
            >
              {ev.title}
            </div>
          ))}
        </div>
      </div>
    );
  },
}));

// Mock API functions
vi.mock('../../lib/api/admin', () => ({
  getAdminCalendarEvents: vi.fn(),
  getAdminProviders: vi.fn(),
}));

const mockHandleUnauthorized = vi.fn();
let mockBusiness = {
  id: 'biz-1',
  name: 'Estudio Test',
  slug: 'estudio-test',
  timezone: 'America/Santiago',
  locale: 'es-CL',
  email: 'contacto@estudio.cl',
};

// Mock useAuth
vi.mock('../auth/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'admin-1', email: 'admin@estudio.cl', display_name: 'Admin' },
    business: mockBusiness,
    handleUnauthorized: mockHandleUnauthorized,
  }),
}));

const mockGetAdminCalendarEvents = vi.mocked(getAdminCalendarEvents);
const mockGetAdminProviders = vi.mocked(getAdminProviders);

const renderWithProviders = (ui: React.ReactElement, initialPath = '/admin/calendario') => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/admin/calendario" element={ui} />
          <Route path="/admin/reservas/:bookingId" element={<div data-testid="booking-detail-page">Booking Detail</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('AdminCalendarPage Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBusiness = {
      id: 'biz-1',
      name: 'Estudio Test',
      slug: 'estudio-test',
      timezone: 'America/Santiago',
      locale: 'es-CL',
      email: 'contacto@estudio.cl',
    };

    mockGetAdminProviders.mockResolvedValue([
      { id: 'provider-1', name: 'Dra. Valenzuela', email: 'v@test.cl', is_active: true },
      { id: 'provider-2', name: 'Dr. Martin', email: 'm@test.cl', is_active: false },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ] as any);
  });

  it('renders all 4 booking statuses and time_off with full textual representation (provider, customer, service, status)', async () => {
    mockGetAdminCalendarEvents.mockResolvedValue({
      timezone: 'America/Santiago',
      events: [
        {
          id: 'b-1',
          kind: 'booking',
          starts_at: '2026-08-10T10:00:00-04:00',
          ends_at: '2026-08-10T11:00:00-04:00',
          provider_id: 'provider-1',
          provider_name: 'Dra. Valenzuela',
          booking_status: 'confirmed',
          customer_display_name: 'Maria P.',
          service_name: 'Consulta General',
          reason: null,
        },
        {
          id: 'b-2',
          kind: 'booking',
          starts_at: '2026-08-11T10:00:00-04:00',
          ends_at: '2026-08-11T11:00:00-04:00',
          provider_id: 'provider-1',
          provider_name: 'Dra. Valenzuela',
          booking_status: 'completed',
          customer_display_name: 'Juan P.',
          service_name: 'Control Anual',
          reason: null,
        },
        {
          id: 'b-3',
          kind: 'booking',
          starts_at: '2026-08-12T10:00:00-04:00',
          ends_at: '2026-08-12T11:00:00-04:00',
          provider_id: 'provider-1',
          provider_name: 'Dra. Valenzuela',
          booking_status: 'no_show',
          customer_display_name: 'Carlos S.',
          service_name: 'Urgencia',
          reason: null,
        },
        {
          id: 'b-4',
          kind: 'booking',
          starts_at: '2026-08-13T10:00:00-04:00',
          ends_at: '2026-08-13T11:00:00-04:00',
          provider_id: 'provider-1',
          provider_name: 'Dra. Valenzuela',
          booking_status: 'cancelled',
          customer_display_name: 'Ana G.',
          service_name: 'Evaluación',
          reason: null,
        },
        {
          id: 't-1',
          kind: 'time_off',
          starts_at: '2026-08-14T09:00:00-04:00',
          ends_at: '2026-08-14T18:00:00-04:00',
          provider_id: 'provider-1',
          provider_name: 'Dra. Valenzuela',
          booking_status: null,
          customer_display_name: null,
          service_name: null,
          reason: 'Vacaciones',
        },
      ],
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    renderWithProviders(<AdminCalendarPage />);
    expect(screen.getByText('Calendario')).toBeDefined();

    fireEvent.click(screen.getByTestId('simulate-dates-set'));

    await waitFor(() => {
      expect(screen.getByTestId('event-b-1').textContent).toBe(
        '[Confirmada] Dra. Valenzuela — Maria P. - Consulta General'
      );
    });

    expect(screen.getByTestId('event-b-2').textContent).toBe(
      '[Completada] Dra. Valenzuela — Juan P. - Control Anual'
    );
    expect(screen.getByTestId('event-b-3').textContent).toBe(
      '[Inasistencia] Dra. Valenzuela — Carlos S. - Urgencia'
    );
    expect(screen.getByTestId('event-b-4').textContent).toBe(
      '[Cancelada] Dra. Valenzuela — Ana G. - Evaluación'
    );
    expect(screen.getByTestId('event-t-1').textContent).toBe(
      'Bloqueo: Dra. Valenzuela — Vacaciones'
    );
  });

  it('handles race conditions between consecutive date ranges and cancels earlier request with AbortSignal', async () => {
    let resolveRange1: (val: CalendarEventsData) => void;
    const range1Promise = new Promise<CalendarEventsData>((resolve) => {
      resolveRange1 = resolve;
    });

    let signal1: AbortSignal | undefined;

    mockGetAdminCalendarEvents.mockImplementation((start, _end, _provider, signal) => {
      if (start === '2026-08-01') {
        signal1 = signal;
        return range1Promise;
      }
      if (start === '2026-08-08') {
        return Promise.resolve({
          timezone: 'America/Santiago',
          events: [
            {
              id: 'event-range-2',
              kind: 'booking',
              starts_at: '2026-08-09T10:00:00-04:00',
              ends_at: '2026-08-09T11:00:00-04:00',
              provider_id: 'provider-1',
              provider_name: 'Dra. Valenzuela',
              booking_status: 'confirmed',
              customer_display_name: 'Pedro R.',
              service_name: 'Control Range 2',
              reason: null,
            },
          ],
        });
      }
      return Promise.reject(new Error('Unknown range'));
    });

    renderWithProviders(<AdminCalendarPage />);

    // 1. User views Range 1
    fireEvent.click(screen.getByTestId('simulate-range-1'));

    // 2. User quickly navigates to Range 2 before Range 1 finishes
    fireEvent.click(screen.getByTestId('simulate-range-2'));

    // Verify Range 2 data is rendered immediately
    await waitFor(() => {
      expect(screen.getByTestId('event-event-range-2')).toBeDefined();
    });

    // Verify Range 1 request was aborted by TanStack Query
    expect(signal1?.aborted).toBe(true);

    // 3. Range 1 resolves belatedly
    resolveRange1!({
      timezone: 'America/Santiago',
      events: [
        {
          id: 'event-stale-range-1',
          kind: 'booking',
          starts_at: '2026-08-02T10:00:00-04:00',
          ends_at: '2026-08-02T11:00:00-04:00',
          provider_id: 'provider-1',
          provider_name: 'Dra. Valenzuela',
          booking_status: 'confirmed',
          customer_display_name: 'Stale Customer',
          service_name: 'Stale Service',
          reason: null,
        },
      ],
    });

    // Verify that Range 1 data NEVER overrides active Range 2 data
    expect(screen.queryByTestId('event-stale-range-1')).toBeNull();
    expect(screen.getByTestId('event-event-range-2')).toBeDefined();
  });

  it('renders explicit empty state when calendar data contains no events', async () => {
    mockGetAdminCalendarEvents.mockResolvedValue({
      timezone: 'America/Santiago',
      events: [],
    });

    renderWithProviders(<AdminCalendarPage />);
    fireEvent.click(screen.getByTestId('simulate-dates-set'));

    await waitFor(() => {
      expect(
        screen.getByText('No hay eventos registrados para el período y profesional seleccionados.')
      ).toBeDefined();
    });
  });

  it('renders inline error state and allows retry with button', async () => {
    mockGetAdminCalendarEvents.mockRejectedValueOnce(
      new ApiError(500, { message: 'Error de conexión', code: 'server_error' })
    );

    renderWithProviders(<AdminCalendarPage />);
    fireEvent.click(screen.getByTestId('simulate-dates-set'));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined();
      expect(screen.getByText('Error de conexión')).toBeDefined();
    });

    // Setup successful response on retry
    mockGetAdminCalendarEvents.mockResolvedValueOnce({
      timezone: 'America/Santiago',
      events: [],
    });

    fireEvent.click(screen.getByText('Reintentar'));

    await waitFor(() => {
      expect(
        screen.getByText('No hay eventos registrados para el período y profesional seleccionados.')
      ).toBeDefined();
    });
  });

  it('calls handleUnauthorized on 401 error and does not show generic error', async () => {
    mockGetAdminCalendarEvents.mockRejectedValue(
      new ApiError(401, { message: 'Sesión expirada', code: 'unauthorized' })
    );

    renderWithProviders(<AdminCalendarPage />);
    fireEvent.click(screen.getByTestId('simulate-dates-set'));

    await waitFor(() => {
      expect(mockHandleUnauthorized).toHaveBeenCalled();
    });

    // Does not show generic error alert
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('filters by provider and passes provider_id to api call', async () => {
    mockGetAdminCalendarEvents.mockResolvedValue({
      timezone: 'America/Santiago',
      events: [],
    });

    renderWithProviders(<AdminCalendarPage />);

    await waitFor(() => {
      expect(screen.getByText('Dra. Valenzuela')).toBeDefined();
    });

    const select = screen.getByLabelText('Profesional');
    fireEvent.change(select, { target: { value: 'provider-1' } });
    fireEvent.click(screen.getByTestId('simulate-dates-set'));

    await waitFor(() => {
      expect(mockGetAdminCalendarEvents).toHaveBeenCalledWith(
        '2026-08-10',
        '2026-08-15',
        'provider-1',
        expect.any(AbortSignal)
      );
    });
  });

  it('navigates to booking detail on booking click, but does nothing on time_off click', async () => {
    mockGetAdminCalendarEvents.mockResolvedValue({
      timezone: 'America/Santiago',
      events: [
        {
          id: 'booking-uuid-123',
          kind: 'booking',
          starts_at: '2026-08-10T10:00:00-04:00',
          ends_at: '2026-08-10T11:00:00-04:00',
          provider_id: 'provider-1',
          provider_name: 'Dra. Valenzuela',
          booking_status: 'confirmed',
          customer_display_name: 'Maria P.',
          service_name: 'Consulta',
          reason: null,
        },
        {
          id: 'timeoff-uuid-456',
          kind: 'time_off',
          starts_at: '2026-08-12T10:00:00-04:00',
          ends_at: '2026-08-12T18:00:00-04:00',
          provider_id: 'provider-1',
          provider_name: 'Dra. Valenzuela',
          booking_status: null,
          customer_display_name: null,
          service_name: null,
          reason: 'Vacaciones',
        },
      ],
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    renderWithProviders(<AdminCalendarPage />);
    fireEvent.click(screen.getByTestId('simulate-dates-set'));

    await waitFor(() => {
      expect(screen.getByTestId('event-booking-uuid-123')).toBeDefined();
    });

    // Clicking time_off should NOT navigate
    fireEvent.click(screen.getByTestId('event-timeoff-uuid-456'));
    expect(screen.queryByTestId('booking-detail-page')).toBeNull();

    // Clicking booking navigates to booking detail page
    fireEvent.click(screen.getByTestId('event-booking-uuid-123'));
    expect(screen.getByTestId('booking-detail-page')).toBeDefined();
  });

  it('formats civil dates in business timezone correctly with formatToParts even when UTC and local fall on different days', () => {
    // 2026-08-11T02:00:00Z in UTC is 2026-08-10 22:00:00 in America/Santiago (UTC-4)
    const instant = new Date('2026-08-11T02:00:00Z');
    const formatted = formatCivilDateInTimezone(instant, 'America/Santiago');
    expect(formatted).toBe('2026-08-10');
  });
});
