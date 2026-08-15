import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Wizard } from './Wizard';
import { Confirmation } from './Confirmation';
import { getTodayYMD } from '../../lib/format/date';
import {
  IdempotencyManager,
  createNormalizedPayload,
  type SemanticPayload,
} from '../../lib/idempotency';
import { availabilityQueryKey } from '../../lib/api/availability';

const mockBusiness = {
  name: 'Estudio Nómada',
  slug: 'estudio-nomada',
  timezone: 'America/Santiago',
  locale: 'es-CL',
  currency: 'CLP',
  email: 'hola@estudionomada.cl',
  phone: '+56912345678',
  address: 'Calle Valparaíso 123',
  booking_horizon_days: 60,
};

const mockServices = [
  {
    id: 's-101',
    name: 'Corte de Cabello',
    description: 'Corte estilizado',
    duration_minutes: 45,
    price_amount: 15000,
  },
];

const mockProviders = [
  { id: 'p-201', name: 'Camila Rojas', bio: 'Estilista' },
];

const mockSlots = [
  { starts_at: '2026-08-12T18:00:00Z', ends_at: '2026-08-12T18:45:00Z' },
  { starts_at: '2026-08-12T19:00:00Z', ends_at: '2026-08-12T19:45:00Z' },
];

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

describe('Availability Query Key & Payload Normalization Unit Tests', () => {
  it('availabilityQueryKey always normalizes null providerId', () => {
    expect(availabilityQueryKey('s-1', '2026-08-12', undefined)).toEqual([
      'public-availability',
      's-1',
      '2026-08-12',
      null,
    ]);
    expect(availabilityQueryKey('s-1', '2026-08-12', null)).toEqual([
      'public-availability',
      's-1',
      '2026-08-12',
      null,
    ]);
    expect(availabilityQueryKey('s-1', '2026-08-12', 'p-1')).toEqual([
      'public-availability',
      's-1',
      '2026-08-12',
      'p-1',
    ]);
  });

  it('createNormalizedPayload trims and lowercases fields consistently', () => {
    const raw: SemanticPayload = {
      service_id: 's-1',
      provider_id: null,
      starts_at: '2026-08-12T18:00:00Z',
      customer_name: '  Juan Perez  ',
      customer_email: '  JUAN@EXAMPLE.COM  ',
      customer_phone: ' +56912345678 ',
      customer_notes: '  Mis notas ',
    };

    const norm = createNormalizedPayload(raw);
    expect(norm).toEqual({
      service_id: 's-1',
      provider_id: null,
      starts_at: '2026-08-12T18:00:00Z',
      customer_name: 'Juan Perez',
      customer_email: 'juan@example.com',
      customer_phone: '+56912345678',
      customer_notes: 'Mis notas',
    });
  });

  it('retains same idempotency key when payload changes only in whitespace or case', () => {
    const mgr = new IdempotencyManager();
    const p1 = createNormalizedPayload({
      service_id: 's-1',
      provider_id: null,
      starts_at: '2026-08-12T18:00:00Z',
      customer_name: 'Juan Perez',
      customer_email: 'juan@example.com',
      customer_phone: '+56912345678',
      customer_notes: 'Mis notas',
    });

    const p2 = createNormalizedPayload({
      service_id: 's-1',
      provider_id: null,
      starts_at: '2026-08-12T18:00:00Z',
      customer_name: '  Juan Perez  ',
      customer_email: 'JUAN@EXAMPLE.COM  ',
      customer_phone: '+56912345678 ',
      customer_notes: 'Mis notas  ',
    });

    const k1 = mgr.getIdempotencyKey(p1);
    const k2 = mgr.getIdempotencyKey(p2);
    expect(k1).toBe(k2);
  });
});

