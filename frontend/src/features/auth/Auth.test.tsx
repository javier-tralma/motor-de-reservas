import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './AuthContext';
import { ProtectedRoute } from './ProtectedRoute';
import { LoginPage } from './LoginPage';
import * as adminApi from '../../lib/api/admin';
import { ApiError } from '../../lib/api/client';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

describe('Admin Authentication & Guards', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  it('redirects anonymous visitor from /admin to /admin/login', async () => {
    vi.spyOn(adminApi, 'getAdminMe').mockRejectedValue(
      new ApiError(401, { code: 'session_required', message: 'Se requiere autenticación' })
    );

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin']}>
          <AuthProvider>
            <Routes>
              <Route path="/admin/login" element={<div>Página de Login</div>} />
              <Route element={<ProtectedRoute />}>
                <Route path="/admin" element={<div>Dashboard Protegido</div>} />
              </Route>
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Página de Login')).toBeDefined();
    });

    expect(screen.queryByText('Dashboard Protegido')).toBeNull();
  });

  it('allows authenticated user into /admin and prevents loop', async () => {
    vi.spyOn(adminApi, 'getAdminMe').mockResolvedValue({
      admin: { id: 'admin-1', display_name: 'Javier', email: 'admin@test.cl' },
      business: { name: 'Estudio Nómada', timezone: 'America/Santiago', locale: 'es-CL' },
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin']}>
          <AuthProvider>
            <Routes>
              <Route path="/admin/login" element={<div>Página de Login</div>} />
              <Route element={<ProtectedRoute />}>
                <Route path="/admin" element={<div>Dashboard Protegido</div>} />
              </Route>
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Dashboard Protegido')).toBeDefined();
    });

    // Ensure nothing stored in Web Storage
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it('handles login form submission and displays generic invalid_credentials error', async () => {
    vi.spyOn(adminApi, 'getAdminMe').mockRejectedValue(
      new ApiError(401, { code: 'session_required', message: 'Unauthorized' })
    );
    vi.spyOn(adminApi, 'loginAdmin').mockRejectedValue(
      new ApiError(401, { code: 'invalid_credentials', message: 'Credenciales inválidas' })
    );

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin/login']}>
          <AuthProvider>
            <Routes>
              <Route path="/admin/login" element={<LoginPage />} />
              <Route path="/admin" element={<div>Dashboard Protegido</div>} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByLabelText(/Correo electrónico/i)).toBeDefined();
    });

    fireEvent.change(screen.getByLabelText(/Correo electrónico/i), {
      target: { value: 'admin@test.cl' },
    });
    fireEvent.change(screen.getByLabelText(/Contraseña/i), {
      target: { value: 'WrongPass' },
    });

    fireEvent.click(screen.getByRole('button', { name: /Iniciar sesión/i }));

    await waitFor(() => {
      expect(screen.getByText(/Credenciales inválidas/i)).toBeDefined();
    });
  });

  it('prevents double submit on login form', async () => {
    vi.spyOn(adminApi, 'getAdminMe').mockRejectedValue(
      new ApiError(401, { code: 'session_required', message: 'Unauthorized' })
    );

    let resolveLogin: (val: adminApi.AuthData) => void;
    const loginPromise = new Promise<adminApi.AuthData>((resolve) => {
      resolveLogin = resolve;
    });

    const loginSpy = vi
      .spyOn(adminApi, 'loginAdmin')
      .mockImplementation(() => loginPromise);


    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin/login']}>
          <AuthProvider>
            <Routes>
              <Route path="/admin/login" element={<LoginPage />} />
              <Route path="/admin" element={<div>Dashboard Protegido</div>} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByLabelText(/Correo electrónico/i)).toBeDefined();
    });

    fireEvent.change(screen.getByLabelText(/Correo electrónico/i), {
      target: { value: 'admin@test.cl' },
    });
    fireEvent.change(screen.getByLabelText(/Contraseña/i), {
      target: { value: 'Password123!' },
    });

    const button = screen.getByRole('button', { name: /Iniciar sesión/i });
    fireEvent.click(button);
    fireEvent.click(button); // Second click during submission

    await waitFor(() => {
      expect(loginSpy).toHaveBeenCalledTimes(1);
    });

    resolveLogin!({
      admin: { id: 'admin-1', display_name: 'Javier', email: 'admin@test.cl' },
      business: { name: 'Estudio Nómada', timezone: 'America/Santiago', locale: 'es-CL' },
    });


    await waitFor(() => {
      expect(screen.getByText('Dashboard Protegido')).toBeDefined();
    });
  });

  it('shows error state and retry button on /me 500 error instead of redirecting', async () => {
    vi.spyOn(adminApi, 'getAdminMe').mockRejectedValue(
      new ApiError(500, { code: 'server_error', message: 'Error interno' })
    );

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin']}>
          <AuthProvider>
            <Routes>
              <Route path="/admin/login" element={<div>Página de Login</div>} />
              <Route element={<ProtectedRoute />}>
                <Route path="/admin" element={<div>Dashboard Protegido</div>} />
              </Route>
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Error interno')).toBeDefined();
      expect(screen.getByRole('button', { name: /Reintentar/i })).toBeDefined();
    });

    expect(screen.queryByText('Página de Login')).toBeNull();
    expect(screen.queryByText('Dashboard Protegido')).toBeNull();
  });

  it('shows error state and handles successful retry on network error', async () => {
    const getAdminMeSpy = vi.spyOn(adminApi, 'getAdminMe');
    getAdminMeSpy.mockRejectedValueOnce(new Error('Network Error'));

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/admin']}>
          <AuthProvider>
            <Routes>
              <Route path="/admin/login" element={<div>Página de Login</div>} />
              <Route element={<ProtectedRoute />}>
                <Route path="/admin" element={<div>Dashboard Protegido</div>} />
              </Route>
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Network Error')).toBeDefined();
      expect(screen.getByRole('button', { name: /Reintentar/i })).toBeDefined();
    });

    // Now mock success for retry
    getAdminMeSpy.mockResolvedValueOnce({
      admin: { id: 'admin-1', display_name: 'Javier', email: 'admin@test.cl' },
      business: { name: 'Estudio Nómada', timezone: 'America/Santiago', locale: 'es-CL' },
    });

    fireEvent.click(screen.getByRole('button', { name: /Reintentar/i }));

    await waitFor(() => {
      expect(screen.getByText('Dashboard Protegido')).toBeDefined();
    });
  });
});

