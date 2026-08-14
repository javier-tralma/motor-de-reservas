import React, { useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../auth/useAuth';
import { getAdminBookingDetail, updateAdminBookingStatus, type AdminBookingDetail } from '../../lib/api/admin';
import { ApiError } from '../../lib/api/client';
import { adminQueryKeys } from '../../lib/api/queryKeys';
import { ConfirmModal } from '../../components/ConfirmModal';

export const BookingDetailPage: React.FC = () => {
  const { bookingId } = useParams<{ bookingId: string }>();
  const navigate = useNavigate();
  const { business, handleUnauthorized } = useAuth();
  const queryClient = useQueryClient();

  const [activeModal, setActiveModal] = useState<'completed' | 'no_show' | 'cancelled' | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const completeBtnRef = useRef<HTMLButtonElement>(null);
  const noShowBtnRef = useRef<HTMLButtonElement>(null);
  const cancelBtnRef = useRef<HTMLButtonElement>(null);

  // Fetch Booking Detail
  const {
    data: booking,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<AdminBookingDetail, ApiError>({
    queryKey: adminQueryKeys.bookingDetail(bookingId || ''),
    queryFn: ({ signal }) => getAdminBookingDetail(bookingId || '', signal),
    enabled: !!bookingId,
    retry: (_failureCount, err) => {
      if (err?.status === 401) {
        handleUnauthorized();
      }
      return false;
    },
  });

  // Mutation for Status Update
  const mutation = useMutation<AdminBookingDetail, ApiError, 'completed' | 'cancelled' | 'no_show'>({
    mutationFn: (newStatus) => updateAdminBookingStatus(bookingId || '', newStatus),
    onSuccess: () => {
      setActionError(null);
      setActiveModal(null);
      // Invalidate relevant queries using adminQueryKeys
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.bookingDetail(bookingId || '') });
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.dashboard() });
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.bookingsList() });
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.calendarEventsRoot() });
      queryClient.invalidateQueries({ queryKey: ['public-availability'] });
    },
    onError: (err) => {
      if (err?.status === 401) {
        handleUnauthorized();
        return;
      }
      if (err?.status === 409 || err?.code === 'invalid_status_transition') {
        setActionError('Esta reserva ya fue procesada o se encuentra en un estado terminal.');
      } else {
        setActionError(err?.message || 'No fue posible actualizar el estado de la reserva.');
      }
    },
  });

  const formatPrice = (amount: number): string => {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDateTime = (isoStr?: string): string => {
    if (!isoStr) return '—';
    try {
      const date = new Date(isoStr);
      const timeZone = business?.timezone || 'America/Santiago';
      return new Intl.DateTimeFormat('es-CL', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
        timeZone,
      }).format(date);
    } catch {
      return isoStr;
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case 'confirmed':
        return { label: 'Confirmada', className: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' };
      case 'completed':
        return { label: 'Completada', className: 'bg-blue-500/10 text-blue-400 border-blue-500/30' };
      case 'cancelled':
        return { label: 'Cancelada', className: 'bg-rose-500/10 text-rose-400 border-rose-500/30' };
      case 'no_show':
        return { label: 'Inasistencia', className: 'bg-amber-500/10 text-amber-400 border-amber-500/30' };
      default:
        return { label: status || 'Desconocido', className: 'bg-slate-800 text-slate-400 border-slate-700' };
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-4xl" aria-busy="true" aria-live="polite">
        <div className="h-8 w-48 bg-slate-900 rounded-lg animate-pulse" />
        <div className="h-64 bg-slate-900 border border-slate-800 rounded-2xl animate-pulse" />
      </div>
    );
  }

  if (isError || !booking) {
    return (
      <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 max-w-xl">
        <h3 className="text-base font-bold text-rose-200 mb-2">Reserva no encontrada</h3>
        <p className="text-sm text-rose-300 mb-4">
          {error?.message || 'La reserva solicitada no existe o pertenece a otro negocio.'}
        </p>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate('/admin/reservas')}
            className="px-4 py-2 bg-slate-800 text-slate-200 rounded-xl text-sm font-medium hover:bg-slate-700"
          >
            Volver a Reservas
          </button>
          <button
            type="button"
            onClick={() => refetch()}
            className="px-4 py-2 bg-rose-500 text-white rounded-xl text-sm font-medium hover:bg-rose-600"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  const badge = getStatusBadge(booking.status);
  const isConfirmed = booking.status === 'confirmed';

  return (
    <div className="space-y-8 max-w-4xl">
      {/* Navigation & Header */}
      <div>
        <button
          type="button"
          onClick={() => navigate('/admin/reservas')}
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors mb-4"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span>Volver al listado</span>
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl sm:text-3xl font-bold text-white font-serif tracking-tight">
                Reserva {booking.public_reference}
              </h1>
              <span className={`px-3 py-1 rounded-full border text-xs font-semibold ${badge.className}`}>
                {badge.label}
              </span>
            </div>
            <p className="text-slate-400 text-sm mt-1 capitalize">{formatDateTime(booking.starts_at)}</p>
          </div>
        </div>
      </div>

      {/* Error alert */}
      {actionError && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center justify-between">
          <span>{actionError}</span>
          <button type="button" onClick={() => setActionError(null)} className="text-rose-400 font-bold hover:text-white">
            ×
          </button>
        </div>
      )}

      {/* Main Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Customer PII Card */}
        <div className="md:col-span-2 p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-6">
          <h2 className="text-lg font-bold text-white font-serif border-b border-slate-800 pb-3">
            Información del Cliente
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <span className="text-xs text-slate-500 font-medium">Nombre completo</span>
              <p className="text-base font-semibold text-white mt-0.5">{booking.customer_name}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500 font-medium">Correo electrónico</span>
              <p className="text-base font-semibold text-white mt-0.5">{booking.customer_email}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500 font-medium">Teléfono de contacto</span>
              <p className="text-base font-semibold text-white mt-0.5">{booking.customer_phone}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500 font-medium">Origen de reserva</span>
              <p className="text-base font-semibold text-white mt-0.5 capitalize">{booking.source}</p>
            </div>
          </div>

          {booking.customer_notes && (
            <div className="pt-2 border-t border-slate-800/60">
              <span className="text-xs text-slate-500 font-medium">Notas adicionales</span>
              <p className="text-sm text-slate-300 mt-1 whitespace-pre-wrap">{booking.customer_notes}</p>
            </div>
          )}
        </div>

        {/* Service & Provider Snapshots */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-6">
          <h2 className="text-lg font-bold text-white font-serif border-b border-slate-800 pb-3">
            Detalle del Servicio
          </h2>

          <div className="space-y-4 text-sm">
            <div>
              <span className="text-xs text-slate-500 font-medium">Servicio</span>
              <p className="text-base font-bold text-white mt-0.5">{booking.service_name_snapshot}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500 font-medium">Profesional</span>
              <p className="text-base font-semibold text-slate-200 mt-0.5">{booking.provider_name_snapshot}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500 font-medium">Duración</span>
              <p className="text-base font-semibold text-slate-200 mt-0.5">{booking.duration_minutes_snapshot} minutos</p>
            </div>
            <div>
              <span className="text-xs text-slate-500 font-medium">Precio</span>
              <p className="text-lg font-bold text-emerald-400 mt-0.5">{formatPrice(booking.price_amount_snapshot)}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons for Confirmed Bookings */}
      {isConfirmed && (
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-white">Acciones Operativas</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Actualiza el estado de la cita al concluir la atención o en caso de inasistencia/cancelación.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
            {/* Complete Button */}
            <button
              ref={completeBtnRef}
              type="button"
              onClick={() => setActiveModal('completed')}
              disabled={mutation.isPending}
              className="flex-1 sm:flex-initial px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
            >
              Marcar Completada
            </button>

            {/* No-Show Button */}
            <button
              ref={noShowBtnRef}
              type="button"
              onClick={() => setActiveModal('no_show')}
              disabled={mutation.isPending}
              className="flex-1 sm:flex-initial px-4 py-2.5 rounded-xl bg-amber-600/90 hover:bg-amber-700 text-white font-medium text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 transition-colors"
            >
              Marcar Inasistencia
            </button>

            {/* Cancel Button */}
            <button
              ref={cancelBtnRef}
              type="button"
              onClick={() => setActiveModal('cancelled')}
              disabled={mutation.isPending}
              className="flex-1 sm:flex-initial px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-medium text-sm focus:outline-none focus:ring-2 focus:ring-rose-500 transition-colors"
            >
              Cancelar Reserva
            </button>
          </div>
        </div>
      )}

      {/* Confirmation Modals */}
      <ConfirmModal
        isOpen={activeModal === 'completed'}
        title="Confirmar Atención Completada"
        description="¿Confirmas que el cliente asistió y el servicio fue completado satisfactoriamente?"
        confirmText="Completar Atención"
        cancelText="Volver"
        isDestructive={false}
        isLoading={mutation.isPending}
        onConfirm={() => mutation.mutateAsync('completed')}
        onClose={() => setActiveModal(null)}
        triggerRef={completeBtnRef}
      />

      <ConfirmModal
        isOpen={activeModal === 'no_show'}
        title="Confirmar Inasistencia de Cliente"
        description="¿Marcar como inasistencia? El cliente no se presentó a su cita. El slot permanecerá reservado históricamente."
        confirmText="Confirmar Inasistencia"
        cancelText="Volver"
        isDestructive={true}
        isLoading={mutation.isPending}
        onConfirm={() => mutation.mutateAsync('no_show')}
        onClose={() => setActiveModal(null)}
        triggerRef={noShowBtnRef}
      />

      <ConfirmModal
        isOpen={activeModal === 'cancelled'}
        title="Confirmar Cancelación de Reserva"
        description="¿Estás seguro de cancelar esta reserva? Esta acción liberará el horario inmediatamente para que otros clientes puedan reservar."
        confirmText="Cancelar Reserva"
        cancelText="Volver"
        isDestructive={true}
        isLoading={mutation.isPending}
        onConfirm={() => mutation.mutateAsync('cancelled')}
        onClose={() => setActiveModal(null)}
        triggerRef={cancelBtnRef}
      />
    </div>
  );
};
