import React, { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getAdminProviderServices,
  getAdminServices,
  replaceAdminProviderServices,
} from '../../lib/api/admin';
import type { AdminServiceDetail } from '../../lib/api/admin';
import { adminQueryKeys } from '../../lib/api/queryKeys';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { Button } from '../../components/Button';

interface AssignServicesModalProps {
  providerId: string;
  providerName: string;
  isOpen: boolean;
  onClose: () => void;
  triggerElement?: HTMLButtonElement | null;
}

export const AssignServicesModal: React.FC<AssignServicesModalProps> = ({
  providerId,
  providerName,
  isOpen,
  onClose,
  triggerElement,
}) => {
  const queryClient = useQueryClient();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [serverError, setServerError] = useState<string | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const modalRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(triggerElement || null);

  useEffect(() => {
    if (triggerElement) {
      triggerRef.current = triggerElement;
    }
  }, [triggerElement]);

  // Query assigned provider services
  const {
    data: providerServicesData,
    isLoading: isLoadingAssigned,
    isError: isErrorAssigned,
    refetch: refetchAssigned,
  } = useQuery({
    queryKey: adminQueryKeys.providerServices(providerId),
    queryFn: ({ signal }) => getAdminProviderServices(providerId, signal),
    enabled: isOpen && !!providerId,
  });

  // Ref for tracking synced data identity
  const lastSyncedRef = useRef<string | null>(null);

  // Query all services in business
  const {
    data: allServices = [],
    isLoading: isLoadingAll,
    isError: isErrorAll,
    refetch: refetchAll,
  } = useQuery({
    queryKey: adminQueryKeys.services(),
    queryFn: ({ signal }) => getAdminServices(signal),
    enabled: isOpen,
  });

  const replaceMutation = useMutation({
    mutationFn: (serviceIds: string[]) => replaceAdminProviderServices(providerId, serviceIds),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: adminQueryKeys.providerServices(providerId),
      });
    },
  });

  const isSubmitting = replaceMutation.isPending;

  const handleClose = () => {
    if (isSubmitting) return;
    setServerError(null);
    onClose();
  };

  useFocusTrap(modalRef, isOpen, {
    onEscape: handleClose,
    disableEscape: isSubmitting,
    initialFocusRef: closeButtonRef,
    returnFocusRef: triggerRef,
  });

  const syncKey = providerServicesData
    ? providerId + ':' + providerServicesData.service_ids.join(',')
    : null;

  useEffect(() => {
    if (syncKey && syncKey !== lastSyncedRef.current && !isSubmitting) {
      lastSyncedRef.current = syncKey;
      setSelectedIds(providerServicesData!.service_ids);
    }
  }, [syncKey, isSubmitting, providerServicesData]);

  const handleSave = async () => {
    setServerError(null);
    try {
      await replaceMutation.mutateAsync(selectedIds);
      handleClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al actualizar las asignaciones de servicios';
      setServerError(message);
    }
  };

  const toggleService = (serviceId: string) => {
    if (isSubmitting) return;
    setSelectedIds((prev) =>
      prev.includes(serviceId) ? prev.filter((id) => id !== serviceId) : [...prev, serviceId]
    );
  };

  if (!isOpen) return null;

  const isLoading = isLoadingAssigned || isLoadingAll;
  const isError = isErrorAssigned || isErrorAll;

  return (
    <div
      className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="assign-services-modal-title"
      ref={modalRef}
    >
      <div className="bg-[#fffdf9] border border-[#dfe4df] w-full max-w-lg rounded-2xl shadow-2xl p-6 space-y-5 relative text-left">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#dfe4df] pb-3">
          <div>
            <h2 id="assign-services-modal-title" className="text-lg font-bold text-[#1f2a27]">
              Asignar Servicios
            </h2>
            <p className="text-xs text-[#66736e] mt-0.5">Profesional: {providerName}</p>
          </div>
          <button
            type="button"
            ref={closeButtonRef}
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

        {serverError && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-900" role="alert">
            {serverError}
          </div>
        )}

        {/* Content */}
        {isLoading ? (
          <div className="space-y-3 py-4">
            {[1, 2, 3].map((n) => (
              <div key={n} className="h-10 bg-[#e4e1da] rounded-xl animate-pulse" />
            ))}
          </div>
        ) : isError ? (
          <div className="p-6 bg-rose-50 border border-rose-200 rounded-2xl text-center space-y-3">
            <p className="text-sm text-rose-900">Error al cargar la información de asignaciones.</p>
            <button
              type="button"
              onClick={() => {
                refetchAssigned();
                refetchAll();
              }}
              className="px-4 py-2 bg-[#176b5b] hover:bg-[#125548] text-white rounded-xl text-xs font-semibold"
            >
              Reintentar
            </button>
          </div>
        ) : allServices.length === 0 ? (
          <div className="p-6 text-center text-[#66736e] text-sm">
            No existen servicios creados en el sistema.
          </div>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {allServices.map((service: AdminServiceDetail) => {
              const isChecked = selectedIds.includes(service.id);
              return (
                <label
                  key={service.id}
                  className={`flex items-center justify-between p-3 rounded-xl border transition-colors cursor-pointer ${
                    isChecked
                      ? 'bg-[#176b5b]/10 border-[#176b5b]/30 text-[#1f2a27]'
                      : 'bg-[#fffdf9] border-[#dfe4df] text-[#1f2a27] hover:border-[#ccd3cc]'
                  } ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => toggleService(service.id)}
                      disabled={isSubmitting}
                      className="w-4 h-4 rounded border-[#dfe4df] text-[#176b5b] focus:ring-[#176b5b]"
                    />
                    <span className="text-sm font-medium">{service.name}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    {!service.is_active && (
                      <span className="px-2 py-0.5 bg-stone-100 text-stone-600 border border-stone-200 rounded-full text-[10px] font-semibold uppercase">
                        Inactivo
                      </span>
                    )}
                    <span className="text-xs text-[#66736e]">{service.duration_minutes} min</span>
                  </div>
                </label>
              );
            })}
          </div>
        )}

        {/* Footer */}
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
            type="button"
            onClick={handleSave}
            isLoading={isSubmitting}
            disabled={isSubmitting || isLoading || isError}
            className="text-xs px-4 py-2"
          >
            Guardar Asignaciones
          </Button>
        </div>
      </div>
    </div>
  );
};
