import React, { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  createAdminService,
  getAdminServices,
  updateAdminService,
} from '../../lib/api/admin';
import type { AdminServiceDetail } from '../../lib/api/admin';
import { adminQueryKeys } from '../../lib/api/queryKeys';
import { useFocusTrap } from '../../hooks/useFocusTrap';

const serviceSchema = z.object({
  name: z.string().trim().min(1, 'El nombre es obligatorio').max(120, 'Máximo 120 caracteres'),
  description: z.string().max(1000, 'Máximo 1000 caracteres').optional(),
  duration_minutes: z.coerce.number().min(5, 'Mínimo 5 minutos').max(720, 'Máximo 720 minutos (12h)'),
  price_amount: z.coerce.number().min(0, 'El precio no puede ser negativo'),
  is_active: z.boolean(),
  sort_order: z.coerce.number().min(0),
});


type ServiceFormData = z.infer<typeof serviceSchema>;

export const ServicesPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'inactive'>('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingService, setEditingService] = useState<AdminServiceDetail | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const initialFocusRef = useRef<HTMLInputElement | null>(null);
  const modalRef = useRef<HTMLDivElement | null>(null);

  useFocusTrap(modalRef, isModalOpen);

  const {
    data: services = [],
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: adminQueryKeys.services(),
    queryFn: ({ signal }) => getAdminServices(signal),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting: isFormSubmitting },
  } = useForm<ServiceFormData>({
    resolver: zodResolver(serviceSchema),
    defaultValues: {
      name: '',
      description: '',
      duration_minutes: 30,
      price_amount: 10000,
      is_active: true,
      sort_order: 0,
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: ServiceFormData) => createAdminService(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.services() });
      closeModal();
    },
    onError: (err: Error) => {
      setServerError(err.message || 'Error al crear el servicio');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ServiceFormData }) =>
      updateAdminService(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.services() });
      closeModal();
    },
    onError: (err: Error) => {
      setServerError(err.message || 'Error al actualizar el servicio');
    },
  });

  const isSubmitting = createMutation.isPending || updateMutation.isPending || isFormSubmitting;

  const openCreateModal = (e: React.MouseEvent<HTMLButtonElement>) => {
    triggerRef.current = e.currentTarget;
    setEditingService(null);
    reset({
      name: '',
      description: '',
      duration_minutes: 30,
      price_amount: 10000,
      is_active: true,
      sort_order: 0,
    });
    setServerError(null);
    setIsModalOpen(true);
  };

  const openEditModal = (service: AdminServiceDetail, e: React.MouseEvent<HTMLButtonElement>) => {
    triggerRef.current = e.currentTarget;
    setEditingService(service);
    reset({
      name: service.name,
      description: service.description || '',
      duration_minutes: service.duration_minutes,
      price_amount: service.price_amount,
      is_active: service.is_active,
      sort_order: service.sort_order,
    });
    setServerError(null);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    if (isSubmitting) return;
    setIsModalOpen(false);
    setEditingService(null);
    setServerError(null);
    if (triggerRef.current) {
      triggerRef.current.focus();
    }
  };

  // Keyboard Escape listener & Focus Trap for Modal
  useEffect(() => {
    if (!isModalOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isSubmitting) {
        setIsModalOpen(false);
        setEditingService(null);
        setServerError(null);
        if (triggerRef.current) {
          triggerRef.current.focus();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    if (initialFocusRef.current) {
      initialFocusRef.current.focus();
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isModalOpen, isSubmitting]);


  const onSubmit = (formData: ServiceFormData) => {
    setServerError(null);
    if (editingService) {
      updateMutation.mutate({ id: editingService.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const filteredServices = services.filter((s) => {
    if (filterStatus === 'active') return s.is_active;
    if (filterStatus === 'inactive') return !s.is_active;
    return true;
  });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white font-serif">Catálogo de Servicios</h1>
          <p className="text-sm text-slate-400 mt-1">
            Gestiona los servicios ofrecidos por tu negocio y sus precios.
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
          Nuevo Servicio
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
          Todos ({services.length})
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
          Activos ({services.filter((s) => s.is_active).length})
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
          Inactivos ({services.filter((s) => !s.is_active).length})
        </button>
      </div>

      {/* Content State */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((n) => (
            <div key={n} className="p-5 bg-slate-900 border border-slate-800 rounded-2xl animate-pulse space-y-3">
              <div className="h-5 bg-slate-800 rounded w-3/4" />
              <div className="h-4 bg-slate-800 rounded w-1/2" />
              <div className="h-4 bg-slate-800 rounded w-1/4" />
            </div>
          ))}
        </div>
      ) : isError ? (
        <div className="p-6 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-center space-y-3">
          <p className="text-sm text-rose-300">Ocurrió un error al cargar el catálogo de servicios.</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-medium"
          >
            Reintentar
          </button>
        </div>
      ) : filteredServices.length === 0 ? (
        <div className="p-12 bg-slate-900/50 border border-slate-800 border-dashed rounded-2xl text-center space-y-3">
          <p className="text-slate-400 text-sm">No se encontraron servicios en esta categoría.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredServices.map((service) => (
            <div
              key={service.id}
              className={`p-5 bg-slate-900 border rounded-2xl flex flex-col justify-between transition-all ${
                service.is_active
                  ? 'border-slate-800 hover:border-slate-700'
                  : 'border-slate-800/60 opacity-60 bg-slate-950/40'
              }`}
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-base font-semibold text-white">{service.name}</h3>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                      service.is_active
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-slate-800 text-slate-400 border border-slate-700'
                    }`}
                  >
                    {service.is_active ? 'Activo' : 'Inactivo'}
                  </span>
                </div>
                {service.description && (
                  <p className="text-xs text-slate-400 line-clamp-2">{service.description}</p>
                )}
              </div>

              <div className="mt-4 pt-4 border-t border-slate-800/80 flex items-center justify-between">
                <div>
                  <span className="text-xs text-slate-500 block">
                    {service.duration_minutes} min
                  </span>
                  <span className="text-sm font-bold text-emerald-400">
                    {formatCurrency(service.price_amount)}
                  </span>
                </div>

                <button
                  type="button"
                  onClick={(e) => openEditModal(service, e)}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white rounded-lg text-xs font-medium transition-colors"
                >
                  Editar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal / Drawer for Create / Edit Service */}
      {isModalOpen && (
        <div
          className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="service-modal-title"
        >
          <div ref={modalRef} className="bg-slate-900 border border-slate-800 w-full max-w-lg rounded-2xl shadow-2xl p-6 space-y-5 relative">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 id="service-modal-title" className="text-lg font-bold text-white">
                {editingService ? 'Editar Servicio' : 'Nuevo Servicio'}
              </h2>
              <button
                type="button"
                onClick={closeModal}
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
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-300">
                {serverError}
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label htmlFor="service-name" className="block text-xs font-medium text-slate-300 mb-1">Nombre *</label>
                <input
                  id="service-name"
                  type="text"
                  {...register('name')}
                  ref={(e) => {
                    register('name').ref(e);
                    initialFocusRef.current = e;
                  }}
                  disabled={isSubmitting}
                  aria-invalid={!!errors.name}
                  aria-describedby={errors.name ? 'service-name-error' : undefined}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
                  placeholder="Ej: Corte de Cabello"
                />
                {errors.name && (
                  <span id="service-name-error" className="block text-xs text-rose-400 mt-1">{errors.name.message}</span>
                )}
              </div>

              <div>
                <label htmlFor="service-description" className="block text-xs font-medium text-slate-300 mb-1">Descripción</label>
                <textarea
                  id="service-description"
                  {...register('description')}
                  rows={2}
                  disabled={isSubmitting}
                  aria-invalid={!!errors.description}
                  aria-describedby={errors.description ? 'service-description-error' : undefined}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
                  placeholder="Detalles opcionales sobre el servicio"
                />
                {errors.description && (
                  <span id="service-description-error" className="block text-xs text-rose-400 mt-1">{errors.description.message}</span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="service-duration" className="block text-xs font-medium text-slate-300 mb-1">
                    Duración (min) *
                  </label>
                  <input
                    id="service-duration"
                    type="number"
                    step={5}
                    {...register('duration_minutes')}
                    disabled={isSubmitting}
                    aria-invalid={!!errors.duration_minutes}
                    aria-describedby={errors.duration_minutes ? 'service-duration-error' : undefined}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
                  />
                  {errors.duration_minutes && (
                    <span id="service-duration-error" className="block text-xs text-rose-400 mt-1">{errors.duration_minutes.message}</span>
                  )}
                </div>

                <div>
                  <label htmlFor="service-price" className="block text-xs font-medium text-slate-300 mb-1">
                    Precio (CLP) *
                  </label>
                  <input
                    id="service-price"
                    type="number"
                    step={500}
                    {...register('price_amount')}
                    disabled={isSubmitting}
                    aria-invalid={!!errors.price_amount}
                    aria-describedby={errors.price_amount ? 'service-price-error' : undefined}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
                  />
                  {errors.price_amount && (
                    <span id="service-price-error" className="block text-xs text-rose-400 mt-1">{errors.price_amount.message}</span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-1">
                <div>
                  <label htmlFor="service-sort-order" className="block text-xs font-medium text-slate-300 mb-1">Orden</label>
                  <input
                    id="service-sort-order"
                    type="number"
                    {...register('sort_order')}
                    disabled={isSubmitting}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
                  />
                </div>

                <div className="flex items-center pt-5">
                  <label htmlFor="service-is-active" className="flex items-center gap-2 text-xs font-medium text-slate-300 cursor-pointer">
                    <input
                      id="service-is-active"
                      type="checkbox"
                      {...register('is_active')}
                      disabled={isSubmitting}
                      className="w-4 h-4 rounded bg-slate-950 border-slate-800 text-emerald-500 focus:ring-emerald-500"
                    />
                    Servicio Activo
                  </label>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={closeModal}
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium transition-colors disabled:opacity-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold rounded-xl text-xs transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {isSubmitting ? 'Guardando...' : editingService ? 'Guardar Cambios' : 'Crear Servicio'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
