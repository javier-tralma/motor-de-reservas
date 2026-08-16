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
    queryFn: ({ signal }) => getAdminProviders(undefined, signal),
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

  const formatBookingDate = (startsAtStr: string): string => {
    try {
      const start = new Date(startsAtStr);
      const timeZone = business?.timezone || 'America/Santiago';
      return new Intl.DateTimeFormat('es-CL', {
        dateStyle: 'short',
        timeZone,
      }).format(start);
    } catch {
      return startsAtStr;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'confirmed':
        return { label: 'Confirmada', className: 'bg-[#176b5b]/10 text-[#176b5b] border-[#176b5b]/30' };
      case 'completed':
        return { label: 'Completada', className: 'bg-blue-50 text-blue-700 border-blue-200' };
      case 'cancelled':
        return { label: 'Cancelada', className: 'bg-stone-100 text-stone-600 border-stone-200' };
      case 'no_show':
        return { label: 'Inasistencia', className: 'bg-amber-50 text-amber-800 border-amber-200' };
      default:
        return { label: status, className: 'bg-stone-100 text-stone-600 border-stone-200' };
    }
  };

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-[#1f2a27] tracking-tight">
            Gestión de Reservas
          </h1>
          <p className="text-[#66736e] text-sm mt-1">
            Consulta, filtra y gestiona el estado operativo de las citas.
          </p>
        </div>
        <div className="flex-shrink-0">
          <Link
            to="/admin/reservas/nueva"
            className="inline-flex items-center justify-center px-4 py-2 bg-[#176b5b] hover:bg-[#125548] text-white font-semibold rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-[#176b5b] min-h-[44px]"
          >
            Nueva Reserva
          </Link>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-4 rounded-2xl bg-[#fffdf9] border border-[#dfe4df] grid grid-cols-1 sm:grid-cols-3 gap-4 shadow-xs">
        {/* Date Filter */}
        <div>
          <label htmlFor="filter-date" className="block text-xs font-medium text-[#66736e] mb-1.5">
            Fecha
          </label>
          <input
            id="filter-date"
            type="date"
            value={dateParam}
            onChange={(e) => handleFilterChange('date', e.target.value)}
            className="w-full px-3 py-2 bg-[#fffdf9] border border-[#dfe4df] rounded-xl text-sm text-[#1f2a27] focus:outline-none focus:ring-2 focus:ring-[#176b5b]"
          />
        </div>

        {/* Status Filter */}
        <div>
          <label htmlFor="filter-status" className="block text-xs font-medium text-[#66736e] mb-1.5">
            Estado
          </label>
          <select
            id="filter-status"
            value={statusParam}
            onChange={(e) => handleFilterChange('status', e.target.value)}
            className="w-full px-3 py-2 bg-[#fffdf9] border border-[#dfe4df] rounded-xl text-sm text-[#1f2a27] focus:outline-none focus:ring-2 focus:ring-[#176b5b]"
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
          <label htmlFor="filter-provider" className="block text-xs font-medium text-[#66736e] mb-1.5">
            Profesional
          </label>
          <select
            id="filter-provider"
            value={providerParam}
            onChange={(e) => handleFilterChange('provider_id', e.target.value)}
            className="w-full px-3 py-2 bg-[#fffdf9] border border-[#dfe4df] rounded-xl text-sm text-[#1f2a27] focus:outline-none focus:ring-2 focus:ring-[#176b5b]"
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
            <div key={i} className="h-20 bg-[#fffdf9] border border-[#dfe4df] rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : isError ? (
        <div className="p-6 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900">
          <h3 className="text-base font-bold text-rose-950 mb-2">Error al cargar las reservas</h3>
          <p className="text-sm text-rose-800 mb-4">{error?.message || 'No fue posible conectar con el servidor.'}</p>
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="px-4 py-2 bg-[#b33a3a] text-white rounded-xl text-sm font-medium hover:bg-rose-800 focus:outline-none focus:ring-2 focus:ring-rose-500"
          >
            {isFetching ? 'Reintentando...' : 'Reintentar'}
          </button>
        </div>
      ) : bookings?.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-[#fffdf9] border border-[#dfe4df]">
          <svg className="w-12 h-12 mx-auto text-[#66736e] mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p className="text-[#1f2a27] font-medium text-base">No hay reservas para los filtros seleccionados</p>
          <p className="text-[#66736e] text-xs mt-1">
            Intenta seleccionar otra fecha, profesional o limpiar los filtros.
          </p>
        </div>
      ) : (
        <>
          {/* Desktop Table View */}
          <div className="hidden md:block overflow-x-auto rounded-2xl border border-[#dfe4df] bg-[#fffdf9] shadow-xs">
            <table className="w-full text-left border-collapse text-sm">
              <thead className="border-b border-[#dfe4df] text-xs uppercase tracking-wider text-[#66736e] font-semibold bg-[#f0eee9]">
                <tr>
                  <th scope="col" className="py-3.5 px-4">Fecha / Horario</th>
                  <th scope="col" className="py-3.5 px-4">Cliente</th>
                  <th scope="col" className="py-3.5 px-4">Servicio</th>
                  <th scope="col" className="py-3.5 px-4">Profesional</th>
                  <th scope="col" className="py-3.5 px-4">Estado</th>
                  <th scope="col" className="py-3.5 px-4 text-right">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#dfe4df] text-[#1f2a27]">
                {bookings?.map((item) => {
                  const badge = getStatusBadge(item.status);
                  return (
                    <tr key={item.id} className="hover:bg-[#f7f5f0] transition-colors">
                      <td className="py-3.5 px-4 font-medium whitespace-nowrap">
                        <div className="font-mono text-xs text-[#1f2a27]">
                          {formatTimeRange(item.starts_at, item.ends_at)}
                        </div>
                        <div className="text-xs text-[#66736e] mt-0.5">
                          {formatBookingDate(item.starts_at)}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-[#1f2a27]">
                        {item.customer_name}
                      </td>
                      <td className="py-3.5 px-4 text-[#66736e]">
                        {item.service_name_snapshot}
                      </td>
                      <td className="py-3.5 px-4 text-[#66736e]">
                        {item.provider_name_snapshot}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`inline-flex px-2.5 py-0.5 rounded-full border text-xs font-semibold ${badge.className}`}>
                          {badge.label}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Link
                          to={`/admin/reservas/${item.id}`}
                          className="inline-flex items-center text-xs font-semibold text-[#176b5b] hover:text-[#125548] underline focus:outline-none focus:ring-2 focus:ring-[#176b5b] rounded px-2 py-1"
                        >
                          Ver detalle
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Mobile Card List View */}
          <div className="block md:hidden space-y-3">
            {bookings?.map((item) => {
              const badge = getStatusBadge(item.status);
              return (
                <Link
                  key={item.id}
                  to={`/admin/reservas/${item.id}`}
                  className="p-4 rounded-2xl bg-[#fffdf9] border border-[#dfe4df] hover:border-[#ccd3cc] transition-colors flex flex-col gap-3 cursor-pointer group focus:outline-none focus:ring-2 focus:ring-[#176b5b] block text-left shadow-xs"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="px-2.5 py-1 rounded-xl bg-[#f0eee9] border border-[#dfe4df] text-[#1f2a27] font-mono text-xs font-semibold shrink-0">
                      {formatTimeRange(item.starts_at, item.ends_at)}
                    </div>
                    <span className={`px-2.5 py-0.5 rounded-full border text-xs font-semibold ${badge.className}`}>
                      {badge.label}
                    </span>
                  </div>

                  <div>
                    <p className="text-base font-bold text-[#1f2a27] group-hover:text-[#176b5b] transition-colors">
                      {item.customer_name}
                    </p>
                    <p className="text-xs text-[#66736e] mt-0.5">
                      {item.service_name_snapshot} — <span className="text-[#1f2a27]">{item.provider_name_snapshot}</span>
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};
