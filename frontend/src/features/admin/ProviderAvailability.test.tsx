import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProviderAvailabilityPage } from './ProviderAvailabilityPage';
import { normalizeIntervals, getInitialLocalDate } from '../../lib/utils/availabilityUtils';
import { ProvidersPage } from './ProvidersPage';
import * as adminApi from '../../lib/api/admin';
import { ApiError } from '../../lib/api/client';

const mockHandleUnauthorized = vi.fn();

vi.mock('../auth/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'admin1', display_name: 'Admin Test', email: 'admin@test.cl' },
    business: { name: 'Estudio Test', timezone: 'America/Santiago', locale: 'es-CL' },
    handleUnauthorized: mockHandleUnauthorized,
  }),
}));

vi.mock('../../lib/api/admin', () => ({
  getAdminProviders: vi.fn(),
  getAdminProviderDetail: vi.fn(),
  getAdminProviderAvailabilityRules: vi.fn(),
  replaceAdminProviderAvailabilityRules: vi.fn(),
  getAdminTimeOffs: vi.fn(),
  createAdminTimeOff: vi.fn(),
  deleteAdminTimeOff: vi.fn(),
}));

const mockProvider: adminApi.AdminProviderDetail = {
  id: 'p1',
  name: 'Camila Rojas',
  email: 'camila@estudionomada.cl',
  phone: '+56912345678',
  bio: 'Especialista en corte',
  is_active: true,
  sort_order: 0,
  created_at: '2026-08-10T10:00:00Z',
  updated_at: '2026-08-10T10:00:00Z',
};

const mockRules: adminApi.AdminAvailabilityRuleItem[] = [
  { weekday: 0, start_time: '09:00:00', end_time: '13:00:00' },
  { weekday: 0, start_time: '14:00:00', end_time: '18:00:00' },
  { weekday: 1, start_time: '10:00:00', end_time: '17:00:00' },
];

const mockTimeOffs: adminApi.AdminTimeOffDetail[] = [
  {
    id: 'to1',
    provider_id: 'p1',
    starts_at: '2026-08-20T09:00:00-04:00',
    ends_at: '2026-08-22T18:00:00-04:00',
    reason: 'Vacaciones de invierno',
    created_at: '2026-08-10T10:00:00-04:00',
    updated_at: '2026-08-10T10:00:00-04:00',
  },
];

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

