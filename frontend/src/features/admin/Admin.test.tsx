import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '../auth/AuthContext';
import { ProtectedRoute } from '../auth/ProtectedRoute';
import { AdminLayout } from './AdminLayout';
import { DashboardPage } from './DashboardPage';
import * as adminApi from '../../lib/api/admin';
import { ApiError } from '../../lib/api/client';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, gcTime: 0 },
    },
  });


const mockMeData = {
  admin: { id: 'admin-1', display_name: 'Javier', email: 'admin@test.cl' },
  business: { name: 'Estudio Nómada', timezone: 'America/Santiago', locale: 'es-CL' },
};

const mockDashboardData: adminApi.DashboardData = {
  date: '2026-08-10',
  timezone: 'America/Santiago',
  summary: {
    total: 3,
    confirmed_remaining: 1,
    completed: 1,
    cancelled: 1,
    no_show: 0,
  },
  next_booking: {
    id: 'b-2',
    starts_at: '2026-08-10T15:00:00-04:00',
    ends_at: '2026-08-10T15:30:00-04:00',
    customer_name: 'Maria Gomez',
    service_name: 'Corte de Cabello',
    provider_name: 'Camila Rojas',
    status: 'confirmed',
  },
  agenda: [
    {
      id: 'b-1',
      starts_at: '2026-08-10T10:00:00-04:00',
      ends_at: '2026-08-10T10:30:00-04:00',
      customer_name: 'Juan Pérez',
      service_name: 'Corte de Cabello',
      provider_name: 'Camila Rojas',
      status: 'completed',
    },
    {
      id: 'b-2',
      starts_at: '2026-08-10T15:00:00-04:00',
      ends_at: '2026-08-10T15:30:00-04:00',
      customer_name: 'Maria Gomez',
      service_name: 'Corte de Cabello',
      provider_name: 'Camila Rojas',
      status: 'confirmed',
    },
    {
      id: 'b-3',
      starts_at: '2026-08-10T16:00:00-04:00',
      ends_at: '2026-08-10T16:30:00-04:00',
      customer_name: 'Pedro Soto',
      service_name: 'Corte de Cabello',
      provider_name: 'Camila Rojas',
      status: 'cancelled',
    },
  ],
};