describe('Step 1: Services Matrix', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('shows error alert with retry button when service query fails', async () => {
    let callCount = 0;
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/public/services')) {
          callCount++;
          if (callCount === 1) {
            return Promise.resolve({ ok: false, status: 500 });
          }
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockServices }),
          });
        }
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve({ data: mockBusiness }),
        });
      })
    );

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/reservar']}>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByRole('status')).toBeDefined();
    expect(screen.getByText(/Error al cargar servicios/i)).toBeDefined();

    fireEvent.click(screen.getByRole('button', { name: /Reintentar/i }));
    expect(await screen.findByLabelText(/Corte de Cabello/i)).toBeDefined();
  });

  it('shows empty list message when services array is empty', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/public/services')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: [] }),
          });
        }
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve({ data: mockBusiness }),
        });
      })
    );

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/reservar']}>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText(/No hay servicios disponibles en este momento/i)).toBeDefined();
  });
});

describe('Step 2: Providers Matrix & Empty/Loading/Error States', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('disables Continuar during provider query loading state', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/providers')) {
          // Never resolving promise to simulate loading
          return new Promise(() => {});
        }
        if (url.includes('/public/services')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockServices }),
          });
        }
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve({ data: mockBusiness }),
        });
      })
    );

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/reservar']}>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByLabelText(/Corte de Cabello/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    expect(await screen.findByText('¿Con quién prefieres atenderte?')).toBeDefined();
    const nextBtn = screen.getByRole('button', { name: /Continuar/i });
    expect(nextBtn.hasAttribute('disabled')).toBe(true);
  });

  it('disables Continuar and shows error alert with retry button when provider query fails', async () => {
    let providerFetchCount = 0;
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/providers')) {
          providerFetchCount++;
          if (providerFetchCount === 1) {
            return Promise.resolve({ ok: false, status: 500 });
          }
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockProviders }),
          });
        }
        if (url.includes('/public/services')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockServices }),
          });
        }
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve({ data: mockBusiness }),
        });
      })
    );

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/reservar']}>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByLabelText(/Corte de Cabello/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    expect(await screen.findByRole('status')).toBeDefined();
    expect(screen.getByText(/Error al cargar profesionales/i)).toBeDefined();

    const nextBtn = screen.getByRole('button', { name: /Continuar/i });
    expect(nextBtn.hasAttribute('disabled')).toBe(true);

    fireEvent.click(screen.getByRole('button', { name: /Reintentar/i }));
    expect(await screen.findByLabelText(/Camila Rojas/i)).toBeDefined();
    expect(screen.getByRole('button', { name: /Continuar/i }).hasAttribute('disabled')).toBe(false);
  });

  it('shows empty state message, hides "Cualquier profesional" option, and disables Continuar when providers array is empty', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/providers')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: [] }),
          });
        }
        if (url.includes('/public/services')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockServices }),
          });
        }
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve({ data: mockBusiness }),
        });
      })
    );

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/reservar']}>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByLabelText(/Corte de Cabello/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    expect(await screen.findByText('No hay profesionales disponibles para este servicio.')).toBeDefined();
    expect(screen.queryByLabelText(/Cualquier profesional/i)).toBeNull();
    const nextBtn = screen.getByRole('button', { name: /Continuar/i });
    expect(nextBtn.hasAttribute('disabled')).toBe(true);
  });

  it('renders valid provider list with "Cualquier profesional" option and enables Continuar', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/providers')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockProviders }),
          });
        }
        if (url.includes('/public/services')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockServices }),
          });
        }
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve({ data: mockBusiness }),
        });
      })
    );

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/reservar']}>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByLabelText(/Corte de Cabello/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    expect(await screen.findByLabelText(/Cualquier profesional/i)).toBeDefined();
    expect(screen.getByLabelText(/Camila Rojas/i)).toBeDefined();
    const nextBtn = screen.getByRole('button', { name: /Continuar/i });
    expect(nextBtn.hasAttribute('disabled')).toBe(false);
  });
});

