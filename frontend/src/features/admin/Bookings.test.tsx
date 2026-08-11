import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BookingsListPage } from './BookingsListPage';
import { BookingDetailPage } from './BookingDetailPage';
import * as adminApi from '../../lib/api/admin';

vi.mock('../auth/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'admin1', display_name: 'Admin Test', email: 'admin@test.cl' },
    business: { name: 'Estudio Test', timezone: 'America/Santiago', locale: 'es-CL' },
    handleUnauthorized: vi.fn(),
  }),
}));

vi.mock('../../lib/api/admin', async () => {
  const actual = await vi.importActual<typeof import('../../lib/api/admin')>('../../lib/api/admin');
  return {
    ...actual,
    getAdminBookings: vi.fn(),
    getAdminBookingDetail: vi.fn(),
    updateAdminBookingStatus: vi.fn(),
    getAdminProviders: vi.fn(),
  };
});

const mockProviders: adminApi.AdminProviderListItem[] = [
  { id: 'p1', name: 'Camila Rojas', is_active: true },
  { id: 'p2', name: 'Diego Silva', is_active: false },
];

const mockBookingsList: adminApi.AdminBookingListItem[] = [
  {
    id: 'b1',
    starts_at: '2026-08-10T14:00:00-04:00',
    ends_at: '2026-08-10T14:30:00-04:00',
    customer_name: 'Juan Pérez',
    service_name_snapshot: 'Corte de Cabello',
    provider_name_snapshot: 'Camila Rojas',
    provider_id: 'p1',
    status: 'confirmed',
    source: 'public',
  },
];

const mockBookingDetail: adminApi.AdminBookingDetail = {
  id: 'b1',
  public_reference: 'REF_TEST_123',
  customer_name: 'Juan Pérez',
  customer_email: 'juan@perez.cl',
  customer_phone: '+56911111111',
  customer_notes: 'Nota del cliente',
  starts_at: '2026-08-10T14:00:00-04:00',
  ends_at: '2026-08-10T14:30:00-04:00',
  status: 'confirmed',
  source: 'public',
  service_id: 's1',
  provider_id: 'p1',
  service_name_snapshot: 'Corte de Cabello',
  provider_name_snapshot: 'Camila Rojas',
  duration_minutes_snapshot: 30,
  price_amount_snapshot: 15000,
  cancelled_at: null,
  completed_at: null,
  no_show_at: null,
  created_at: '2026-08-01T10:00:00Z',
  updated_at: '2026-08-01T10:00:00Z',
};

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
      mutations: { retry: false },
    },
  });

describe('BookingsListPage & BookingDetailPage Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(adminApi.getAdminProviders).mockResolvedValue(mockProviders);
    vi.mocked(adminApi.getAdminBookings).mockResolvedValue(mockBookingsList);
    vi.mocked(adminApi.getAdminBookingDetail).mockResolvedValue(mockBookingDetail);
  });

  it('renders bookings list and filters by status', async () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin/reservas']}>
          <Routes>
            <Route path="/admin/reservas" element={<BookingsListPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText('Gestión de Reservas')).toBeDefined();
    expect(await screen.findByText('Juan Pérez')).toBeDefined();
    expect(await screen.findByText('Confirmada')).toBeDefined();

    // Verify booking card is a semantic Link element pointing to /admin/reservas/b1
    const link = screen.getByRole('link', { name: /Juan Pérez/i });
    expect(link).toBeDefined();
    expect(link.getAttribute('href')).toBe('/admin/reservas/b1');

    const statusSelect = screen.getByLabelText('Estado');
    fireEvent.change(statusSelect, { target: { value: 'confirmed' } });

    await waitFor(() => {
      expect(adminApi.getAdminBookings).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'confirmed' })
      );
    });
  });


  it('renders booking detail page with customer PII', async () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin/reservas/b1']}>
          <Routes>
            <Route path="/admin/reservas/:bookingId" element={<BookingDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText('Reserva REF_TEST_123')).toBeDefined();
    expect(screen.getByText('juan@perez.cl')).toBeDefined();
    expect(screen.getByText('+56911111111')).toBeDefined();
    expect(screen.getByText('Nota del cliente')).toBeDefined();
    expect(screen.getByText('Marcar Completada')).toBeDefined();
  });

  it('triggers status change mutation when completing booking', async () => {
    vi.mocked(adminApi.updateAdminBookingStatus).mockResolvedValue({
      ...mockBookingDetail,
      status: 'completed',
      completed_at: '2026-08-10T14:30:00Z',
    });

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin/reservas/b1']}>
          <Routes>
            <Route path="/admin/reservas/:bookingId" element={<BookingDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText('Reserva REF_TEST_123')).toBeDefined();

    fireEvent.click(screen.getByText('Marcar Completada'));

    // Modal opens
    expect(screen.getByText('Confirmar Atención Completada')).toBeDefined();
    fireEvent.click(screen.getByText('Completar Atención'));

    await waitFor(() => {
      expect(adminApi.updateAdminBookingStatus).toHaveBeenCalledWith('b1', 'completed');
    });
  });
});
