import React, { useCallback, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../auth/useAuth';
import { createAdminTimeOff, type AdminTimeOffCreate } from '../../lib/api/admin';
import { ApiError } from '../../lib/api/client';
import { adminQueryKeys, publicQueryKeys } from '../../lib/api/queryKeys';
import { getInitialLocalDate } from '../../lib/utils/availabilityUtils';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { Button } from '../../components/Button';

interface CreateTimeOffModalProps {
  providerId: string;
  providerName: string;
  isOpen: boolean;
  onClose: () => void;
  timezone?: string;
  triggerRef?: React.RefObject<HTMLElement | null>;
  onSuccess?: () => void;
}

export const CreateTimeOffModal: React.FC<CreateTimeOffModalProps> = ({
  providerId,
  providerName,
  isOpen,
  onClose,
  timezone,
  triggerRef,
  onSuccess,
}) => {
  const queryClient = useQueryClient();
  const { business, handleUnauthorized } = useAuth();
  const effectiveTimezone = timezone || business?.timezone || 'America/Santiago';

  const modalRef = useRef<HTMLDivElement | null>(null);
  const startInputRef = useRef<HTMLInputElement | null>(null);

  const [startDate, setStartDate] = useState(() => getInitialLocalDate(effectiveTimezone));
  const [startTime, setStartTime] = useState('09:00');
  const [endDate, setEndDate] = useState(() => getInitialLocalDate(effectiveTimezone));
  const [endTime, setEndTime] = useState('18:00');
  const [reason, setReason] = useState('');
  const [clientError, setClientError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  const handleClose = useCallback(() => {
    setClientError(null);
    setServerError(null);
    onClose();
  }, [onClose]);

  const createMutation = useMutation({
    mutationFn: (data: AdminTimeOffCreate) => createAdminTimeOff(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.providerTimeOffs(providerId) });
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.calendarEventsRoot() });
      queryClient.invalidateQueries({ queryKey: publicQueryKeys.availabilityRoot() });
      onSuccess?.();
      handleClose();
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.status === 401) {
        handleUnauthorized();
        return;
      }
      const msg = err instanceof Error ? err.message : 'Error al registrar el bloqueo.';
      setServerError(msg);
    },
  });

  const isSubmitting = createMutation.isPending;

  useFocusTrap(modalRef, isOpen, {
    onEscape: handleClose,
    disableEscape: isSubmitting,
    initialFocusRef: startInputRef,
    returnFocusRef: triggerRef,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setClientError(null);
    setServerError(null);

    if (!startDate || !startTime || !endDate || !endTime) {
      setClientError('Todos los campos de fecha y hora son obligatorios.');
      return;
    }

    const startsAtLocal = `${startDate}T${startTime.length === 5 ? startTime + ':00' : startTime}`;
    const endsAtLocal = `${endDate}T${endTime.length === 5 ? endTime + ':00' : endTime}`;

    if (startsAtLocal >= endsAtLocal) {
      setClientError('La fecha y hora de término debe ser posterior a la de inicio.');
      return;
    }

    createMutation.mutate({
      provider_id: providerId,
      starts_at_local: startsAtLocal,
      ends_at_local: endsAtLocal,
      reason: reason.trim() || null,
    });
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-time-off-modal-title"
      ref={modalRef}
    >
      <div className="bg-[#fffdf9] border border-[#dfe4df] w-full max-w-md rounded-2xl shadow-2xl p-6 space-y-5 relative text-left">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#dfe4df] pb-3">
          <div>
            <h2 id="create-time-off-modal-title" className="text-lg font-bold text-[#1f2a27]">
              Registrar Bloqueo o Ausencia
            </h2>
            <p className="text-xs text-[#66736e] mt-0.5">Profesional: {providerName}</p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            disabled={isSubmitting}
            className="p-1 rounded-lg text-[#66736e] hover:text-[#1f2a27] hover:bg-[#f0eee9] transition-colors disabled:opacity-50"
            aria-label="Cerrar modal"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Error Alerts */}
        {clientError && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900" role="alert">
            {clientError}
          </div>
        )}
        {serverError && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-900" role="alert">
            {serverError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Start Section */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-[#66736e]">
              Inicio del bloqueo
            </label>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="date"
                ref={startInputRef}
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                disabled={isSubmitting}
                required
                aria-label="Fecha de inicio"
                className="w-full bg-[#fffdf9] border border-[#dfe4df] rounded-xl px-3 py-2 text-sm text-[#1f2a27] focus:outline-none focus:ring-2 focus:ring-[#176b5b] disabled:opacity-50"
              />
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                disabled={isSubmitting}
                required
                aria-label="Hora de inicio"
                className="w-full bg-[#fffdf9] border border-[#dfe4df] rounded-xl px-3 py-2 text-sm text-[#1f2a27] focus:outline-none focus:ring-2 focus:ring-[#176b5b] disabled:opacity-50"
              />
            </div>
          </div>

          {/* End Section */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-[#66736e]">
              Término del bloqueo
            </label>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                disabled={isSubmitting}
                required
                aria-label="Fecha de término"
                className="w-full bg-[#fffdf9] border border-[#dfe4df] rounded-xl px-3 py-2 text-sm text-[#1f2a27] focus:outline-none focus:ring-2 focus:ring-[#176b5b] disabled:opacity-50"
              />
              <input
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                disabled={isSubmitting}
                required
                aria-label="Hora de término"
                className="w-full bg-[#fffdf9] border border-[#dfe4df] rounded-xl px-3 py-2 text-sm text-[#1f2a27] focus:outline-none focus:ring-2 focus:ring-[#176b5b] disabled:opacity-50"
              />
            </div>
          </div>

          {/* Reason */}
          <div className="space-y-1.5">
            <label htmlFor="time-off-reason" className="block text-xs font-semibold uppercase tracking-wider text-[#66736e]">
              Motivo <span className="text-[#66736e] font-normal lowercase">(opcional)</span>
            </label>
            <input
              id="time-off-reason"
              type="text"
              maxLength={240}
              placeholder="Ej. Vacaciones, Capacitación, Consulta médica"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={isSubmitting}
              className="w-full bg-[#fffdf9] border border-[#dfe4df] rounded-xl px-3 py-2 text-sm text-[#1f2a27] placeholder-[#66736e]/60 focus:outline-none focus:ring-2 focus:ring-[#176b5b] disabled:opacity-50"
            />
          </div>

          {/* Footer actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#dfe4df]">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isSubmitting}
              className="text-xs px-4 py-2"
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              isLoading={isSubmitting}
              disabled={isSubmitting}
              className="text-xs px-4 py-2"
            >
              Registrar Bloqueo
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