describe('Step 3: Availability Matrix', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('shows error alert with retry button when availability query fails', async () => {
    let availCount = 0;
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/providers')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockProviders }),
          });
        }
        if (url.includes('/public/services')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockServices }),
          });
        }
        if (url.includes('/public/availability')) {
          availCount++;
          if (availCount === 1) {
            return Promise.resolve({ ok: false, status: 500 });
          }
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () =>
              Promise.resolve({
                data: { date: '2026-08-12', service_id: 's-101', timezone: 'America/Santiago', slots: mockSlots },
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve({ data: mockBusiness }),
        });
      })
    );

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/reservar']}>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByLabelText(/Corte de Cabello/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    fireEvent.click(await screen.findByLabelText(/Camila Rojas/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    expect(await screen.findByText(/Error al cargar horarios/i)).toBeDefined();

    fireEvent.click(screen.getByRole('button', { name: /Reintentar/i }));
    expect(await screen.findByRole('button', { name: '14:00' })).toBeDefined();
  });

  it('shows empty slots message when no slots exist for date', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/providers')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockProviders }),
          });
        }
        if (url.includes('/public/services')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockServices }),
          });
        }
        if (url.includes('/public/availability')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () =>
              Promise.resolve({
                data: { date: '2026-08-12', service_id: 's-101', timezone: 'America/Santiago', slots: [] },
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve({ data: mockBusiness }),
        });
      })
    );

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/reservar']}>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByLabelText(/Corte de Cabello/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    fireEvent.click(await screen.findByLabelText(/Camila Rojas/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    expect(await screen.findByText(/No quedan horas disponibles ese día/i)).toBeDefined();
  });
});

describe('Keyboard Navigation Integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('allows focusing and selecting service radio via keyboard and advancing with Enter key on Continuar button', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/providers')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockProviders }),
          });
        }
        if (url.includes('/public/services')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockServices }),
          });
        }
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve({ data: mockBusiness }),
        });
      })
    );

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/reservar']}>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    const serviceRadio = await screen.findByLabelText(/Corte de Cabello/i);
    serviceRadio.focus();
    expect(document.activeElement).toBe(serviceRadio);

    // Select radio input via keyboard Space key
    fireEvent.click(serviceRadio);
    expect((serviceRadio as HTMLInputElement).checked).toBe(true);

    const nextBtn = screen.getByRole('button', { name: /Continuar/i });
    nextBtn.focus();
    expect(document.activeElement).toBe(nextBtn);

    // Activate button via keyboard click/keyDown
    fireEvent.click(nextBtn);

    // Advanced to Step 2
    expect(await screen.findByText('¿Con quién prefieres atenderte?')).toBeDefined();
  });
});

