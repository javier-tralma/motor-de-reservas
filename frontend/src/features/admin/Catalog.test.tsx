import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { ServicesPage } from './ServicesPage';
import { ProvidersPage } from './ProvidersPage';
import { AssignServicesModal } from './AssignServicesModal';
import * as adminApi from '../../lib/api/admin';

vi.mock('../../lib/api/admin', () => ({
  getAdminServices: vi.fn(),
  createAdminService: vi.fn(),
  updateAdminService: vi.fn(),
  getAdminProviders: vi.fn(),
  getAdminProviderDetail: vi.fn(),
  createAdminProvider: vi.fn(),
  updateAdminProvider: vi.fn(),
  getAdminProviderServices: vi.fn(),
  replaceAdminProviderServices: vi.fn(),
}));

const mockServices: adminApi.AdminServiceDetail[] = [
  {
    id: 's1',
    name: 'Corte de Cabello',
    description: 'Corte clásico',
    duration_minutes: 30,
    price_amount: 15000,
    is_active: true,
    sort_order: 0,
    created_at: '2026-08-10T10:00:00Z',
    updated_at: '2026-08-10T10:00:00Z',
  },
  {
    id: 's2',
    name: 'Coloración',
    description: 'Tinte completo',
    duration_minutes: 90,
    price_amount: 45000,
    is_active: false,
    sort_order: 1,
    created_at: '2026-08-10T10:00:00Z',
    updated_at: '2026-08-10T10:00:00Z',
  },
];

const mockProvidersList: adminApi.AdminProviderListItem[] = [
  { id: 'p1', name: 'Camila Rojas', is_active: true },
  { id: 'p2', name: 'Gonzalo Valenzuela', is_active: false },
];

