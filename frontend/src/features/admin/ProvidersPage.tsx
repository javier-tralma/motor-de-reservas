import React, { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  createAdminProvider,
  getAdminProviderDetail,
  getAdminProviders,
  updateAdminProvider,
} from '../../lib/api/admin';
import type { AdminProviderDetail, AdminProviderListItem } from '../../lib/api/admin';
import { adminQueryKeys } from '../../lib/api/queryKeys';
import { AssignServicesModal } from './AssignServicesModal';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { Button } from '../../components/Button';

const PHONE_REGEX = /^[0-9+() -]{7,32}$/;

const providerSchema = z.object({
  name: z.string().trim().min(1, 'El nombre es obligatorio').max(120, 'Máximo 120 caracteres'),
  email: z
    .string()
    .trim()
    .email('Email inválido')
    .or(z.literal(''))
    .optional()
    .nullable(),
  phone: z
    .string()
    .trim()
    .refine((val) => !val || PHONE_REGEX.test(val), 'Formato telefónico inválido (7 a 32 caracteres)')
    .optional()
    .nullable(),
  bio: z.string().max(1000, 'Máximo 1000 caracteres').optional(),
  is_active: z.boolean(),
  sort_order: z.coerce.number().min(0),
});

type ProviderFormData = z.infer<typeof providerSchema>;