describe('Milestone 7: Provider Availability & Time Off UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('availabilityUtils', () => {
    it('sorts intervals by weekday and start_time', () => {
      const raw: adminApi.AdminAvailabilityRuleItem[] = [
        { weekday: 1, start_time: '14:00', end_time: '18:00' },
        { weekday: 0, start_time: '14:00', end_time: '18:00' },
        { weekday: 0, start_time: '09:00', end_time: '13:00' },
      ];
      const normalized = normalizeIntervals(raw);
      expect(normalized).toEqual([
        { weekday: 0, start_time: '09:00:00', end_time: '13:00:00' },
        { weekday: 0, start_time: '14:00:00', end_time: '18:00:00' },
        { weekday: 1, start_time: '14:00:00', end_time: '18:00:00' },
      ]);
    });

    it('merges adjacent intervals on the same day before submission', () => {
      const raw: adminApi.AdminAvailabilityRuleItem[] = [
        { weekday: 0, start_time: '09:00', end_time: '11:00' },
        { weekday: 0, start_time: '11:00', end_time: '13:00' },
        { weekday: 0, start_time: '13:00', end_time: '18:00' },
      ];
      const normalized = normalizeIntervals(raw);
      expect(normalized).toEqual([
        { weekday: 0, start_time: '09:00:00', end_time: '18:00:00' },
      ]);
    });

    it('preserves non-adjacent intervals with breaks', () => {
      const raw: adminApi.AdminAvailabilityRuleItem[] = [
        { weekday: 0, start_time: '09:00', end_time: '13:00' },
        { weekday: 0, start_time: '14:00', end_time: '18:00' },
      ];
      const normalized = normalizeIntervals(raw);
      expect(normalized).toEqual([
        { weekday: 0, start_time: '09:00:00', end_time: '13:00:00' },
        { weekday: 0, start_time: '14:00:00', end_time: '18:00:00' },
      ]);
    });

    it('getInitialLocalDate respects timezone instead of UTC', () => {
      // 2026-08-15 02:00:00 UTC is 2026-08-14 22:00:00 in America/Santiago (UTC-4)
      const testInstant = new Date('2026-08-15T02:00:00Z');
      expect(getInitialLocalDate('America/Santiago', testInstant)).toBe('2026-08-14');
      expect(getInitialLocalDate('UTC', testInstant)).toBe('2026-08-15');
    });
  });

  describe('ProviderAvailabilityPage Component', () => {
    it('renders provider info, weekly schedule and time off list', async () => {
      vi.mocked(adminApi.getAdminProviderDetail).mockResolvedValue(mockProvider);
      vi.mocked(adminApi.getAdminProviderAvailabilityRules).mockResolvedValue(mockRules);
      vi.mocked(adminApi.getAdminTimeOffs).mockResolvedValue(mockTimeOffs);

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/admin/profesionales/p1/disponibilidad']}>
            <Routes>
              <Route
                path="/admin/profesionales/:providerId/disponibilidad"
                element={<ProviderAvailabilityPage />}
              />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      // Verify Provider Header
      expect(await screen.findByText('Camila Rojas')).toBeDefined();
      expect(screen.getByText(/camila@estudionomada.cl/i)).toBeDefined();
      expect(screen.getByText('Activo')).toBeDefined();

      // Verify Weekly Schedule Section
      expect(screen.getByText('Horario Semanal Habitual')).toBeDefined();
      expect(screen.getByText('Lunes')).toBeDefined();
      expect(screen.getByText('Martes')).toBeDefined();

      // Verify Time Off Section
      expect(screen.getByText('Bloqueos y Ausencias (Time Off)')).toBeDefined();
      expect(screen.getByText('Vacaciones de invierno')).toBeDefined();
    });

    it('derives initial date in CreateTimeOffModal from business timezone', async () => {
      // Set fixed instant where UTC is Aug 15 but Santiago is Aug 14
      vi.setSystemTime(new Date('2026-08-15T02:00:00Z'));

      vi.mocked(adminApi.getAdminProviderDetail).mockResolvedValue(mockProvider);
      vi.mocked(adminApi.getAdminProviderAvailabilityRules).mockResolvedValue([]);
      vi.mocked(adminApi.getAdminTimeOffs).mockResolvedValue([]);

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/admin/profesionales/p1/disponibilidad']}>
            <Routes>
              <Route
                path="/admin/profesionales/:providerId/disponibilidad"
                element={<ProviderAvailabilityPage />}
              />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      const addBtn = await screen.findByRole('button', { name: /Añadir Bloqueo/i });
      fireEvent.click(addBtn);

      expect(await screen.findByRole('dialog')).toBeDefined();
      const startInput = screen.getByLabelText(/Fecha de inicio/i) as HTMLInputElement;
      const endInput = screen.getByLabelText(/Fecha de término/i) as HTMLInputElement;

      // Must be 2026-08-14 (Santiago local date), NOT 2026-08-15 (UTC date)
      expect(startInput.value).toBe('2026-08-14');
      expect(endInput.value).toBe('2026-08-14');
    });

    it('edits weekly schedule, merges adjacent intervals and saves', async () => {
      vi.mocked(adminApi.getAdminProviderDetail).mockResolvedValue(mockProvider);
      vi.mocked(adminApi.getAdminProviderAvailabilityRules).mockResolvedValue(mockRules);
      vi.mocked(adminApi.getAdminTimeOffs).mockResolvedValue([]);
      vi.mocked(adminApi.replaceAdminProviderAvailabilityRules).mockResolvedValue([
        { weekday: 0, start_time: '09:00:00', end_time: '18:00:00' },
      ]);

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/admin/profesionales/p1/disponibilidad']}>
            <Routes>
              <Route
                path="/admin/profesionales/:providerId/disponibilidad"
                element={<ProviderAvailabilityPage />}
              />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      await screen.findByText('Horario Semanal Habitual');

      // Add a third interval to Lunes: 13:00 to 14:00 (which makes 09:00-13:00, 13:00-14:00, 14:00-18:00 completely adjacent)
      const addIntervalButtons = screen.getAllByRole('button', { name: /\+ Añadir tramo/i });
      fireEvent.click(addIntervalButtons[0]);

      const lunesInputs = screen.getAllByLabelText(/Lunes tramo/i);
      // tramo 3 start and end inputs
      fireEvent.change(lunesInputs[4], { target: { value: '13:00' } });
      fireEvent.change(lunesInputs[5], { target: { value: '14:00' } });

      const saveBtn = screen.getByRole('button', { name: /Guardar Horarios/i });
      expect((saveBtn as HTMLButtonElement).disabled).toBe(false);
      fireEvent.click(saveBtn);

      await waitFor(() => {
        expect(adminApi.replaceAdminProviderAvailabilityRules).toHaveBeenCalledWith(
          'p1',
          expect.arrayContaining([
            { weekday: 0, start_time: '09:00:00', end_time: '18:00:00' },
          ])
        );
      });

      expect(await screen.findByText('Horarios guardados correctamente.')).toBeDefined();
    });

    it('detects invalid time order and overlapping intervals, preventing submit', async () => {
      vi.mocked(adminApi.getAdminProviderDetail).mockResolvedValue(mockProvider);
      vi.mocked(adminApi.getAdminProviderAvailabilityRules).mockResolvedValue(mockRules);
      vi.mocked(adminApi.getAdminTimeOffs).mockResolvedValue([]);

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/admin/profesionales/p1/disponibilidad']}>
            <Routes>
              <Route
                path="/admin/profesionales/:providerId/disponibilidad"
                element={<ProviderAvailabilityPage />}
              />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      await screen.findByText('Horario Semanal Habitual');

      // Set invalid order: start 18:00, end 09:00
      const lunesInputs = screen.getAllByLabelText(/Lunes tramo/i);
      fireEvent.change(lunesInputs[0], { target: { value: '18:00' } });
      fireEvent.change(lunesInputs[1], { target: { value: '09:00' } });

      expect(await screen.findByText(/La hora de inicio \(18:00\) debe ser anterior/i)).toBeDefined();
      const saveBtn = screen.getByRole('button', { name: /Guardar Horarios/i });
      expect((saveBtn as HTMLButtonElement).disabled).toBe(true);

      // Fix start/end order, but create overlap (09:00-15:00 and 14:00-18:00)
      fireEvent.change(lunesInputs[0], { target: { value: '09:00' } });
      fireEvent.change(lunesInputs[1], { target: { value: '15:00' } });

      expect(await screen.findByText(/Conflicto de solape entre tramos/i)).toBeDefined();
      expect((saveBtn as HTMLButtonElement).disabled).toBe(true);
    });

    it('creates a time off block via CreateTimeOffModal', async () => {
      vi.mocked(adminApi.getAdminProviderDetail).mockResolvedValue(mockProvider);
      vi.mocked(adminApi.getAdminProviderAvailabilityRules).mockResolvedValue([]);
      vi.mocked(adminApi.getAdminTimeOffs).mockResolvedValue([]);
      vi.mocked(adminApi.createAdminTimeOff).mockResolvedValue({
        id: 'to2',
        provider_id: 'p1',
        starts_at: '2026-08-25T09:00:00-04:00',
        ends_at: '2026-08-25T18:00:00-04:00',
        reason: 'Capacitación',
        created_at: '2026-08-10T10:00:00-04:00',
        updated_at: '2026-08-10T10:00:00-04:00',
      });

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/admin/profesionales/p1/disponibilidad']}>
            <Routes>
              <Route
                path="/admin/profesionales/:providerId/disponibilidad"
                element={<ProviderAvailabilityPage />}
              />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      const addBtn = await screen.findByRole('button', { name: /Añadir Bloqueo/i });
      fireEvent.click(addBtn);

      expect(await screen.findByRole('dialog')).toBeDefined();
      expect(screen.getByText(/Registrar Bloqueo o Ausencia/i)).toBeDefined();

      fireEvent.change(screen.getByLabelText(/Fecha de inicio/i), { target: { value: '2026-08-25' } });
      fireEvent.change(screen.getByLabelText(/Hora de inicio/i), { target: { value: '09:00' } });
      fireEvent.change(screen.getByLabelText(/Fecha de término/i), { target: { value: '2026-08-25' } });
      fireEvent.change(screen.getByLabelText(/Hora de término/i), { target: { value: '18:00' } });
      fireEvent.change(screen.getByLabelText(/Motivo/i), { target: { value: 'Capacitación' } });

      fireEvent.click(screen.getByRole('button', { name: 'Registrar Bloqueo' }));

      await waitFor(() => {
        expect(adminApi.createAdminTimeOff).toHaveBeenCalledWith({
          provider_id: 'p1',
          starts_at_local: '2026-08-25T09:00:00',
          ends_at_local: '2026-08-25T18:00:00',
          reason: 'Capacitación',
        });
      });
    });

    it('validates starts_at < ends_at in CreateTimeOffModal', async () => {
      vi.mocked(adminApi.getAdminProviderDetail).mockResolvedValue(mockProvider);
      vi.mocked(adminApi.getAdminProviderAvailabilityRules).mockResolvedValue([]);
      vi.mocked(adminApi.getAdminTimeOffs).mockResolvedValue([]);

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/admin/profesionales/p1/disponibilidad']}>
            <Routes>
              <Route
                path="/admin/profesionales/:providerId/disponibilidad"
                element={<ProviderAvailabilityPage />}
              />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      fireEvent.click(await screen.findByRole('button', { name: /Añadir Bloqueo/i }));
      await screen.findByRole('dialog');

      fireEvent.change(screen.getByLabelText(/Fecha de inicio/i), { target: { value: '2026-08-25' } });
      fireEvent.change(screen.getByLabelText(/Hora de inicio/i), { target: { value: '18:00' } });
      fireEvent.change(screen.getByLabelText(/Fecha de término/i), { target: { value: '2026-08-25' } });
      fireEvent.change(screen.getByLabelText(/Hora de término/i), { target: { value: '09:00' } });

      fireEvent.click(screen.getByRole('button', { name: 'Registrar Bloqueo' }));

      expect(await screen.findByText(/La fecha y hora de término debe ser posterior a la de inicio/i)).toBeDefined();
      expect(adminApi.createAdminTimeOff).not.toHaveBeenCalled();
    });

    it('handles 401 Unauthorized when creating time off by calling handleUnauthorized', async () => {
      vi.mocked(adminApi.getAdminProviderDetail).mockResolvedValue(mockProvider);
      vi.mocked(adminApi.getAdminProviderAvailabilityRules).mockResolvedValue([]);
      vi.mocked(adminApi.getAdminTimeOffs).mockResolvedValue([]);
      vi.mocked(adminApi.createAdminTimeOff).mockRejectedValue(
        new ApiError(401, { code: 'unauthorized', message: 'Session expired' })
      );

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/admin/profesionales/p1/disponibilidad']}>
            <Routes>
              <Route
                path="/admin/profesionales/:providerId/disponibilidad"
                element={<ProviderAvailabilityPage />}
              />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      fireEvent.click(await screen.findByRole('button', { name: /Añadir Bloqueo/i }));
      await screen.findByRole('dialog');

      fireEvent.change(screen.getByLabelText(/Fecha de inicio/i), { target: { value: '2026-08-25' } });
      fireEvent.change(screen.getByLabelText(/Hora de inicio/i), { target: { value: '09:00' } });
      fireEvent.change(screen.getByLabelText(/Fecha de término/i), { target: { value: '2026-08-25' } });
      fireEvent.change(screen.getByLabelText(/Hora de término/i), { target: { value: '18:00' } });

      fireEvent.click(screen.getByRole('button', { name: 'Registrar Bloqueo' }));

      await waitFor(() => {
        expect(mockHandleUnauthorized).toHaveBeenCalled();
      });
    });

    it('handles 401 Unauthorized when saving schedule and when deleting time off', async () => {
      vi.mocked(adminApi.getAdminProviderDetail).mockResolvedValue(mockProvider);
      vi.mocked(adminApi.getAdminProviderAvailabilityRules).mockResolvedValue(mockRules);
      vi.mocked(adminApi.getAdminTimeOffs).mockResolvedValue(mockTimeOffs);
      vi.mocked(adminApi.replaceAdminProviderAvailabilityRules).mockRejectedValue(
        new ApiError(401, { code: 'unauthorized', message: 'Session expired' })
      );
      vi.mocked(adminApi.deleteAdminTimeOff).mockRejectedValue(
        new ApiError(401, { code: 'unauthorized', message: 'Session expired' })
      );

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/admin/profesionales/p1/disponibilidad']}>
            <Routes>
              <Route
                path="/admin/profesionales/:providerId/disponibilidad"
                element={<ProviderAvailabilityPage />}
              />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      await screen.findByText('Horario Semanal Habitual');

      // Trigger schedule replacement 401 by toggling Domingo active
      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[6]);

      const saveBtn = screen.getByRole('button', { name: /Guardar Horarios/i });
      expect((saveBtn as HTMLButtonElement).disabled).toBe(false);
      fireEvent.click(saveBtn);

      await waitFor(() => {
        expect(mockHandleUnauthorized).toHaveBeenCalled();
      });

      mockHandleUnauthorized.mockClear();

      // Trigger time off delete 401
      const deleteBtn = screen.getByRole('button', { name: 'Eliminar' });
      fireEvent.click(deleteBtn);

      const confirmDeleteBtn = await screen.findByRole('button', { name: 'Eliminar Bloqueo' });
      fireEvent.click(confirmDeleteBtn);

      await waitFor(() => {
        expect(mockHandleUnauthorized).toHaveBeenCalled();
      });
    });

    it('displays inline error on delete failure without window.alert and keeps confirmation modal open', async () => {
      vi.mocked(adminApi.getAdminProviderDetail).mockResolvedValue(mockProvider);
      vi.mocked(adminApi.getAdminProviderAvailabilityRules).mockResolvedValue([]);
      vi.mocked(adminApi.getAdminTimeOffs).mockResolvedValue(mockTimeOffs);
      vi.mocked(adminApi.deleteAdminTimeOff).mockRejectedValue(
        new Error('No se pudo conectar con el servidor.')
      );

      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/admin/profesionales/p1/disponibilidad']}>
            <Routes>
              <Route
                path="/admin/profesionales/:providerId/disponibilidad"
                element={<ProviderAvailabilityPage />}
              />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      const deleteBtn = await screen.findByRole('button', { name: 'Eliminar' });
      fireEvent.click(deleteBtn);

      const confirmModalTitle = await screen.findByText(/Eliminar Bloqueo de Disponibilidad/i);
      expect(confirmModalTitle).toBeDefined();

      const confirmDeleteBtn = screen.getByRole('button', { name: 'Eliminar Bloqueo' });
      fireEvent.click(confirmDeleteBtn);

      // Verify window.alert was NOT called
      await waitFor(() => {
        expect(alertSpy).not.toHaveBeenCalled();
      });

      // Verify inline error with role="alert"
      const inlineAlert = await screen.findByRole('alert');
      expect(inlineAlert).toBeDefined();
      expect(inlineAlert.textContent).toContain('No se pudo conectar con el servidor.');

      // Verify modal remains open
      expect(screen.getByText(/Eliminar Bloqueo de Disponibilidad/i)).toBeDefined();

      // Cancelling modal clears the error
      fireEvent.click(screen.getByRole('button', { name: 'Volver' }));
      await waitFor(() => {
        expect(screen.queryByText(/Eliminar Bloqueo de Disponibilidad/i)).toBeNull();
        expect(screen.queryByRole('alert')).toBeNull();
      });

      alertSpy.mockRestore();
    });

    it('deletes a time off block with confirmation modal successfully', async () => {
      vi.mocked(adminApi.getAdminProviderDetail).mockResolvedValue(mockProvider);
      vi.mocked(adminApi.getAdminProviderAvailabilityRules).mockResolvedValue([]);
      vi.mocked(adminApi.getAdminTimeOffs).mockResolvedValue(mockTimeOffs);
      vi.mocked(adminApi.deleteAdminTimeOff).mockResolvedValue(undefined);

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/admin/profesionales/p1/disponibilidad']}>
            <Routes>
              <Route
                path="/admin/profesionales/:providerId/disponibilidad"
                element={<ProviderAvailabilityPage />}
              />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      const deleteBtn = await screen.findByRole('button', { name: 'Eliminar' });
      fireEvent.click(deleteBtn);

      expect(await screen.findByText(/Eliminar Bloqueo de Disponibilidad/i)).toBeDefined();
      const confirmDeleteBtn = screen.getByRole('button', { name: 'Eliminar Bloqueo' });
      fireEvent.click(confirmDeleteBtn);

      await waitFor(() => {
        expect(adminApi.deleteAdminTimeOff).toHaveBeenCalledWith('to1');
      });
    });

    it('displays Disponibilidad action button on ProvidersPage navigating to availability route', async () => {
      vi.mocked(adminApi.getAdminProviders).mockResolvedValue([
        { id: 'p1', name: 'Camila Rojas', is_active: true },
      ]);

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <ProvidersPage />
          </MemoryRouter>
        </QueryClientProvider>
      );

      const availLink = await screen.findByRole('link', { name: /Disponibilidad/i });
      expect(availLink).toBeDefined();
      expect(availLink.getAttribute('href')).toBe('/admin/profesionales/p1/disponibilidad');
    });
  });
});