const mockProviderDetail: adminApi.AdminProviderDetail = {
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

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

describe('Catalog Administration UI (Milestone 6)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1
  it('creates a new service via modal form', async () => {
    vi.mocked(adminApi.getAdminServices).mockResolvedValue(mockServices);
    vi.mocked(adminApi.createAdminService).mockResolvedValue({ ...mockServices[0], id: 's3' });

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ServicesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByRole('button', { name: /Nuevo Servicio/i }));
    
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeDefined();
    });

    fireEvent.change(screen.getByLabelText(/Nombre \*/i), { target: { value: 'Nuevo Corte' } });
    fireEvent.change(screen.getByLabelText(/Duración \(min\) \*/i), { target: { value: '45' } });
    fireEvent.change(screen.getByLabelText(/Precio \(CLP\) \*/i), { target: { value: '20000' } });

    fireEvent.click(screen.getByRole('button', { name: /Crear Servicio/i }));

    await waitFor(() => {
      expect(adminApi.createAdminService).toHaveBeenCalledWith(expect.objectContaining({
        name: 'Nuevo Corte',
        duration_minutes: 45,
        price_amount: 20000,
      }));
    });
  });

  // 2
  it('edits an existing service via modal form', async () => {
    vi.mocked(adminApi.getAdminServices).mockResolvedValue(mockServices);
    vi.mocked(adminApi.updateAdminService).mockResolvedValue(mockServices[0]);

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ServicesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    const editButtons = await screen.findAllByRole('button', { name: 'Editar' });
    fireEvent.click(editButtons[0]);

    await waitFor(() => {
      expect((screen.getByLabelText(/Nombre \*/i) as HTMLInputElement).value).toBe('Corte de Cabello');
    });

    fireEvent.change(screen.getByLabelText(/Nombre \*/i), { target: { value: 'Corte de Cabello Editado' } });
    fireEvent.click(screen.getByRole('button', { name: /Guardar Cambios/i }));

    await waitFor(() => {
      expect(adminApi.updateAdminService).toHaveBeenCalledWith('s1', expect.objectContaining({
        name: 'Corte de Cabello Editado',
      }));
    });
  });

  // 3
  it('validates service form fields', async () => {
    vi.mocked(adminApi.getAdminServices).mockResolvedValue([]);

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ServicesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByRole('button', { name: /Nuevo Servicio/i }));
    
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeDefined();
    });

    // Clear required fields
    fireEvent.change(screen.getByLabelText(/Nombre \*/i), { target: { value: '' } });
    fireEvent.change(screen.getByLabelText(/Duración \(min\) \*/i), { target: { value: '0' } });
    fireEvent.change(screen.getByLabelText(/Precio \(CLP\) \*/i), { target: { value: '-10' } });

    fireEvent.submit(screen.getByRole('button', { name: /Crear Servicio/i }).closest('form')!);
    
    await waitFor(() => {
      expect(screen.getByText(/El nombre es obligatorio/i)).toBeDefined();
      expect(screen.getByText(/Mínimo 5 minutos/i)).toBeDefined();
      expect(screen.getByText(/El precio no puede ser negativo/i)).toBeDefined();
    });
  });

  // 4
  it('creates a new provider', async () => {
    vi.mocked(adminApi.getAdminProviders).mockResolvedValue(mockProvidersList);
    vi.mocked(adminApi.createAdminProvider).mockResolvedValue(mockProviderDetail);

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ProvidersPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByRole('button', { name: /Nuevo Profesional/i }));
    
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeDefined();
    });

    fireEvent.change(screen.getByLabelText(/Nombre \*/i), { target: { value: 'Nuevo Pro' } });
    fireEvent.click(screen.getByRole('button', { name: /Crear Profesional/i }));

    await waitFor(() => {
      expect(adminApi.createAdminProvider).toHaveBeenCalledWith(expect.objectContaining({
        name: 'Nuevo Pro',
      }));
    });
  });

  // 5
  it('edits provider with phone and email validation', async () => {
    vi.mocked(adminApi.getAdminProviders).mockResolvedValue(mockProvidersList);
    vi.mocked(adminApi.getAdminProviderDetail).mockResolvedValue(mockProviderDetail);
    vi.mocked(adminApi.updateAdminProvider).mockResolvedValue(mockProviderDetail);

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ProvidersPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    const editButtons = await screen.findAllByRole('button', { name: 'Editar' });
    fireEvent.click(editButtons[0]);

    await waitFor(() => {
      expect((screen.getByLabelText(/Nombre \*/i) as HTMLInputElement).value).toBe('Camila Rojas');
    });

    // Invalid phone
    fireEvent.change(screen.getByLabelText(/Teléfono/i), { target: { value: 'abc' } });
    fireEvent.click(screen.getByRole('button', { name: /Guardar Cambios/i }));

    await waitFor(() => {
      expect(screen.getByText(/Formato telefónico inválido/i)).toBeDefined();
    });

    // Valid phone
    fireEvent.change(screen.getByLabelText(/Teléfono/i), { target: { value: '+56987654321' } });
    fireEvent.click(screen.getByRole('button', { name: /Guardar Cambios/i }));

    await waitFor(() => {
      expect(adminApi.updateAdminProvider).toHaveBeenCalled();
    });
  });

  // 6
  it('shows loading skeleton for services list', async () => {
    vi.mocked(adminApi.getAdminServices).mockImplementation(() => new Promise(() => {}));

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ServicesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  // 7
  it('shows error state with retry for services list', async () => {
    vi.mocked(adminApi.getAdminServices).mockRejectedValue(new Error('Network error'));

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ServicesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText(/Ocurrió un error al cargar/i)).toBeDefined();
    const retryButton = screen.getByRole('button', { name: /Reintentar/i });
    expect(retryButton).toBeDefined();

    vi.mocked(adminApi.getAdminServices).mockResolvedValue(mockServices);
    fireEvent.click(retryButton);

    expect(await screen.findByText('Corte de Cabello')).toBeDefined();
  });

  // 8
  it('shows loading skeleton for provider services in AssignServicesModal', async () => {
    vi.mocked(adminApi.getAdminServices).mockResolvedValue(mockServices);
    vi.mocked(adminApi.getAdminProviderServices).mockImplementation(() => new Promise(() => {}));

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AssignServicesModal providerId="p1" providerName="Test" isOpen={true} onClose={() => {}} />
        </MemoryRouter>
      </QueryClientProvider>
    );

    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  // 9
  it('selects and deselects services in AssignServicesModal', async () => {
    vi.mocked(adminApi.getAdminServices).mockResolvedValue(mockServices);
    vi.mocked(adminApi.getAdminProviderServices).mockResolvedValue({ provider_id: 'p1', service_ids: ['s1'] });

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AssignServicesModal providerId="p1" providerName="Test" isOpen={true} onClose={() => {}} />
        </MemoryRouter>
      </QueryClientProvider>
    );

    const checkboxes = await screen.findAllByRole('checkbox') as HTMLInputElement[];
    expect(checkboxes[0].checked).toBe(true);
    expect(checkboxes[1].checked).toBe(false);

    // Deselect s1
    fireEvent.click(checkboxes[0]);
    expect(checkboxes[0].checked).toBe(false);

    // Select s2
    fireEvent.click(checkboxes[1]);
    expect(checkboxes[1].checked).toBe(true);
  });

  // 10
  it('shows inactive service badge in AssignServicesModal', async () => {
    vi.mocked(adminApi.getAdminServices).mockResolvedValue(mockServices);
    vi.mocked(adminApi.getAdminProviderServices).mockResolvedValue({ provider_id: 'p1', service_ids: [] });

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AssignServicesModal providerId="p1" providerName="Test" isOpen={true} onClose={() => {}} />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText('Inactivo')).toBeDefined();
  });

  // 11
  it('closes modal on Escape key', async () => {
    vi.mocked(adminApi.getAdminServices).mockResolvedValue(mockServices);

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ServicesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByRole('button', { name: /Nuevo Servicio/i }));
    
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeDefined();
    });

    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).toBeNull();
    });
  });

  // 12
  it('traps focus with Tab and Shift+Tab', async () => {
    const onClose = vi.fn();
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AssignServicesModal providerId="p1" providerName="Test" isOpen={true} onClose={onClose} />
        </MemoryRouter>
      </QueryClientProvider>
    );

    const dialog = await screen.findByRole('dialog');
    const buttons = dialog.querySelectorAll('button:not([disabled])');
    const firstFocusable = buttons[0] as HTMLElement;
    const lastFocusable = buttons[buttons.length - 1] as HTMLElement;

    // Wait for the query to resolve so checkboxes might appear, 
    // but the test can run with just the header and footer buttons.
    firstFocusable.focus();
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).toBe(lastFocusable);

    lastFocusable.focus();
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: false });
    expect(document.activeElement).toBe(firstFocusable);
  });

  // 13
  it('returns focus to trigger on close', async () => {
    vi.mocked(adminApi.getAdminServices).mockResolvedValue(mockServices);

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ServicesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    const newBtn = await screen.findByRole('button', { name: /Nuevo Servicio/i });
    fireEvent.click(newBtn);
    
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeDefined();
    });

    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).toBeNull();
      expect(document.activeElement).toBe(newBtn);
    });
  });

  // 14
  it('labels are associated with inputs', async () => {
    vi.mocked(adminApi.getAdminServices).mockResolvedValue(mockServices);

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ServicesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByRole('button', { name: /Nuevo Servicio/i }));
    
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeDefined();
    });

    expect(screen.getByLabelText(/Nombre \*/i)).toBeDefined();
    expect(screen.getByLabelText(/Descripción/i)).toBeDefined();
    expect(screen.getByLabelText(/Duración \(min\) \*/i)).toBeDefined();
    expect(screen.getByLabelText(/Precio \(CLP\) \*/i)).toBeDefined();
  });

  // 15
  it('blocks double submit', async () => {
    vi.mocked(adminApi.getAdminServices).mockResolvedValue(mockServices);
    vi.mocked(adminApi.createAdminService).mockImplementation(() => new Promise(() => {}));

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ServicesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByRole('button', { name: /Nuevo Servicio/i }));
    
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeDefined();
    });

    fireEvent.change(screen.getByLabelText(/Nombre \*/i), { target: { value: 'Nuevo' } });
    fireEvent.change(screen.getByLabelText(/Duración \(min\) \*/i), { target: { value: '45' } });
    fireEvent.change(screen.getByLabelText(/Precio \(CLP\) \*/i), { target: { value: '20000' } });

    const submitBtn = screen.getByRole('button', { name: /Crear Servicio/i });
    fireEvent.click(submitBtn);
    fireEvent.click(submitBtn); // Double click

    await waitFor(() => {
      expect(adminApi.createAdminService).toHaveBeenCalledTimes(1);
    });
  });
});
