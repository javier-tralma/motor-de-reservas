import React, { useRef, useState } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { Button } from '../../components/Button';
import { InlineAlert } from '../../components/InlineAlert';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { StepCustomer } from '../public-booking/StepCustomer';
import { StepDateTime } from '../public-booking/StepDateTime';
import { AdminCalendar } from '../admin/AdminCalendar';
import { ServicesPage } from '../admin/ServicesPage';
import { ProvidersPage } from '../admin/ProvidersPage';
import * as adminApi from '../../lib/api/admin';
import * as bookingsApi from '../../lib/api/bookings';

vi.mock('../auth/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'admin1', display_name: 'Admin Test', email: 'admin@test.cl' },
    business: { name: 'Estudio Nómada', timezone: 'America/Santiago', locale: 'es-CL' },
    handleUnauthorized: vi.fn(),
  }),
}));

vi.mock('../../lib/api/admin', async () => {
  const actual = await vi.importActual<typeof import('../../lib/api/admin')>('../../lib/api/admin');
  return {
    ...actual,
    getAdminBookings: vi.fn(),
    getAdminBookingDetail: vi.fn(),
    getAdminProviders: vi.fn(),
    getAdminServices: vi.fn(),
  };
});

vi.mock('../../lib/api/bookings', async () => {
  const actual = await vi.importActual<typeof import('../../lib/api/bookings')>('../../lib/api/bookings');
  return {
    ...actual,
    createPublicBooking: vi.fn(),
  };
});

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
      mutations: { retry: false },
    },
  });