describe('Admin Layout & Dashboard', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(adminApi, 'getAdminMe').mockResolvedValue(mockMeData);
  });

  it('renders dashboard with stats, next booking, and agenda', async () => {
    vi.spyOn(adminApi, 'getAdminDashboard').mockResolvedValue(mockDashboardData);

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin']}>
          <AuthProvider>
            <Routes>
              <Route element={<ProtectedRoute />}>
                <Route element={<AdminLayout />}>
                  <Route path="/admin" element={<DashboardPage />} />
                </Route>
              </Route>
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText(/Agenda del día/i)).toBeDefined();
    expect(screen.getByText('Juan Pérez')).toBeDefined();
    expect(screen.getAllByText('Maria Gomez').length).toBeGreaterThan(0);
    expect(screen.getByText('Pedro Soto')).toBeDefined();



    // Check status badges
    expect(screen.getByText('Completada')).toBeDefined();
    expect(screen.getByText('Confirmada')).toBeDefined();
    expect(screen.getByText('Cancelada')).toBeDefined();
  });

  it('renders empty state when agenda is empty', async () => {
    vi.spyOn(adminApi, 'getAdminDashboard').mockResolvedValue({
      date: '2026-08-10',
      timezone: 'America/Santiago',
      summary: { total: 0, confirmed_remaining: 0, completed: 0, cancelled: 0, no_show: 0 },
      next_booking: null,
      agenda: [],
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin']}>
          <AuthProvider>
            <Routes>
              <Route element={<ProtectedRoute />}>
                <Route element={<AdminLayout />}>
                  <Route path="/admin" element={<DashboardPage />} />
                </Route>
              </Route>
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('No hay reservas programadas para hoy')).toBeDefined();
    });
  });

  it('handles dashboard error and allows retry', async () => {
    vi.spyOn(adminApi, 'getAdminDashboard')
      .mockRejectedValueOnce(new ApiError(500, { code: 'server_error', message: 'Error de servidor' }))
      .mockResolvedValueOnce(mockDashboardData);


    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin']}>
          <AuthProvider>
            <Routes>
              <Route element={<ProtectedRoute />}>
                <Route element={<AdminLayout />}>
                  <Route path="/admin" element={<DashboardPage />} />
                </Route>
              </Route>
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Error al cargar la agenda')).toBeDefined();
    });

    fireEvent.click(screen.getByRole('button', { name: /Reintentar/i }));

    await waitFor(() => {
      expect(screen.getByText('Juan Pérez')).toBeDefined();
    });
  });

  it('executes logout from layout and redirects to login', async () => {
    vi.spyOn(adminApi, 'getAdminDashboard').mockResolvedValue(mockDashboardData);
    const logoutSpy = vi.spyOn(adminApi, 'logoutAdmin').mockResolvedValue();

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin']}>
          <AuthProvider>
            <Routes>
              <Route path="/admin/login" element={<div>Página de Login</div>} />
              <Route element={<ProtectedRoute />}>
                <Route element={<AdminLayout />}>
                  <Route path="/admin" element={<DashboardPage />} />
                </Route>
              </Route>
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Agenda del día/i)).toBeDefined();
    });

    const logoutBtn = screen.getByRole('button', { name: /Cerrar sesión/i });
    fireEvent.click(logoutBtn);

    await waitFor(() => {
      expect(logoutSpy).toHaveBeenCalledTimes(1);
      expect(screen.getByText('Página de Login')).toBeDefined();
    });
  });

  it('handles logout network error without redirecting and shows error message', async () => {
    vi.spyOn(adminApi, 'getAdminDashboard').mockResolvedValue(mockDashboardData);
    const logoutSpy = vi.spyOn(adminApi, 'logoutAdmin').mockRejectedValue(new Error('Network Error'));

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin']}>
          <AuthProvider>
            <Routes>
              <Route path="/admin/login" element={<div>Página de Login</div>} />
              <Route element={<ProtectedRoute />}>
                <Route element={<AdminLayout />}>
                  <Route path="/admin" element={<DashboardPage />} />
                </Route>
              </Route>
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Agenda del día/i)).toBeDefined();
    });

    const logoutBtn = screen.getByRole('button', { name: /Cerrar sesión/i });
    fireEvent.click(logoutBtn);

    await waitFor(() => {
      expect(logoutSpy).toHaveBeenCalledTimes(1);
      expect(screen.getByText('Error al cerrar sesión. Intenta nuevamente.')).toBeDefined();
    });
    // Ensure we are still on the dashboard
    expect(screen.queryByText('Página de Login')).toBeNull();
  });

  it('displays greeting based on business timezone, not local browser timezone', async () => {

    // We mock a business in 'Asia/Tokyo' (UTC+9)
    // If we pretend our server/browser is in UTC, and it's 14:00 UTC
    // In Tokyo it would be 23:00 (Buenas noches)
    vi.spyOn(adminApi, 'getAdminMe').mockResolvedValue({
      admin: { id: 'admin-1', display_name: 'Yuki', email: 'yuki@test.jp' },
      business: { name: 'Tokyo Studio', timezone: 'Asia/Tokyo', locale: 'ja-JP' },
    });
    vi.spyOn(adminApi, 'getAdminDashboard').mockResolvedValue({
      ...mockDashboardData,
      timezone: 'Asia/Tokyo',
    });

    const mockDate = new Date('2026-08-10T14:00:00Z'); // 14:00 UTC -> 23:00 Tokyo
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(mockDate);

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin']}>
          <AuthProvider>
            <Routes>
              <Route element={<ProtectedRoute />}>
                <Route element={<AdminLayout />}>
                  <Route path="/admin" element={<DashboardPage />} />
                </Route>
              </Route>
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      // 23:00 is "Buenas noches"
      expect(screen.getByText(/Buenas noches, Yuki\./i)).toBeDefined();
    });

    vi.useRealTimers();
  });
});
