import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../auth/useAuth';
import { getAdminDashboard, type BookingAgendaItem, type DashboardData } from '../../lib/api/admin';
import { ApiError } from '../../lib/api/client';
import { adminQueryKeys } from '../../lib/api/queryKeys';

export const DashboardPage: React.FC = () => {
  const { user, business, handleUnauthorized } = useAuth();

  const {
    data: dashboard,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery<DashboardData, ApiError>({
    queryKey: adminQueryKeys.dashboard(),
    queryFn: getAdminDashboard,
    staleTime: 30000,

    retry: (_failureCount, err) => {
      if (err?.status === 401) {
        handleUnauthorized();
      }
      return false;
    },

  });

  // Calculate greeting
  const getGreeting = (): string => {
    const timeZone = business?.timezone || 'America/Santiago';
    const hour = parseInt(
      new Intl.DateTimeFormat('en-US', {
        hour: 'numeric',
        hour12: false,
        timeZone,
      }).format(new Date()),
      10
    );
    if (hour >= 6 && hour < 12) return 'Buenos días';
    if (hour >= 12 && hour < 20) return 'Buenas tardes';
    return 'Buenas noches';
  };

  // Format date in es-CL
  const formatCivilDate = (dateStr?: string, tzStr?: string): string => {
    if (!dateStr) return '';
    try {
      const [year, month, day] = dateStr.split('-').map(Number);
      const date = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
      return new Intl.DateTimeFormat('es-CL', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric',
        timeZone: tzStr || business?.timezone || 'America/Santiago',
      }).format(date);
    } catch {
      return dateStr;
    }
  };

  // Format time range
  const formatTimeRange = (startsAtStr: string, endsAtStr: string, tzStr?: string): string => {
    try {
      const start = new Date(startsAtStr);
      const end = new Date(endsAtStr);
      const timeZone = tzStr || business?.timezone || 'America/Santiago';

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

  // Status Badge config
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

  if (isLoading) {
    return (
      <div className="space-y-6" aria-busy="true" aria-live="polite">
        {/* Header Skeleton */}
        <div className="animate-pulse space-y-2">
          <div className="h-8 w-64 bg-[#e4e1da] rounded-lg" />
          <div className="h-4 w-48 bg-[#e4e1da]/60 rounded-lg" />
        </div>

        {/* Stats Skeleton */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-24 bg-[#fffdf9] border border-[#dfe4df] rounded-2xl animate-pulse" />
          ))}
        </div>

        {/* Agenda Skeleton */}
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-[#fffdf9] border border-[#dfe4df] rounded-2xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 max-w-xl">
        <h2 className="text-lg font-bold text-rose-950 mb-2">Error al cargar la agenda</h2>
        <p className="text-sm text-rose-800 mb-4">
          {error?.message || 'No fue posible consultar los datos del dashboard.'}
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="px-4 py-2 bg-[#b33a3a] text-white rounded-xl text-sm font-medium hover:bg-rose-800 focus:outline-none focus:ring-2 focus:ring-rose-500 disabled:opacity-50"
        >
          {isFetching ? 'Reintentando...' : 'Reintentar'}
        </button>
      </div>
    );
  }

  const summary = dashboard?.summary;
  const nextBooking = dashboard?.next_booking;
  const agenda = dashboard?.agenda || [];

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Welcome Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-[#1f2a27] tracking-tight">
          {getGreeting()}, {user?.display_name || 'Administrador'}.
        </h1>
        <p className="text-[#66736e] text-sm mt-1 capitalize">
          {formatCivilDate(dashboard?.date, dashboard?.timezone)}
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <div className="p-5 rounded-2xl bg-[#fffdf9] border border-[#dfe4df] flex flex-col justify-between">
          <span className="text-xs font-medium text-[#66736e]">Total hoy</span>
          <span className="text-3xl font-bold text-[#1f2a27] mt-2">{summary?.total ?? 0}</span>
        </div>
        <div className="p-5 rounded-2xl bg-[#fffdf9] border border-[#dfe4df] flex flex-col justify-between">
          <span className="text-xs font-medium text-[#176b5b]">Confirmadas</span>
          <span className="text-3xl font-bold text-[#176b5b] mt-2">{summary?.confirmed_remaining ?? 0}</span>
        </div>
        <div className="p-5 rounded-2xl bg-[#fffdf9] border border-[#dfe4df] flex flex-col justify-between">
          <span className="text-xs font-medium text-blue-700">Completadas</span>
          <span className="text-3xl font-bold text-blue-700 mt-2">{summary?.completed ?? 0}</span>
        </div>
        <div className="p-5 rounded-2xl bg-[#fffdf9] border border-[#dfe4df] flex flex-col justify-between">
          <span className="text-xs font-medium text-stone-600">Canceladas</span>
          <span className="text-3xl font-bold text-stone-700 mt-2">{summary?.cancelled ?? 0}</span>
        </div>
        <div className="p-5 rounded-2xl bg-[#fffdf9] border border-[#dfe4df] flex flex-col justify-between">
          <span className="text-xs font-medium text-amber-800">Inasistencias</span>
          <span className="text-3xl font-bold text-amber-800 mt-2">{summary?.no_show ?? 0}</span>
        </div>
      </div>

      {/* Next Booking Highlight */}
      {nextBooking && (
        <section aria-labelledby="next-booking-heading" className="p-6 rounded-2xl bg-[#fffdf9] border border-[#dfe4df] shadow-xs">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2 h-2 rounded-full bg-[#176b5b]" />
            <h2 id="next-booking-heading" className="text-xs font-semibold text-[#176b5b] uppercase tracking-wider">
              Próxima reserva
            </h2>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <p className="text-xl font-bold text-[#1f2a27]">{nextBooking.customer_name}</p>
              <p className="text-sm text-[#66736e] mt-1">
                {nextBooking.service_name} • con <span className="text-[#1f2a27] font-medium">{nextBooking.provider_name}</span>
              </p>
            </div>
            <div className="text-left sm:text-right">
              <span className="inline-block text-lg font-bold text-[#176b5b] font-mono">
                {formatTimeRange(nextBooking.starts_at, nextBooking.ends_at, dashboard?.timezone)}
              </span>
            </div>
          </div>
        </section>
      )}

      {/* Agenda Section */}
      <section aria-labelledby="agenda-heading" className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 id="agenda-heading" className="text-lg font-bold text-[#1f2a27]">
            Agenda del día
          </h2>
          <span className="text-xs text-[#66736e]">
            {agenda.length} {agenda.length === 1 ? 'cita' : 'citas'}
          </span>
        </div>

        {agenda.length === 0 ? (
          <div className="p-12 text-center rounded-2xl bg-[#fffdf9] border border-[#dfe4df]">
            <svg
              className="w-12 h-12 mx-auto text-[#66736e] mb-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <p className="text-[#1f2a27] font-medium text-base">No hay reservas programadas para hoy</p>
            <p className="text-[#66736e] text-xs mt-1">
              Las nuevas reservas realizadas por clientes aparecerán aquí automáticamente.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {agenda.map((item: BookingAgendaItem) => {
              const badge = getStatusBadge(item.status);
              return (
                <div
                  key={item.id}
                  className="p-5 rounded-2xl bg-[#fffdf9] border border-[#dfe4df] hover:border-[#ccd3cc] transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xs"
                >
                  <div className="flex items-start sm:items-center gap-4">
                    <div className="px-3 py-1.5 rounded-xl bg-[#f0eee9] border border-[#dfe4df] text-[#1f2a27] font-mono text-sm font-semibold shrink-0">
                      {formatTimeRange(item.starts_at, item.ends_at, dashboard?.timezone)}
                    </div>
                    <div>
                      <p className="text-base font-bold text-[#1f2a27]">{item.customer_name}</p>
                      <p className="text-xs text-[#66736e] mt-0.5">
                        {item.service_name} — <span className="text-[#1f2a27]">{item.provider_name}</span>
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between sm:justify-end gap-3 shrink-0">
                    <span
                      className={`px-3 py-1 rounded-full border text-xs font-semibold ${badge.className}`}
                    >
                      {badge.label}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
};
