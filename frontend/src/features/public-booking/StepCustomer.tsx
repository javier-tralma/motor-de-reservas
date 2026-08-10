import React, { useState, useRef } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import type { ServicePublic, ProviderPublic } from '../../lib/api/services';
import type { SlotPublic } from '../../lib/api/availability';
import { createPublicBooking, type BookingCreatePayload } from '../../lib/api/bookings';
import { ApiError } from '../../lib/api/client';
import { createNormalizedPayload, type SemanticPayload } from '../../lib/idempotency';
import { TextField } from '../../components/TextField';
import { TextArea } from '../../components/TextArea';
import { Button } from '../../components/Button';
import { InlineAlert } from '../../components/InlineAlert';
import { formatCLP } from '../../lib/format/currency';
import { formatLocalDate, formatTimeRange } from '../../lib/format/date';

const customerSchema = z.object({
  customer_name: z
    .string()
    .transform((val) => val.trim())
    .pipe(z.string().min(1, 'Ingresa tu nombre completo').max(120, 'Máximo 120 caracteres')),
  customer_email: z.string().email('Ingresa un correo electrónico válido'),
  customer_phone: z
    .string()
    .transform((val) => val.trim())
    .pipe(z.string().min(1, 'Ingresa tu número de teléfono').max(32, 'Máximo 32 caracteres')),
  customer_notes: z.string().max(500, 'Máximo 500 caracteres').optional(),
});

export type CustomerFormInput = z.infer<typeof customerSchema>;

interface StepCustomerProps {
  service: ServicePublic;
  provider: ProviderPublic | null;
  selectedDate: string;
  selectedSlot: SlotPublic;
  getClientRequestId: (payload: SemanticPayload) => string;
  initialCustomerData: {
    customer_name: string;
    customer_email: string;
    customer_phone: string;
    customer_notes?: string;
  };
  onBack: () => void;
  onSuccess: (publicReference: string) => void;
  onSlotConflict: (errorMessage: string) => void;
  onCustomerDataChange: (data: CustomerFormInput) => void;
  timeZone?: string;
}

export const StepCustomer: React.FC<StepCustomerProps> = ({
  service,
  provider,
  selectedDate,
  selectedSlot,
  getClientRequestId,
  initialCustomerData,
  onBack,
  onSuccess,
  onSlotConflict,
  onCustomerDataChange,
  timeZone = 'America/Santiago',
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const isSubmittingRef = useRef(false);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<CustomerFormInput>({
    resolver: zodResolver(customerSchema),
    defaultValues: {
      customer_name: initialCustomerData.customer_name || '',
      customer_email: initialCustomerData.customer_email || '',
      customer_phone: initialCustomerData.customer_phone || '',
      customer_notes: initialCustomerData.customer_notes || '',
    },
  });

  const notesValue = useWatch({ control, name: 'customer_notes' }) || '';

  const onSubmit = async (data: CustomerFormInput) => {
    if (isSubmittingRef.current) {
      return;
    }
    isSubmittingRef.current = true;
    setIsSubmitting(true);
    setSubmitError(null);
    onCustomerDataChange(data);

    try {
      const semanticPayload = createNormalizedPayload({
        service_id: service.id,
        provider_id: provider ? provider.id : null,
        starts_at: selectedSlot.starts_at,
        customer_name: data.customer_name,
        customer_email: data.customer_email,
        customer_phone: data.customer_phone,
        customer_notes: data.customer_notes || '',
      });

      const clientRequestId = getClientRequestId(semanticPayload);

      const payload: BookingCreatePayload = {
        ...semanticPayload,
        client_request_id: clientRequestId,
      };

      const result = await createPublicBooking(payload);
      onSuccess(result.public_reference);
    } catch (err) {
      isSubmittingRef.current = false;
      setIsSubmitting(false);

      if (err instanceof ApiError) {
        if (err.code === 'slot_unavailable') {
          onSlotConflict('Esa hora acaba de ser reservada. Actualizamos los horarios para que elijas otra.');
          return;
        }
        if (err.code === 'idempotency_conflict') {
          setSubmitError('Hubo una inconsistencia al procesar la reserva. Por favor intenta con una hora nueva.');
          return;
        }
        setSubmitError(err.message || 'Error al procesar la reserva.');
      } else {
        setSubmitError('Ocurrió un problema de conexión. Por favor reintenta.');
      }
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmittingRef.current) {
      return;
    }
    handleSubmit(onSubmit)(e);
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-xl sm:text-2xl font-bold text-[#1f2a27]">
          Ingresa tus datos de contacto
        </h2>
        <p className="text-sm text-[#66736e] mt-1">
          Completa tus datos para enviarte la confirmación de la cita.
        </p>
      </div>

      {submitError && (
        <InlineAlert
          type="error"
          title="No se pudo realizar la reserva"
          message={submitError}
        />
      )}

      {/* Summary Box */}
      <div className="bg-[#fffdf9] p-4 rounded-xl border border-[#dfe4df] flex flex-col gap-2">
        <h4 className="text-xs uppercase tracking-wider font-bold text-[#66736e]">
          Detalle de tu reserva
        </h4>
        <div className="flex justify-between items-start">
          <div>
            <span className="block font-semibold text-[#1f2a27] text-base">{service.name}</span>
            <span className="text-xs text-[#66736e]">
              {provider ? `Con ${provider.name}` : 'Cualquier profesional'} · {service.duration_minutes} min
            </span>
          </div>
          <span className="font-bold text-[#176b5b] text-base">
            {formatCLP(service.price_amount)}
          </span>
        </div>
        <div className="text-sm text-[#1f2a27] border-t border-[#dfe4df] pt-2 mt-1">
          <span className="capitalize">{formatLocalDate(selectedDate, timeZone)}</span> ·{' '}
          <span className="font-semibold">{formatTimeRange(selectedSlot.starts_at, selectedSlot.ends_at, timeZone)}</span>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleFormSubmit} className="flex flex-col gap-4">
        <TextField
          label="Nombre completo *"
          placeholder="Ej. Juan Pérez"
          error={errors.customer_name?.message}
          {...register('customer_name')}
        />

        <TextField
          type="email"
          label="Correo electrónico *"
          placeholder="ejemplo@correo.cl"
          error={errors.customer_email?.message}
          {...register('customer_email')}
        />

        <TextField
          type="tel"
          label="Teléfono de contacto *"
          placeholder="+56 9 1234 5678"
          error={errors.customer_phone?.message}
          {...register('customer_phone')}
        />

        <TextArea
          label="Nota o indicación especial (opcional)"
          placeholder="Escribe alguna indicación para el profesional..."
          maxLength={500}
          currentLength={notesValue.length}
          error={errors.customer_notes?.message}
          {...register('customer_notes')}
        />

        <div className="pt-4 flex justify-between items-center border-t border-[#dfe4df] mt-2">
          <Button variant="outline" type="button" onClick={onBack} disabled={isSubmitting}>
            Volver
          </Button>
          <Button type="submit" isLoading={isSubmitting} fullWidth className="sm:w-auto">
            Confirmar reserva
          </Button>
        </div>
      </form>
    </div>
  );
};