describe('Milestone 11 - UX, Accessibility & Responsive Hardening Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('1. Button & Loading State Semantics', () => {
    it('Button with isLoading preserves accessible name, has aria-busy, is disabled, and hides spinner from screen readers', () => {
      const { rerender } = render(
        <Button isLoading={true}>Confirmar Reserva</Button>
      );

      // Accessible name is preserved
      const btn = screen.getByRole('button', { name: /Confirmar Reserva/i });
      expect(btn).toBeDefined();
      expect(btn.hasAttribute('disabled')).toBe(true);
      expect(btn.getAttribute('aria-busy')).toBe('true');

      // Spinner is decorative (aria-hidden)
      const spinner = btn.querySelector('svg');
      expect(spinner).not.toBeNull();
      expect(spinner?.getAttribute('aria-hidden')).toBe('true');

      // Returns to normal enabled state
      rerender(<Button isLoading={false}>Confirmar Reserva</Button>);
      expect(btn.hasAttribute('disabled')).toBe(false);
      expect(btn.getAttribute('aria-busy')).toBeNull();
      expect(btn.querySelector('svg')).toBeNull();
    });

    it('StepCustomer public flow prevents double submit and keeps accessible action name', async () => {
      let resolvePromise: (value: bookingsApi.BookingPublicCreatedData) => void = () => {};
      const pendingPromise = new Promise<bookingsApi.BookingPublicCreatedData>((resolve) => {
        resolvePromise = resolve;
      });

      vi.mocked(bookingsApi.createPublicBooking).mockImplementation(() => pendingPromise);

      const mockService = {
        id: 's1',
        name: 'Corte Clásico',
        description: 'Corte',
        duration_minutes: 30,
        price_amount: 15000,
      };
      const mockSlot = {
        starts_at: '2026-08-10T14:00:00-04:00',
        ends_at: '2026-08-10T14:30:00-04:00',
      };

      const onSuccess = vi.fn();
      const onSlotConflict = vi.fn();

      render(
        <StepCustomer
          service={mockService}
          provider={null}
          selectedDate="2026-08-10"
          selectedSlot={mockSlot}
          getClientRequestId={() => 'req-123'}
          initialCustomerData={{
            customer_name: 'Ana López',
            customer_email: 'ana@example.com',
            customer_phone: '+56987654321',
          }}
          onBack={vi.fn()}
          onSuccess={onSuccess}
          onSlotConflict={onSlotConflict}
          onCustomerDataChange={vi.fn()}
        />
      );

      const submitBtn = screen.getByRole('button', { name: /Confirmar reserva/i });
      expect(submitBtn.hasAttribute('disabled')).toBe(false);

      // Submit once
      fireEvent.click(submitBtn);

      // Submit a second time immediately
      fireEvent.click(submitBtn);

      // Verify createPublicBooking was only called once after async validation
      await waitFor(() => {
        expect(bookingsApi.createPublicBooking).toHaveBeenCalledTimes(1);
      });

      // Button is now disabled and aria-busy
      expect(submitBtn.hasAttribute('disabled')).toBe(true);
      expect(submitBtn.getAttribute('aria-busy')).toBe('true');

      // Resolve
      const mockCreatedResult: bookingsApi.BookingPublicCreatedData = {
        public_reference: 'REF-ANA-1',
        status: 'confirmed',
        starts_at: '2026-08-10T14:00:00-04:00',
        ends_at: '2026-08-10T14:30:00-04:00',
        service: mockService,
        provider: { name: 'Camila Rojas' },
        customer_email: 'ana@example.com',
      };
      resolvePromise(mockCreatedResult);
      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalledWith('REF-ANA-1');
      });
    });
  });

  describe('2. Focus Trap, Tab Cycle, Escape, Inert & Re-render Stability', () => {
    const TrapTestComponent: React.FC = () => {
      const [isOpen, setIsOpen] = useState(false);
      const containerRef = useRef<HTMLDivElement | null>(null);
      const triggerRef = useRef<HTMLButtonElement | null>(null);
      const backgroundRef = useRef<HTMLDivElement | null>(null);

      useFocusTrap(containerRef, isOpen, {
        onEscape: () => setIsOpen(false),
        returnFocusRef: triggerRef,
        inertRefs: [backgroundRef],
      });

      return (
        <div>
          <div ref={backgroundRef} data-testid="bg-container">
            <button ref={triggerRef} onClick={() => setIsOpen(true)}>
              Abrir Overlay
            </button>
            <input placeholder="Fondo input" />
          </div>

          {isOpen && (
            <div ref={containerRef} role="dialog" aria-modal="true">
              <h2>Overlay Activo</h2>
              <button id="modal-btn-1">Botón Uno</button>
              <button id="modal-btn-2">Botón Dos</button>
            </div>
          )}
        </div>
      );
    };

    it('manages initial focus, Tab cycle, Escape key, background inert, and trigger restoration', async () => {
      render(<TrapTestComponent />);
      const bgContainer = screen.getByTestId('bg-container');
      const triggerBtn = screen.getByText('Abrir Overlay');

      expect(bgContainer.hasAttribute('inert')).toBe(false);

      // Open
      fireEvent.click(triggerBtn);

      const dialog = screen.getByRole('dialog');
      expect(dialog).toBeDefined();

      // Background gets inert
      expect(bgContainer.hasAttribute('inert')).toBe(true);

      // Initial focus on first element in modal
      const btn1 = screen.getByText('Botón Uno');
      const btn2 = screen.getByText('Botón Dos');
      expect(document.activeElement).toBe(btn1);

      // Tab from btn2 wraps to btn1
      btn2.focus();
      expect(document.activeElement).toBe(btn2);
      fireEvent.keyDown(window, { key: 'Tab' });
      expect(document.activeElement).toBe(btn1);

      // Shift+Tab from btn1 wraps to btn2
      fireEvent.keyDown(window, { key: 'Tab', shiftKey: true });
      expect(document.activeElement).toBe(btn2);

      // Escape closes overlay
      fireEvent.keyDown(window, { key: 'Escape' });

      // Dialog is gone
      expect(screen.queryByRole('dialog')).toBeNull();

      // Inert is removed from background
      expect(bgContainer.hasAttribute('inert')).toBe(false);

      // Focus is restored to trigger button
      expect(document.activeElement).toBe(triggerBtn);
    });

    const FormModalWithDynamicOptions: React.FC = () => {
      const [isOpen, setIsOpen] = useState(true);
      const [text, setText] = useState('');
      const modalRef = useRef<HTMLDivElement | null>(null);
      const triggerRef = useRef<HTMLButtonElement | null>(null);
      const bgRef = useRef<HTMLDivElement | null>(null);
      const inputRef = useRef<HTMLInputElement | null>(null);

      // Pass inline onEscape function and new array literal on every render to verify stability
      useFocusTrap(modalRef, isOpen, {
        onEscape: () => setIsOpen(false),
        returnFocusRef: triggerRef,
        initialFocusRef: inputRef,
        inertRefs: [bgRef],
      });

      return (
        <div>
          <div ref={bgRef} data-testid="bg-element">
            <button ref={triggerRef} onClick={() => setIsOpen(true)}>
              Disparador
            </button>
          </div>

          {isOpen && (
            <div ref={modalRef} role="dialog" aria-modal="true">
              <input
                ref={inputRef}
                data-testid="modal-input"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Escribe aquí"
              />
              <button onClick={() => setIsOpen(false)}>Cerrar</button>
            </div>
          )}
        </div>
      );
    };

    it('preserves focus on input during re-renders, maintains inert on background, and restores trigger only once upon close', () => {
      render(<FormModalWithDynamicOptions />);

      const bgElement = screen.getByTestId('bg-element');
      const triggerBtn = screen.getByText('Disparador');
      const input = screen.getByTestId('modal-input');

      // Initial focus went to input
      expect(document.activeElement).toBe(input);
      expect(bgElement.hasAttribute('inert')).toBe(true);

      // Simulate user typing character by character (triggering multiple re-renders with new inline function identities)
      const typedText = 'Prueba';
      for (let i = 0; i < typedText.length; i++) {
        const nextVal = typedText.slice(0, i + 1);
        fireEvent.change(input, { target: { value: nextVal } });

        // 1. Input value updates completely
        expect((input as HTMLInputElement).value).toBe(nextVal);

        // 2. Focus remains on the input and is NOT stolen back to the trigger or initial focus reset
        expect(document.activeElement).toBe(input);
        expect(document.activeElement).not.toBe(triggerBtn);

        // 3. Background remains inert
        expect(bgElement.hasAttribute('inert')).toBe(true);
      }

      // Value is fully written
      expect((input as HTMLInputElement).value).toBe('Prueba');
      expect(document.activeElement).toBe(input);

      // Close modal using Escape
      fireEvent.keyDown(window, { key: 'Escape' });

      // Modal closed
      expect(screen.queryByRole('dialog')).toBeNull();

      // Inert removed
      expect(bgElement.hasAttribute('inert')).toBe(false);

      // Focus restored once to trigger
      expect(document.activeElement).toBe(triggerBtn);
    });
  });

  describe('3. Proportional InlineAlert Roles & Focus Management', () => {
    it('InlineAlert with type="error" and no isUrgent prop defaults to role="status" and does not move focus', () => {
      render(
        <div>
          <button id="focus-btn" autoFocus>
            Botón enfocado
          </button>
          <InlineAlert
            type="error"
            title="Error recuperable"
            message="No pudimos cargar los datos. Puedes reintentar."
          />
        </div>
      );

      // Renders as role="status"
      const statusEl = screen.getByRole('status');
      expect(statusEl).toBeDefined();
      expect(screen.queryByRole('alert')).toBeNull();

      // Focus remains on the active button, no focus stealing
      const focusBtn = screen.getByText('Botón enfocado');
      expect(document.activeElement).toBe(focusBtn);
    });

    it('InlineAlert with isUrgent={true} renders role="alert" and can receive programmatic focus', () => {
      const alertRef = React.createRef<HTMLDivElement>();
      render(
        <InlineAlert
          ref={alertRef}
          type="error"
          isUrgent={true}
          tabIndex={-1}
          title="Error Crítico"
          message="Ese horario acaba de ser reservado."
        />
      );

      const alertEl = screen.getByRole('alert');
      expect(alertEl).toBeDefined();
      expect(alertEl.getAttribute('tabindex')).toBe('-1');

      alertRef.current?.focus();
      expect(document.activeElement).toBe(alertEl);
    });

    it('explicit role prop takes precedence over default and isUrgent', () => {
      render(
        <InlineAlert
          type="error"
          isUrgent={false}
          role="region"
          title="Región personalizada"
          message="Mensaje"
        />
      );

      expect(screen.getByRole('region')).toBeDefined();
      expect(screen.queryByRole('status')).toBeNull();
      expect(screen.queryByRole('alert')).toBeNull();
    });

    it('StepDateTime focuses urgent conflict alert on slot_unavailable', async () => {
      const queryClient = createTestQueryClient();
      const mockService = {
        id: 's1',
        name: 'Corte Clásico',
        description: 'Corte',
        duration_minutes: 30,
        price_amount: 15000,
      };

      render(
        <QueryClientProvider client={queryClient}>
          <StepDateTime
            service={mockService}
            provider={null}
            selectedDate="2026-08-10"
            selectedSlot={null}
            onSelectDate={vi.fn()}
            onSelectSlot={vi.fn()}
            onNext={vi.fn()}
            onBack={vi.fn()}
            conflictMessage="Esa hora acaba de ser reservada. Actualizamos los horarios para que elijas otra."
          />
        </QueryClientProvider>
      );

      const alertEl = await screen.findByRole('alert');
      expect(alertEl).toBeDefined();
      expect(document.activeElement).toBe(alertEl);
    });
  });

  describe('4. Responsive Calendar View Persistence & Initial Adaptation', () => {
    const mockCalendarEvents = [
      {
        id: 'ev-1',
        kind: 'booking' as const,
        starts_at: '2026-08-10T10:00:00-04:00',
        ends_at: '2026-08-10T11:00:00-04:00',
        provider_id: 'p1',
        provider_name: 'Camila Rojas',
        booking_status: 'confirmed' as const,
        customer_display_name: 'Pedro G.',
        service_name: 'Corte',
        reason: null,
      },
    ];

    it('mounts with listWeek on mobile and timeGridWeek on desktop', () => {
      // 1. Mobile mount
      window.innerWidth = 500;
      const { unmount } = render(
        <AdminCalendar
          events={mockCalendarEvents}
          timezone="America/Santiago"
          onDatesSet={vi.fn()}
          onEventClick={vi.fn()}
          userSelectedView={null}
          onViewChange={vi.fn()}
        />
      );
      const listTab = screen.getByRole('tab', { name: /List view/i });
      expect(listTab.getAttribute('aria-selected')).toBe('true');
      unmount();

      // 2. Desktop mount
      window.innerWidth = 1024;
      render(
        <AdminCalendar
          events={mockCalendarEvents}
          timezone="America/Santiago"
          onDatesSet={vi.fn()}
          onEventClick={vi.fn()}
          userSelectedView={null}
          onViewChange={vi.fn()}
        />
      );
      const weekTab = screen.getByRole('tab', { name: /Week view/i });
      expect(weekTab.getAttribute('aria-selected')).toBe('true');
    });

    it('strictly preserves manual user selection against subsequent window resize', () => {
      const onViewChange = vi.fn();
      render(
        <AdminCalendar
          events={mockCalendarEvents}
          timezone="America/Santiago"
          onDatesSet={vi.fn()}
          onEventClick={vi.fn()}
          userSelectedView="timeGridDay"
          onViewChange={onViewChange}
        />
      );

      // User chose Day view.
      const dayTab = screen.getByRole('tab', { name: /Day view/i });
      expect(dayTab.getAttribute('aria-selected')).toBe('true');

      // Window resize to mobile width does not override it.
      window.innerWidth = 360;
      window.dispatchEvent(new Event('resize'));

      expect(dayTab.getAttribute('aria-selected')).toBe('true');
    });
  });

  describe('5. Textual Status Indicators (Non-Color-Only)', () => {
    it('ServicesPage renders explicit text labels for Active and Inactive items', async () => {
      const mockServicesList: adminApi.AdminServiceDetail[] = [
        {
          id: 's1',
          name: 'Servicio Activo',
          description: '',
          duration_minutes: 30,
          price_amount: 10000,
          is_active: true,
          sort_order: 0,
          created_at: '2026-08-01T00:00:00Z',
          updated_at: '2026-08-01T00:00:00Z',
        },
        {
          id: 's2',
          name: 'Servicio Antiguo',
          description: '',
          duration_minutes: 45,
          price_amount: 12000,
          is_active: false,
          sort_order: 1,
          created_at: '2026-08-01T00:00:00Z',
          updated_at: '2026-08-01T00:00:00Z',
        },
      ];

      vi.mocked(adminApi.getAdminServices).mockResolvedValue(mockServicesList);
      const queryClient = createTestQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <ServicesPage />
          </MemoryRouter>
        </QueryClientProvider>
      );

      expect(await screen.findByText('Servicio Activo')).toBeDefined();
      expect(screen.getByText('Activo')).toBeDefined();
      expect(screen.getByText('Inactivo')).toBeDefined();
    });

    it('ProvidersPage renders explicit text labels for Active and Inactive providers', async () => {
      const mockProvidersList = [
        { id: 'p1', name: 'Laura Gómez', is_active: true },
        { id: 'p2', name: 'Carlos Ruiz', is_active: false },
      ];

      vi.mocked(adminApi.getAdminProviders).mockResolvedValue(mockProvidersList);
      const queryClient = createTestQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <ProvidersPage />
          </MemoryRouter>
        </QueryClientProvider>
      );

      expect(await screen.findByText('Laura Gómez')).toBeDefined();
      expect(screen.getByText('Carlos Ruiz')).toBeDefined();
      expect(screen.getByText('Activo')).toBeDefined();
      expect(screen.getByText('Inactivo')).toBeDefined();
    });
  });
});
