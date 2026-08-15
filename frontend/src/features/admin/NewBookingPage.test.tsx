
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NewBookingPage } from './NewBookingPage';
import { AuthContext } from '../auth/useAuth';
import * as adminApi from '../../lib/api/admin';
import * as availabilityApi from '../../lib/api/availability';
import * as clientApi from '../../lib/api/client';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../../lib/api/admin', () => ({
  getAdminServices: vi.fn(),
  getAdminProviders: vi.fn(),
  createAdminBooking: vi.fn(),
}));

vi.mock('../../lib/api/availability', () => ({
  fetchPublicAvailability: vi.fn(),
}));

vi.mock('../../lib/api/client', () => ({
  ApiError: class ApiError extends Error {
    code: string;
    status: number;
    constructor(status: number, payload: { message: string, code: string }) {
      super(payload.message);
      this.status = status;
      this.code = payload.code;
    }
  },
}));

describe('NewBookingPage', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.resetAllMocks();
    mockNavigate.mockClear();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 0 } },
    });
  });

  const renderWithProviders = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AuthContext.Provider
            value={{
              user: null,
              business: { id: 'b1', name: 'Biz', timezone: 'America/Santiago' } as unknown as adminApi.BusinessInfo,
              isLoading: false,
              isAuthenticated: true,
              error: null,
              login: vi.fn(),
              logout: vi.fn(),
              refreshUser: vi.fn(),
              handleUnauthorized: vi.fn(),
            }}
          >
            <NewBookingPage />
          </AuthContext.Provider>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  it('renders step 1 and filters out inactive services', async () => {
    vi.mocked(adminApi.getAdminServices).mockResolvedValue([
      { id: 's1', name: 'Active Svc', is_active: true } as unknown as adminApi.AdminServiceDetail,
      { id: 's2', name: 'Inactive Svc', is_active: false } as unknown as adminApi.AdminServiceDetail,
    ]);

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByText('Active Svc')).toBeDefined();
    });
    expect(screen.queryByText('Inactive Svc')).toBeNull();
  });

  it('navigates through steps, ensures customer_phone is required, and handles slot_unavailable correctly', async () => {
    vi.mocked(adminApi.getAdminServices).mockResolvedValue([
      { id: 's1', name: 'Active Svc', is_active: true } as unknown as adminApi.AdminServiceDetail,
    ]);
    
    vi.mocked(adminApi.getAdminProviders).mockResolvedValue([
      { id: 'p1', name: 'Active Prov', is_active: true } as unknown as adminApi.AdminProviderListItem,
    ]);
    
    const mockAvailabilityData = {
      date: '2026-08-17',
      service_id: 's1',
      timezone: 'America/Santiago',
      slots: [
        { starts_at: '2026-08-17T10:00:00-04:00', ends_at: '2026-08-17T11:00:00-04:00' },
        { starts_at: '2026-08-17T10:30:00-04:00', ends_at: '2026-08-17T11:30:00-04:00' }
      ],
    };
    vi.mocked(availabilityApi.fetchPublicAvailability).mockResolvedValue(mockAvailabilityData);

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByText('Active Svc')).toBeDefined();
    });
    fireEvent.click(screen.getByText('Active Svc'));

    await waitFor(() => screen.getByText('Active Prov'));
    fireEvent.click(screen.getByText('Active Prov'));

    await waitFor(() => screen.getByText('Fecha y Hora'));
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-08-17' } });

    await waitFor(() => {
      expect(screen.getByText('10:00')).toBeDefined();
    });
    fireEvent.click(screen.getByText('10:00'));
    fireEvent.click(screen.getByText('Continuar'));

    await waitFor(() => screen.getByText('Datos del Cliente'));

    fireEvent.change(screen.getByLabelText(/Nombre completo/i), { target: { value: 'John' } });
    fireEvent.change(screen.getByLabelText(/Correo electrónico/i), { target: { value: 'john@example.com' } });
    
    const submitBtn = screen.getByText('Confirmar Reserva');
    expect(submitBtn.hasAttribute('disabled')).toBe(true);
    
    fireEvent.change(screen.getByLabelText(/Teléfono/i), { target: { value: '+56912345678' } });
    expect(submitBtn.hasAttribute('disabled')).toBe(false);

    vi.mocked(adminApi.createAdminBooking).mockRejectedValueOnce(
      new clientApi.ApiError(409, { message: 'Slot not available', code: 'slot_unavailable' })
    );

    fireEvent.click(submitBtn);

    await waitFor(() => screen.getByText('Fecha y Hora'));
    await screen.findByText(/El horario seleccionado ya no está disponible/i);
    expect(adminApi.createAdminBooking).toHaveBeenCalledTimes(1);
    

    vi.mocked(adminApi.createAdminBooking).mockResolvedValueOnce({ id: 'b123' } as unknown as adminApi.AdminBookingDetail);
    
    await waitFor(() => screen.getByText('10:30'));
    fireEvent.click(screen.getByText('10:30'));
    fireEvent.click(screen.getByText('Continuar'));

    await waitFor(() => screen.getByText('Datos del Cliente'));
    const submitBtn2 = screen.getByText('Confirmar Reserva');
    
    // Assert customer data was kept
    expect((screen.getByLabelText(/Nombre completo/i) as HTMLInputElement).value).toBe('John');
    expect((screen.getByLabelText(/Correo electrónico/i) as HTMLInputElement).value).toBe('john@example.com');
    expect((screen.getByLabelText(/Teléfono/i) as HTMLInputElement).value).toBe('+56912345678');
    
    expect(submitBtn2.hasAttribute('disabled')).toBe(false);
    
    fireEvent.click(submitBtn2);

    await waitFor(() => expect(adminApi.createAdminBooking).toHaveBeenCalledTimes(2));

    const payload1 = vi.mocked(adminApi.createAdminBooking).mock.calls[0][0];
    const payload2 = vi.mocked(adminApi.createAdminBooking).mock.calls[1][0];
    expect(payload2.starts_at).toBe('2026-08-17T10:30:00-04:00');
    expect(payload1.client_request_id).not.toBe(payload2.client_request_id);
  });

  it('keeps the idempotency key if idempotent_conflict happens without payload change', async () => {
    vi.mocked(adminApi.getAdminServices).mockResolvedValue([
      { id: 's1', name: 'Active Svc', is_active: true } as unknown as adminApi.AdminServiceDetail,
    ]);
    vi.mocked(adminApi.getAdminProviders).mockResolvedValue([
      { id: 'p1', name: 'Active Prov', is_active: true } as unknown as adminApi.AdminProviderListItem,
    ]);
    vi.mocked(availabilityApi.fetchPublicAvailability).mockResolvedValue({
      date: '2026-08-17',
      service_id: 's1',
      timezone: 'America/Santiago',
      slots: [{ starts_at: '2026-08-17T10:00:00-04:00', ends_at: '2026-08-17T11:00:00-04:00' }],
    });

    renderWithProviders();
    await waitFor(() => screen.getByText('Active Svc'));
    fireEvent.click(screen.getByText('Active Svc'));
    await waitFor(() => screen.getByText('Active Prov'));
    fireEvent.click(screen.getByText('Active Prov'));
    await waitFor(() => screen.getByText('Fecha y Hora'));
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-08-17' } });
    await waitFor(() => screen.getByText('10:00'));
    fireEvent.click(screen.getByText('10:00'));
    fireEvent.click(screen.getByText('Continuar'));
    await waitFor(() => screen.getByText('Datos del Cliente'));

    fireEvent.change(screen.getByLabelText(/Nombre completo/i), { target: { value: 'John' } });
    fireEvent.change(screen.getByLabelText(/Correo electrónico/i), { target: { value: 'john@example.com' } });
    fireEvent.change(screen.getByLabelText(/Teléfono/i), { target: { value: '123456789' } });

    vi.mocked(adminApi.createAdminBooking).mockRejectedValueOnce(
      new clientApi.ApiError(409, { message: 'Conflict', code: 'idempotency_conflict' })
    );
    
    const submitBtn = screen.getByText('Confirmar Reserva');
    fireEvent.click(submitBtn);

    await screen.findByText(/Conflict/i);

    const payload1 = vi.mocked(adminApi.createAdminBooking).mock.calls[0][0];

    vi.mocked(adminApi.createAdminBooking).mockRejectedValueOnce(
      new clientApi.ApiError(409, { message: 'Conflict again', code: 'idempotency_conflict' })
    );
    fireEvent.click(submitBtn);

    await waitFor(() => expect(adminApi.createAdminBooking).toHaveBeenCalledTimes(2));

    const payload2 = vi.mocked(adminApi.createAdminBooking).mock.calls[1][0];
    
    expect(payload1.client_request_id).toBe(payload2.client_request_id);

    // change semantic data -> new UUID
    fireEvent.change(screen.getByLabelText(/Nombre completo/i), { target: { value: 'Jane' } });
    
    vi.mocked(adminApi.createAdminBooking).mockResolvedValueOnce({ id: 'b123' } as unknown as adminApi.AdminBookingDetail);
    
    fireEvent.click(submitBtn);
    await waitFor(() => expect(adminApi.createAdminBooking).toHaveBeenCalledTimes(3));
    const payload3 = vi.mocked(adminApi.createAdminBooking).mock.calls[2][0];
    expect(payload3.client_request_id).not.toBe(payload1.client_request_id);
  });

  it('handles availability error and retry', async () => {
    vi.mocked(adminApi.getAdminServices).mockResolvedValue([
      { id: 's1', name: 'Active Svc', is_active: true } as unknown as adminApi.AdminServiceDetail,
    ]);
    vi.mocked(adminApi.getAdminProviders).mockResolvedValue([
      { id: 'p1', name: 'Active Prov', is_active: true } as unknown as adminApi.AdminProviderListItem,
    ]);
    vi.mocked(availabilityApi.fetchPublicAvailability).mockRejectedValueOnce(new Error('Network error'));
    
    renderWithProviders();
    await waitFor(() => screen.getByText('Active Svc'));
    fireEvent.click(screen.getByText('Active Svc'));
    await waitFor(() => screen.getByText('Active Prov'));
    fireEvent.click(screen.getByText('Active Prov'));
    await waitFor(() => screen.getByText('Fecha y Hora'));
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-08-17' } });

    await waitFor(() => {
      expect(screen.getByText('Error al cargar los horarios disponibles.')).toBeDefined();
    });

    vi.mocked(availabilityApi.fetchPublicAvailability).mockResolvedValueOnce({
      date: '2026-08-17',
      service_id: 's1',
      timezone: 'America/Santiago',
      slots: [{ starts_at: '2026-08-17T10:00:00-04:00', ends_at: '2026-08-17T11:00:00-04:00' }],
    });

    fireEvent.click(screen.getByText('Reintentar'));

    await waitFor(() => {
      expect(screen.getByText('10:00')).toBeDefined();
    });
  });

  it('invalidates queries and navigates after success', async () => {
    vi.mocked(adminApi.getAdminServices).mockResolvedValue([
      { id: 's1', name: 'Active Svc', is_active: true } as unknown as adminApi.AdminServiceDetail,
    ]);
    vi.mocked(adminApi.getAdminProviders).mockResolvedValue([
      { id: 'p1', name: 'Active Prov', is_active: true } as unknown as adminApi.AdminProviderListItem,
    ]);
    
    // Simular un slot donde el UTC y el local caen en distinto dia
    // 21:00 CLT es 01:00 UTC del dia siguiente.
    vi.mocked(availabilityApi.fetchPublicAvailability).mockResolvedValue({
      date: '2026-08-17',
      service_id: 's1',
      timezone: 'America/Santiago',
      slots: [{ starts_at: '2026-08-17T21:00:00-04:00', ends_at: '2026-08-17T22:00:00-04:00' }],
    });

    renderWithProviders();
    await waitFor(() => screen.getByText('Active Svc'));
    fireEvent.click(screen.getByText('Active Svc'));
    await waitFor(() => screen.getByText('Active Prov'));
    fireEvent.click(screen.getByText('Active Prov'));
    await waitFor(() => screen.getByText('Fecha y Hora'));
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-08-17' } });

    await waitFor(() => {
      expect(screen.getByText('21:00')).toBeDefined();
    });
    fireEvent.click(screen.getByText('21:00'));
    fireEvent.click(screen.getByText('Continuar'));

    await waitFor(() => screen.getByText('Datos del Cliente'));
    fireEvent.change(screen.getByLabelText(/Nombre completo/i), { target: { value: 'John' } });
    fireEvent.change(screen.getByLabelText(/Correo electrónico/i), { target: { value: 'john@example.com' } });
    fireEvent.change(screen.getByLabelText(/Teléfono/i), { target: { value: '+56912345678' } });

    vi.mocked(adminApi.createAdminBooking).mockResolvedValue({ id: 'final-id' } as unknown as adminApi.AdminBookingDetail);
    
    // Espiar invalidaciones
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    fireEvent.click(screen.getByText('Confirmar Reserva'));

    await waitFor(() => expect(adminApi.createAdminBooking).toHaveBeenCalledTimes(1));

    await waitFor(() => {
      // Verifiquemos si llamo a invalidateQueries para cada cosa
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ['admin', 'bookings'] }));
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ['admin', 'calendarEvents'] }));
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ['admin', 'dashboard'] }));
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ['public-availability'] }));
      expect(mockNavigate).toHaveBeenCalledWith('/admin/reservas/final-id', { replace: true });
    });
  });
});
