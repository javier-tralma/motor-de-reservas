import React from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../auth/useAuth';
import { getAdminBookings, getAdminProviders, type AdminBookingListItem, type AdminProviderListItem } from '../../lib/api/admin';
import { ApiError } from '../../lib/api/client';
import { adminQueryKeys } from '../../lib/api/queryKeys';

export const BookingsListPage: React.FC = () => {
  const { business, handleUnauthorized } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  // Read URL params
  const dateParam = searchParams.get('date') || '';
  const statusParam = searchParams.get('status') || '';
  const providerParam = searchParams.get('provider_id') || '';

  const filters = {
    date: dateParam || undefined,
    status: statusParam || undefined,
    provider_id: providerParam || undefined,
  };

  // Fetch providers for filter dropdown
  const { data: providers } = useQuery<AdminProviderListItem[], ApiError>({
    queryKey: adminQueryKeys.providers(),
    queryFn: ({ signal }) => getAdminProviders(signal),
    staleTime: 60000,
  });

  // Fetch bookings list
  const {
    data: bookings,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery<AdminBookingListItem[], ApiError>({
    queryKey: adminQueryKeys.bookingsList(filters),
    queryFn: ({ signal }) => getAdminBookings({ ...filters, signal }),
    staleTime: 15000,
    retry: (_failureCount, err) => {
      if (err?.status === 401) {
        handleUnauthorized();
      }
      return false;
    },
  });

  const handleFilterChange = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setSearchParams(next);
  };

  const formatTimeRange = (startsAtStr: string, endsAtStr: string): string => {
    try {
      const start = new Date(startsAtStr);
      const end = new Date(endsAtStr);
      const timeZone = business?.timezone || 'America/Santiago';

      const timeFormatter = new Intl.DateTimeFormat('es-CL', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
        timeZone,
      });

      return `${timeFormatter.format(start)} - ${timeFormatter.format(end)}`;
    } catch {
      return `${startsAtStr} - ${endsAtStr}`;
    }
  };

  const getStatusBadge = (status: string) => {
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
        return { label: status, className: 'bg-slate-800 text-slate-400 border-slate-700' };
    }
  };

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white font-serif tracking-tight">
            Gestión de Reservas
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Consulta, filtra y gestiona el estado operativo de las citas.
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Date Filter */}
        <div>
          <label htmlFor="filter-date" className="block text-xs font-medium text-slate-400 mb-1.5">
            Fecha
          </label>
          <input
            id="filter-date"
            type="date"
            value={dateParam}
            onChange={(e) => handleFilterChange('date', e.target.value)}
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        {/* Status Filter */}
        <div>
          <label htmlFor="filter-status" className="block text-xs font-medium text-slate-400 mb-1.5">
            Estado
          </label>
          <select
            id="filter-status"
            value={statusParam}
            onChange={(e) => handleFilterChange('status', e.target.value)}
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="">Todos los estados</option>
            <option value="confirmed">Confirmadas</option>
            <option value="completed">Completadas</option>
            <option value="cancelled">Canceladas</option>
            <option value="no_show">Inasistencias</option>
          </select>
        </div>

        {/* Provider Filter */}
        <div>
          <label htmlFor="filter-provider" className="block text-xs font-medium text-slate-400 mb-1.5">
            Profesional
          </label>
          <select
            id="filter-provider"
            value={providerParam}
            onChange={(e) => handleFilterChange('provider_id', e.target.value)}
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="">Todos los profesionales</option>
            {providers?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} {!p.is_active ? '(Inactivo)' : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Content States */}
      {isLoading ? (
        <div className="space-y-3" aria-busy="true" aria-live="polite">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-20 bg-slate-900 border border-slate-800 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : isError ? (
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300">
          <h3 className="text-base font-bold text-rose-200 mb-2">Error al cargar las reservas</h3>
          <p className="text-sm text-rose-300 mb-4">{error?.message || 'No fue posible conectar con el servidor.'}</p>
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="px-4 py-2 bg-rose-500 text-white rounded-xl text-sm font-medium hover:bg-rose-600 focus:outline-none focus:ring-2 focus:ring-rose-500"
          >
            {isFetching ? 'Reintentando...' : 'Reintentar'}
          </button>
        </div>
      ) : bookings?.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-slate-900/50 border border-slate-800">
          <svg className="w-12 h-12 mx-auto text-slate-600 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p className="text-slate-300 font-medium text-base">No hay reservas para los filtros seleccionados</p>
          <p className="text-slate-500 text-xs mt-1">
            Intenta seleccionar otra fecha, profesional o limpiar los filtros.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {bookings?.map((item) => {
            const badge = getStatusBadge(item.status);
            return (
              <Link
                key={item.id}
                to={`/admin/reservas/${item.id}`}
                className="p-5 rounded-2xl bg-slate-900 border border-slate-800/80 hover:border-slate-700 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer group focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <div className="flex items-start sm:items-center gap-4">
                  <div className="px-3 py-1.5 rounded-xl bg-slate-800 border border-slate-700/50 text-slate-200 font-mono text-sm font-semibold shrink-0">
                    {formatTimeRange(item.starts_at, item.ends_at)}
                  </div>
                  <div>
                    <p className="text-base font-bold text-white group-hover:text-emerald-400 transition-colors">
                      {item.customer_name}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {item.service_name_snapshot} — <span className="text-slate-300">{item.provider_name_snapshot}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between sm:justify-end gap-3 shrink-0">
                  <span className={`px-3 py-1 rounded-full border text-xs font-semibold ${badge.className}`}>
                    {badge.label}
                  </span>
                  <svg className="w-5 h-5 text-slate-600 group-hover:text-slate-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
};