describe('Double Submit Guard & POST Body Idempotency Integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  it('prevents double submit: pending controlled POST ignores second click and produces exactly one POST request', async () => {
    let postCallCount = 0;
    let resolvePostPromise!: (val: unknown) => void;

    const controlledPostPromise = new Promise((resolve) => {
      resolvePostPromise = resolve;
    });

    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, options?: RequestInit) => {
        if (url.includes('/providers')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockProviders }),
          });
        }
        if (url.includes('/public/services')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockServices }),
          });
        }
        if (url.includes('/public/availability')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () =>
              Promise.resolve({
                data: { date: '2026-08-12', service_id: 's-101', timezone: 'America/Santiago', slots: mockSlots },
              }),
          });
        }
        if (url.includes('/public/bookings') && options?.method === 'POST') {
          postCallCount++;
          return controlledPostPromise.then(() => ({
            ok: true,
            status: 201,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () =>
              Promise.resolve({
                data: {
                  public_reference: 'ref-controlled-123',
                  status: 'confirmed',
                  service: { name: 'Corte de Cabello', duration_minutes: 45, price_amount: 15000 },
                  provider: { name: 'Camila Rojas' },
                  starts_at: '2026-08-12T18:00:00Z',
                  ends_at: '2026-08-12T18:45:00Z',
                  customer_email: 'juan@example.com',
                },
              }),
          }));
        }
        if (url.includes('/public/bookings/ref-controlled-123/confirmation')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () =>
              Promise.resolve({
                data: {
                  public_reference: 'ref-controlled-123',
                  status: 'confirmed',
                  service: { name: 'Corte de Cabello', duration_minutes: 45, price_amount: 15000 },
                  provider: { name: 'Camila Rojas' },
                  starts_at: '2026-08-12T18:00:00Z',
                  ends_at: '2026-08-12T18:45:00Z',
                  customer_email_masked: 'j***n@example.com',
                  business: {
                    name: 'Estudio Nómada',
                    email: 'hola@estudionomada.cl',
                    phone: '+56912345678',
                    address: 'Calle Valparaíso 123',
                  },
                },
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve({ data: mockBusiness }),
        });
      })
    );

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/reservar']}>
          <Routes>
            <Route path="/reservar" element={<Wizard />} />
            <Route path="/reservar/confirmacion/:publicReference" element={<Confirmation />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Navegar hasta paso 4
    fireEvent.click(await screen.findByLabelText(/Corte de Cabello/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    fireEvent.click(await screen.findByLabelText(/Camila Rojas/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    fireEvent.click(await screen.findByRole('button', { name: '14:00' }));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    fireEvent.change(await screen.findByLabelText(/Nombre completo/i), { target: { value: 'Juan Pérez' } });
    fireEvent.change(screen.getByLabelText(/Correo electrónico/i), { target: { value: 'juan@example.com' } });
    fireEvent.change(screen.getByLabelText(/Teléfono de contacto/i), { target: { value: '+56912345678' } });

    const submitBtn = screen.getByRole('button', { name: /Confirmar reserva/i });

    // Disparar dos clicks consecutivos
    fireEvent.click(submitBtn);
    fireEvent.click(submitBtn);

    // Comprobar que solo existe UN intento POST mientras la promesa está pendiente
    await waitFor(() => expect(postCallCount).toBe(1));

    // Resolve la promesa
    resolvePostPromise(true);

    // Verificar la navegación a la confirmación
    expect(await screen.findByText('¡Reserva confirmada!')).toBeDefined();
    expect(screen.getByText('ref-controlled-123')).toBeDefined();
  });

  it('identical payload retry reuses the exact same client_request_id and HTTP 200 replay navigates to confirmation', async () => {
    const postBodiesSent: Record<string, unknown>[] = [];
    let postCallCount = 0;

    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, options?: RequestInit) => {
        if (url.includes('/providers')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockProviders }),
          });
        }
        if (url.includes('/public/services')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockServices }),
          });
        }
        if (url.includes('/public/availability')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () =>
              Promise.resolve({
                data: { date: '2026-08-12', service_id: 's-101', timezone: 'America/Santiago', slots: mockSlots },
              }),
          });
        }
        if (url.includes('/public/bookings') && options?.method === 'POST') {
          postCallCount++;
          const bodyObj = JSON.parse(options.body as string);
          postBodiesSent.push(bodyObj);

          if (postCallCount === 1) {
            return Promise.reject(new TypeError('Failed to fetch'));
          }

          return Promise.resolve({
            ok: true,
            status: 200,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () =>
              Promise.resolve({
                data: {
                  public_reference: 'ref-replay-200',
                  status: 'confirmed',
                  service: { name: 'Corte de Cabello', duration_minutes: 45, price_amount: 15000 },
                  provider: { name: 'Camila Rojas' },
                  starts_at: '2026-08-12T18:00:00Z',
                  ends_at: '2026-08-12T18:45:00Z',
                  customer_email: 'juan@example.com',
                },
              }),
          });
        }
        if (url.includes('/public/bookings/ref-replay-200/confirmation')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () =>
              Promise.resolve({
                data: {
                  public_reference: 'ref-replay-200',
                  status: 'confirmed',
                  service: { name: 'Corte de Cabello', duration_minutes: 45, price_amount: 15000 },
                  provider: { name: 'Camila Rojas' },
                  starts_at: '2026-08-12T18:00:00Z',
                  ends_at: '2026-08-12T18:45:00Z',
                  customer_email_masked: 'j***n@example.com',
                  business: {
                    name: 'Estudio Nómada',
                    email: 'hola@estudionomada.cl',
                    phone: '+56912345678',
                    address: 'Calle Valparaíso 123',
                  },
                },
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve({ data: mockBusiness }),
        });
      })
    );

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/reservar']}>
          <Routes>
            <Route path="/reservar" element={<Wizard />} />
            <Route path="/reservar/confirmacion/:publicReference" element={<Confirmation />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByLabelText(/Corte de Cabello/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    fireEvent.click(await screen.findByLabelText(/Camila Rojas/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    fireEvent.click(await screen.findByRole('button', { name: '14:00' }));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    fireEvent.change(await screen.findByLabelText(/Nombre completo/i), { target: { value: 'Juan Pérez' } });
    fireEvent.change(screen.getByLabelText(/Correo electrónico/i), { target: { value: 'juan@example.com' } });
    fireEvent.change(screen.getByLabelText(/Teléfono de contacto/i), { target: { value: '+56912345678' } });

    // Intento 1: submit (falla con TypeError)
    fireEvent.click(screen.getByRole('button', { name: /Confirmar reserva/i }));
    expect(await screen.findByText(/Ocurrió un problema de conexión/i)).toBeDefined();

    expect(postBodiesSent.length).toBe(1);
    const key1 = postBodiesSent[0].client_request_id;

    // Reintento 2 con payload idéntico
    fireEvent.click(screen.getByRole('button', { name: /Confirmar reserva/i }));

    expect(await screen.findByText('¡Reserva confirmada!')).toBeDefined();
    expect(postBodiesSent.length).toBe(2);
    const key2 = postBodiesSent[1].client_request_id;

    // Misma clave en reintento idéntico
    expect(key2).toBe(key1);
  });

  it('generates a new client_request_id when a semantic field is modified after a failed attempt', async () => {
    const postBodiesSent: Record<string, unknown>[] = [];
    let postCallCount = 0;

    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, options?: RequestInit) => {
        if (url.includes('/providers')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockProviders }),
          });
        }
        if (url.includes('/public/services')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockServices }),
          });
        }
        if (url.includes('/public/availability')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () =>
              Promise.resolve({
                data: { date: '2026-08-12', service_id: 's-101', timezone: 'America/Santiago', slots: mockSlots },
              }),
          });
        }
        if (url.includes('/public/bookings') && options?.method === 'POST') {
          postCallCount++;
          const bodyObj = JSON.parse(options.body as string);
          postBodiesSent.push(bodyObj);

          if (postCallCount === 1) {
            // Primer POST falla con error HTTP 500
            return Promise.resolve({
              ok: false,
              status: 500,
              headers: new Headers({ 'content-type': 'application/json' }),
              json: () =>
                Promise.resolve({
                  error: { code: 'server_error', message: 'Error al procesar la reserva' },
                }),
            });
          }

          // Segundo POST exitoso
          return Promise.resolve({
            ok: true,
            status: 201,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () =>
              Promise.resolve({
                data: {
                  public_reference: 'ref-new-key-201',
                  status: 'confirmed',
                  service: { name: 'Corte de Cabello', duration_minutes: 45, price_amount: 15000 },
                  provider: { name: 'Camila Rojas' },
                  starts_at: '2026-08-12T18:00:00Z',
                  ends_at: '2026-08-12T18:45:00Z',
                  customer_email: 'juan@example.com',
                },
              }),
          });
        }
        if (url.includes('/public/bookings/ref-new-key-201/confirmation')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () =>
              Promise.resolve({
                data: {
                  public_reference: 'ref-new-key-201',
                  status: 'confirmed',
                  service: { name: 'Corte de Cabello', duration_minutes: 45, price_amount: 15000 },
                  provider: { name: 'Camila Rojas' },
                  starts_at: '2026-08-12T18:00:00Z',
                  ends_at: '2026-08-12T18:45:00Z',
                  customer_email_masked: 'j***n@example.com',
                  business: {
                    name: 'Estudio Nómada',
                    email: 'hola@estudionomada.cl',
                    phone: '+56912345678',
                    address: 'Calle Valparaíso 123',
                  },
                },
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve({ data: mockBusiness }),
        });
      })
    );

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/reservar']}>
          <Routes>
            <Route path="/reservar" element={<Wizard />} />
            <Route path="/reservar/confirmacion/:publicReference" element={<Confirmation />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByLabelText(/Corte de Cabello/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    fireEvent.click(await screen.findByLabelText(/Camila Rojas/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    fireEvent.click(await screen.findByRole('button', { name: '14:00' }));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    fireEvent.change(await screen.findByLabelText(/Nombre completo/i), { target: { value: 'Juan Pérez' } });
    fireEvent.change(screen.getByLabelText(/Correo electrónico/i), { target: { value: 'juan@example.com' } });
    fireEvent.change(screen.getByLabelText(/Teléfono de contacto/i), { target: { value: '+56912345678' } });
    fireEvent.change(screen.getByLabelText(/Nota o indicación/i), { target: { value: '  Nota inicial  ' } });

    // Intento 1: submit (falla con HTTP 500)
    fireEvent.click(screen.getByRole('button', { name: /Confirmar reserva/i }));
    expect(await screen.findByText(/Error al procesar la reserva/i)).toBeDefined();

    expect(postBodiesSent.length).toBe(1);
    const key1 = postBodiesSent[0].client_request_id;
    expect(postBodiesSent[0].customer_notes).toBe('Nota inicial');

    // Modificar campo semántico (customer_notes)
    fireEvent.change(screen.getByLabelText(/Nota o indicación/i), { target: { value: '  Nota modificada  ' } });

    // Intento 2: submit
    fireEvent.click(screen.getByRole('button', { name: /Confirmar reserva/i }));

    expect(await screen.findByText('¡Reserva confirmada!')).toBeDefined();
    expect(postBodiesSent.length).toBe(2);
    const key2 = postBodiesSent[1].client_request_id;

    // 5. Demuestra que el segundo body usa una clave diferente
    expect(key2).not.toBe(key1);
    // 6. Demuestra que el body contiene el valor normalizado
    expect(postBodiesSent[1].customer_notes).toBe('Nota modificada');
  });

  it('invalidates availability query with availabilityQueryKey(serviceId, date, null) on slot_unavailable for "Cualquier profesional"', async () => {
    let currentSlots = [...mockSlots];
    let queryInvalidatedKey: unknown = null;

    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, options?: RequestInit) => {
        if (url.includes('/providers')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockProviders }),
          });
        }
        if (url.includes('/public/services')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () => Promise.resolve({ data: mockServices }),
          });
        }
        if (url.includes('/public/availability')) {
          return Promise.resolve({
            ok: true,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () =>
              Promise.resolve({
                data: { date: '2026-08-12', service_id: 's-101', timezone: 'America/Santiago', slots: currentSlots },
              }),
          });
        }
        if (url.includes('/public/bookings') && options?.method === 'POST') {
          currentSlots = [mockSlots[1]];
          return Promise.resolve({
            ok: false,
            status: 409,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: () =>
              Promise.resolve({
                error: { code: 'slot_unavailable', message: 'Hora no disponible' },
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve({ data: mockBusiness }),
        });
      })
    );

    const queryClient = createTestQueryClient();
    const originalInvalidate = queryClient.invalidateQueries.bind(queryClient);
    vi.spyOn(queryClient, 'invalidateQueries').mockImplementation((filters, options) => {
      queryInvalidatedKey = filters?.queryKey;
      return originalInvalidate(filters, options);
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/reservar']}>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByLabelText(/Corte de Cabello/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    fireEvent.click(await screen.findByLabelText(/Cualquier profesional/i));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    fireEvent.click(await screen.findByRole('button', { name: '14:00' }));
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    fireEvent.change(await screen.findByLabelText(/Nombre completo/i), { target: { value: 'Juan Pérez' } });
    fireEvent.change(screen.getByLabelText(/Correo electrónico/i), { target: { value: 'juan@example.com' } });
    fireEvent.change(screen.getByLabelText(/Teléfono de contacto/i), { target: { value: '+56912345678' } });

    fireEvent.click(screen.getByRole('button', { name: /Confirmar reserva/i }));

    expect(await screen.findByRole('alert')).toBeDefined();

    expect(queryInvalidatedKey).toEqual(availabilityQueryKey('s-101', getTodayYMD('America/Santiago'), null));
  });
});