export const ProvidersPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'inactive'>('all');
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [editingProviderId, setEditingProviderId] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  // Assign Services Modal state
  const [assignModalProvider, setAssignModalProvider] = useState<{ id: string; name: string } | null>(null);

  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const initialFocusRef = useRef<HTMLInputElement | null>(null);
  const modalRef = useRef<HTMLDivElement | null>(null);
  const [assignTriggerEl, setAssignTriggerEl] = useState<HTMLButtonElement | null>(null);

  // Minimal list query
  const {
    data: providers = [],
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: adminQueryKeys.providers(),
    queryFn: ({ signal }) => getAdminProviders(undefined, signal),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting: isFormSubmitting },
  } = useForm<ProviderFormData>({
    resolver: zodResolver(providerSchema),
    defaultValues: {
      name: '',
      email: '',
      phone: '',
      bio: '',
      is_active: true,
      sort_order: 0,
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: ProviderFormData) => createAdminProvider(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.providers() });
      closeFormModal();
    },
    onError: (err: Error) => {
      setServerError(err.message || 'Error al crear el profesional');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ProviderFormData }) =>
      updateAdminProvider(id, data),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.providers() });
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.providerDetail(updated.id) });
      closeFormModal();
    },
    onError: (err: Error) => {
      setServerError(err.message || 'Error al actualizar el profesional');
    },
  });

  const isSubmitting = createMutation.isPending || updateMutation.isPending || isFormSubmitting;

  const openCreateModal = (e: React.MouseEvent<HTMLButtonElement>) => {
    triggerRef.current = e.currentTarget;
    setEditingProviderId(null);
    reset({
      name: '',
      email: '',
      phone: '',
      bio: '',
      is_active: true,
      sort_order: 0,
    });
    setServerError(null);
    setIsFormModalOpen(true);
  };

  const openEditModal = async (provider: AdminProviderListItem, e: React.MouseEvent<HTMLButtonElement>) => {
    triggerRef.current = e.currentTarget;
    setEditingProviderId(provider.id);
    setServerError(null);
    try {
      const detail: AdminProviderDetail = await getAdminProviderDetail(provider.id);
      reset({
        name: detail.name,
        email: detail.email || '',
        phone: detail.phone || '',
        bio: detail.bio || '',
        is_active: detail.is_active,
        sort_order: detail.sort_order,
      });
      setIsFormModalOpen(true);
    } catch {
      setServerError('Error al cargar el detalle del profesional');
    }
  };

  const closeFormModal = () => {
    if (isSubmitting) return;
    setIsFormModalOpen(false);
    setEditingProviderId(null);
    setServerError(null);
  };

  useFocusTrap(modalRef, isFormModalOpen, {
    onEscape: closeFormModal,
    disableEscape: isSubmitting,
    initialFocusRef,
    returnFocusRef: triggerRef,
  });

  const onSubmit = (formData: ProviderFormData) => {
    setServerError(null);
    // Normalize empty strings to null for email and phone
    const normalizedData = {
      ...formData,
      email: formData.email ? formData.email.trim() : null,
      phone: formData.phone ? formData.phone.trim() : null,
    };

    if (editingProviderId) {
      updateMutation.mutate({ id: editingProviderId, data: normalizedData });
    } else {
      createMutation.mutate(normalizedData);
    }
  };

  const filteredProviders = providers.filter((p) => {
    if (filterStatus === 'active') return p.is_active;
    if (filterStatus === 'inactive') return !s_isActive(p.is_active);
    return true;
  });

  function s_isActive(active: boolean) {
    return active;
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white font-serif">Profesionales</h1>
          <p className="text-sm text-slate-400 mt-1">
            Gestiona el equipo de trabajo y las asignaciones de servicios por profesional.
          </p>
        </div>
        <button
          type="button"
          onClick={openCreateModal}
          className="px-4 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold rounded-xl text-sm transition-colors shadow-lg shadow-emerald-500/10 flex items-center justify-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Nuevo Profesional
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          type="button"
          onClick={() => setFilterStatus('all')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            filterStatus === 'all'
              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          Todos ({providers.length})
        </button>
        <button
          type="button"
          onClick={() => setFilterStatus('active')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            filterStatus === 'active'
              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          Activos ({providers.filter((p) => p.is_active).length})
        </button>
        <button
          type="button"
          onClick={() => setFilterStatus('inactive')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            filterStatus === 'inactive'
              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          Inactivos ({providers.filter((p) => !p.is_active).length})
        </button>
      </div>

      {/* Content State */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((n) => (
            <div key={n} className="p-5 bg-slate-900 border border-slate-800 rounded-2xl animate-pulse space-y-3">
              <div className="h-5 bg-slate-800 rounded w-3/4" />
              <div className="h-4 bg-slate-800 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : isError ? (
        <div className="p-6 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-center space-y-3">
          <p className="text-sm text-rose-300">Ocurrió un error al cargar la lista de profesionales.</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-medium"
          >
            Reintentar
          </button>
        </div>
      ) : filteredProviders.length === 0 ? (
        <div className="p-12 bg-slate-900/50 border border-slate-800 border-dashed rounded-2xl text-center space-y-3">
          <p className="text-slate-400 text-sm">No se encontraron profesionales en esta categoría.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProviders.map((provider) => (
            <div
              key={provider.id}
              className={`p-5 bg-slate-900 border rounded-2xl flex flex-col justify-between transition-all ${
                provider.is_active
                  ? 'border-slate-800 hover:border-slate-700'
                  : 'border-slate-800/60 opacity-60 bg-slate-950/40'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold text-base">
                    {provider.name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-white">{provider.name}</h3>
                  </div>
                </div>
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                    provider.is_active
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-slate-800 text-slate-400 border border-slate-700'
                  }`}
                >
                  {provider.is_active ? 'Activo' : 'Inactivo'}
                </span>
              </div>

              <div className="mt-5 pt-4 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={(e) => {
                      setAssignTriggerEl(e.currentTarget);
                      setAssignModalProvider({ id: provider.id, name: provider.name });
                    }}
                    className="px-2.5 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded-lg text-xs font-medium transition-colors"
                  >
                    Servicios
                  </button>

                  <Link
                    to={`/admin/profesionales/${provider.id}/disponibilidad`}
                    className="px-2.5 py-1.5 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20 rounded-lg text-xs font-medium transition-colors inline-flex items-center"
                  >
                    Disponibilidad
                  </Link>
                </div>

                <button
                  type="button"
                  onClick={(e) => openEditModal(provider, e)}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white rounded-lg text-xs font-medium transition-colors"
                >
                  Editar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Form Modal for Create / Edit Provider */}
      {isFormModalOpen && (
        <div
          className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="provider-modal-title"
        >
          <div ref={modalRef} className="bg-slate-900 border border-slate-800 w-full max-w-lg rounded-2xl shadow-2xl p-6 space-y-5 relative">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 id="provider-modal-title" className="text-lg font-bold text-white">
                {editingProviderId ? 'Editar Profesional' : 'Nuevo Profesional'}
              </h2>
              <button
                type="button"
                onClick={closeFormModal}
                disabled={isSubmitting}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors disabled:opacity-50"
                aria-label="Cerrar modal"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {serverError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-300" role="alert">
                {serverError}
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label htmlFor="provider-name" className="block text-xs font-medium text-slate-300 mb-1">Nombre *</label>
                <input
                  id="provider-name"
                  type="text"
                  {...register('name')}
                  ref={(e) => {
                    register('name').ref(e);
                    initialFocusRef.current = e;
                  }}
                  disabled={isSubmitting}
                  aria-invalid={!!errors.name}
                  aria-describedby={errors.name ? 'provider-name-error' : undefined}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
                  placeholder="Ej: Camila Rojas"
                />
                {errors.name && (
                  <span id="provider-name-error" className="block text-xs text-rose-400 mt-1">{errors.name.message}</span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="provider-email" className="block text-xs font-medium text-slate-300 mb-1">Email</label>
                  <input
                    id="provider-email"
                    type="text"
                    {...register('email')}
                    disabled={isSubmitting}
                    aria-invalid={!!errors.email}
                    aria-describedby={errors.email ? 'provider-email-error' : undefined}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
                    placeholder="camila@ejemplo.cl"
                  />
                  {errors.email && (
                    <span id="provider-email-error" className="block text-xs text-rose-400 mt-1">{errors.email.message}</span>
                  )}
                </div>

                <div>
                  <label htmlFor="provider-phone" className="block text-xs font-medium text-slate-300 mb-1">Teléfono</label>
                  <input
                    id="provider-phone"
                    type="text"
                    {...register('phone')}
                    disabled={isSubmitting}
                    aria-invalid={!!errors.phone}
                    aria-describedby={errors.phone ? 'provider-phone-error' : undefined}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
                    placeholder="+56912345678"
                  />
                  {errors.phone && (
                    <span id="provider-phone-error" className="block text-xs text-rose-400 mt-1">{errors.phone.message}</span>
                  )}
                </div>
              </div>

              <div>
                <label htmlFor="provider-bio" className="block text-xs font-medium text-slate-300 mb-1">Biografía</label>
                <textarea
                  id="provider-bio"
                  {...register('bio')}
                  rows={2}
                  disabled={isSubmitting}
                  aria-invalid={!!errors.bio}
                  aria-describedby={errors.bio ? 'provider-bio-error' : undefined}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
                  placeholder="Especialidad o experiencia..."
                />
                {errors.bio && (
                  <span id="provider-bio-error" className="block text-xs text-rose-400 mt-1">{errors.bio.message}</span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4 pt-1">
                <div>
                  <label htmlFor="provider-sort-order" className="block text-xs font-medium text-slate-300 mb-1">Orden</label>
                  <input
                    id="provider-sort-order"
                    type="number"
                    {...register('sort_order')}
                    disabled={isSubmitting}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
                  />
                </div>

                <div className="flex items-center pt-5">
                  <label htmlFor="provider-is-active" className="flex items-center gap-2 text-xs font-medium text-slate-300 cursor-pointer">
                    <input
                      id="provider-is-active"
                      type="checkbox"
                      {...register('is_active')}
                      disabled={isSubmitting}
                      className="w-4 h-4 rounded bg-slate-950 border-slate-800 text-emerald-500 focus:ring-emerald-500"
                    />
                    Profesional Activo
                  </label>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                <Button
                  type="button"
                  variant="outline"
                  onClick={closeFormModal}
                  disabled={isSubmitting}
                  className="text-xs px-4 py-2"
                >
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  isLoading={isSubmitting}
                  disabled={isSubmitting}
                  className="text-xs px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold"
                >
                  {editingProviderId ? 'Guardar Cambios' : 'Crear Profesional'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Assign Services Modal */}
      {assignModalProvider && (
        <AssignServicesModal
          providerId={assignModalProvider.id}
          providerName={assignModalProvider.name}
          isOpen={true}
          onClose={() => setAssignModalProvider(null)}
          triggerElement={assignTriggerEl}
        />
      )}
    </div>
  );
};
