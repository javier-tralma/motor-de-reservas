import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { getAdminServices, getAdminProviders, createAdminBooking } from '../../lib/api/admin';
import { adminQueryKeys, publicQueryKeys } from '../../lib/api/queryKeys';
import { fetchPublicAvailability, type SlotPublic } from '../../lib/api/availability';
import { IdempotencyManager, type SemanticPayload } from '../../lib/idempotency';
import { ApiError } from '../../lib/api/client';
import { Button } from '../../components/Button';
import { TextField } from '../../components/TextField';
import { TextArea } from '../../components/TextArea';
import { RadioCard } from '../../components/RadioCard';
import { InlineAlert } from '../../components/InlineAlert';
import type { AdminBookingCreateRequest } from '../../lib/api/admin';
import { useAuth } from '../auth/useAuth';

export function NewBookingPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { business } = useAuth();
  const idempotencyManagerRef = useRef<IdempotencyManager>(new IdempotencyManager());
  const conflictAlertRef = useRef<HTMLDivElement | null>(null);

  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [serviceId, setServiceId] = useState<string>('');
  const [providerId, setProviderId] = useState<string>('');
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [selectedSlot, setSelectedSlot] = useState<SlotPublic | null>(null);
  const [slotConflictError, setSlotConflictError] = useState<string | null>(null);
  
  const [customerData, setCustomerData] = useState({
    name: '',
    email: '',
    phone: '',
    notes: '',
  });

  // Queries
  const { data: services, isLoading: loadingServices, isError: errorServices, refetch: refetchServices } = useQuery({
    queryKey: adminQueryKeys.services(),
    queryFn: ({ signal }) => getAdminServices(signal),
  });

  const { data: providers, isLoading: loadingProviders, isError: errorProviders, refetch: refetchProviders } = useQuery({
    queryKey: adminQueryKeys.providersForService(serviceId),
    queryFn: ({ signal }) => getAdminProviders(serviceId, signal),
    enabled: !!serviceId,
  });

  const { data: availability, isLoading: loadingAvailability, isError: errorAvailability, refetch: refetchAvailability } = useQuery({
    queryKey: publicQueryKeys.availability(serviceId, selectedDate, providerId),
    queryFn: ({ signal }) => fetchPublicAvailability({ service_id: serviceId, date: selectedDate, provider_id: providerId, signal }),
    enabled: !!serviceId && !!providerId && !!selectedDate,
  });

  const createMutation = useMutation({
    mutationFn: (payload: AdminBookingCreateRequest) => createAdminBooking(payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.bookingsRoot() });
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.calendarEventsRoot() });
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.dashboard() });
      queryClient.invalidateQueries({ queryKey: publicQueryKeys.availabilityRoot() });
      navigate(`/admin/reservas/${data.id}`, { replace: true });
    },
    onError: async (error: Error | ApiError) => {
      const err = error as ApiError;
      if (err?.code === 'slot_unavailable') {
        await queryClient.invalidateQueries({ queryKey: publicQueryKeys.availabilityRoot() });
        setSlotConflictError('El horario seleccionado ya no está disponible. Por favor, elige otro.');
        setStep(3);
        setSelectedSlot(null);
      } else if (err?.code === 'idempotency_conflict') {
        // do not invalidate key, just keep form
      }
    },
  });

  // Focus conflict alert on step 3 if conflict occurred
  useEffect(() => {
    if (step === 3 && slotConflictError) {
      conflictAlertRef.current?.focus();
    }
  }, [step, slotConflictError]);

  const activeServices = services?.filter(s => s.is_active) || [];
  const activeProviders = providers?.filter(p => p.is_active) || [];

  const handleNext = () => {
    if (step < 4) setStep((s) => (s + 1) as 1 | 2 | 3 | 4);
  };
  const handleBack = () => {
    if (step > 1) setStep((s) => (s - 1) as 1 | 2 | 3 | 4);
  };

  const handleCreate = () => {
    if (!serviceId || !providerId || !selectedSlot) return;

    const payload: SemanticPayload = {
      service_id: serviceId,
      provider_id: providerId,
      starts_at: selectedSlot.starts_at,
      customer_name: customerData.name,
      customer_email: customerData.email,
      customer_phone: customerData.phone,
      customer_notes: customerData.notes,
    };

    const client_request_id = idempotencyManagerRef.current.getIdempotencyKey(payload);

    createMutation.mutate({
      ...payload,
      provider_id: providerId,
      client_request_id,
    } as AdminBookingCreateRequest);
  };

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Nueva Reserva</h1>
        <p className="text-gray-500 mt-1">Creación manual de reserva desde administración</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        {step === 1 && (
          <div>
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              Seleccionar Servicio
            </h2>
            {loadingServices ? (
              <p>Cargando servicios...</p>
            ) : errorServices ? (
              <div role="alert" className="text-red-600 space-y-2">
                <p>Error al cargar los servicios.</p>
                <Button onClick={() => refetchServices()} variant="secondary">Reintentar</Button>
              </div>
            ) : activeServices.length === 0 ? (
              <p className="text-gray-500">No hay servicios activos disponibles.</p>
            ) : (
              <div className="space-y-3">
                {activeServices.map((s) => (
                  <RadioCard
                    id={`service-${s.id}`}
                    name="service"
                    value={s.id}
                    key={s.id}
                    title={s.name}
                    description={`${s.duration_minutes} min • $${s.price_amount}`}
                    checked={serviceId === s.id}
                    onChange={() => {
                      setServiceId(s.id);
                      setProviderId('');
                      setSelectedSlot(null);
                      setSlotConflictError(null);
                      handleNext();
                    }}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {step === 2 && (
          <div>
            <button onClick={handleBack} className="text-indigo-600 text-sm mb-4">← Volver</button>
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              Seleccionar Profesional
            </h2>
            {loadingProviders ? (
              <p>Cargando profesionales...</p>
            ) : errorProviders ? (
              <div role="alert" className="text-red-600 space-y-2">
                <p>Error al cargar los profesionales.</p>
                <Button onClick={() => refetchProviders()} variant="secondary">Reintentar</Button>
              </div>
            ) : activeProviders.length === 0 ? (
              <p className="text-gray-500">No hay profesionales activos para este servicio.</p>
            ) : (
              <div className="space-y-3">
                {activeProviders.map((p) => (
                  <RadioCard
                    id={`provider-${p.id}`}
                    name="provider"
                    value={p.id}
                    key={p.id}
                    title={p.name}
                    checked={providerId === p.id}
                    onChange={() => {
                      setProviderId(p.id);
                      setSelectedSlot(null);
                      setSlotConflictError(null);
                      handleNext();
                    }}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {step === 3 && (
          <div>
            <button onClick={handleBack} className="text-indigo-600 text-sm mb-4">← Volver</button>
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              Fecha y Hora
            </h2>

            {slotConflictError && (
              <div className="mb-4">
                <InlineAlert
                  ref={conflictAlertRef}
                  type="error"
                  isUrgent={true}
                  tabIndex={-1}
                  title="Horario no disponible"
                  message={slotConflictError}
                />
              </div>
            )}
            
            <div className="mb-6">
              <label htmlFor="booking-date" className="block text-sm font-medium text-gray-700 mb-1">Fecha</label>
              <input 
                id="booking-date"
                type="date"
                value={selectedDate}
                onChange={(e) => {
                  setSelectedDate(e.target.value);
                  setSelectedSlot(null);
                  setSlotConflictError(null);
                }}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              />
            </div>

            {selectedDate && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Horarios disponibles</h3>
                {loadingAvailability ? (
                  <p>Cargando horarios...</p>
                ) : errorAvailability ? (
                  <div role="alert" className="text-red-600 space-y-2">
                    <p>Error al cargar los horarios disponibles.</p>
                    <Button onClick={() => refetchAvailability()} variant="secondary">Reintentar</Button>
                  </div>
                ) : availability?.slots.length === 0 ? (
                  <p className="text-gray-500">No hay horarios disponibles.</p>
                ) : (
                  <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                    {availability?.slots.map((slot: SlotPublic) => (
                      <button
                        key={slot.starts_at}
                        onClick={() => {
                          setSelectedSlot(slot);
                          setSlotConflictError(null);
                        }}
                        className={`p-2 text-sm rounded-md border focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                          selectedSlot?.starts_at === slot.starts_at
                            ? 'bg-indigo-600 text-white border-indigo-600'
                            : 'bg-white text-gray-700 border-gray-300 hover:border-indigo-500'
                        }`}
                      >
                        {new Intl.DateTimeFormat('es-CL', {
                          hour: '2-digit',
                          minute: '2-digit',
                          hour12: false,
                          timeZone: business?.timezone || 'America/Santiago',
                        }).format(new Date(slot.starts_at))}
                      </button>
                    ))}
                  </div>
                )}
                
                <div className="mt-6">
                  <Button 
                    onClick={handleNext} 
                    disabled={!selectedSlot}
                    className="w-full"
                  >
                    Continuar
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {step === 4 && (
          <div>
            <button onClick={handleBack} className="text-indigo-600 text-sm mb-4">← Volver</button>
            <h2 className="text-lg font-semibold mb-4">Datos del Cliente</h2>
            
            <div className="space-y-4">
              <TextField
                id="customer-name"
                label="Nombre completo *"
                value={customerData.name}
                onChange={(e) => setCustomerData({ ...customerData, name: e.target.value })}
                required
              />
              <TextField
                id="customer-email"
                label="Correo electrónico *"
                type="email"
                value={customerData.email}
                onChange={(e) => setCustomerData({ ...customerData, email: e.target.value })}
                required
              />
              <TextField
                id="customer-phone"
                label="Teléfono *"
                type="tel"
                value={customerData.phone}
                onChange={(e) => setCustomerData({ ...customerData, phone: e.target.value })}
                required
              />
              <TextArea
                id="customer-notes"
                label="Notas"
                value={customerData.notes}
                onChange={(e) => setCustomerData({ ...customerData, notes: e.target.value })}
              />
            </div>

            {createMutation.isError && (createMutation.error as ApiError)?.code !== 'slot_unavailable' && (
              <div className="mt-4">
                <InlineAlert
                  type="error"
                  isUrgent={true}
                  title="Error al crear la reserva"
                  message={(createMutation.error as ApiError)?.message || 'Error al procesar la reserva'}
                />
              </div>
            )}

            <div className="mt-6">
              <Button 
                onClick={handleCreate}
                isLoading={createMutation.isPending}
                disabled={!customerData.name || !customerData.email || !customerData.phone || createMutation.isPending}
                className="w-full"
              >
                Confirmar Reserva
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
