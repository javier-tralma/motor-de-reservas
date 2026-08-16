import React, { useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../auth/useAuth';
import {
  getAdminCalendarEvents,
  getAdminProviders,
  type AdminProviderListItem,
  type CalendarEventsData,
} from '../../lib/api/admin';
import { ApiError } from '../../lib/api/client';
import { adminQueryKeys } from '../../lib/api/queryKeys';
import { AdminCalendar } from './AdminCalendar';

export const AdminCalendarPage: React.FC = () => {
  const { business, handleUnauthorized } = useAuth();
  const navigate = useNavigate();

  const [selectedProviderId, setSelectedProviderId] = useState<string>('');
  const [userSelectedView, setUserSelectedView] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<{ start: string; end: string } | null>(null);

  const timezone = business?.timezone || 'America/Santiago';
  const isTimezoneReady = Boolean(business?.timezone);

  // Fetch providers for the filter dropdown
  const { data: providersResponse } = useQuery<AdminProviderListItem[], ApiError>({
    queryKey: adminQueryKeys.providers(),
    queryFn: ({ signal }) => getAdminProviders(undefined, signal),
    staleTime: 60000,
    retry: (_failureCount, err) => {
      if (err?.status === 401) {
        handleUnauthorized();
      }
      return false;
    },
  });

  const providers =
    (Array.isArray(providersResponse)
      ? providersResponse
      : (providersResponse as unknown as { data?: AdminProviderListItem[] })?.data) || [];

  // Fetch calendar events
  const {
    data: calendarData,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
  } = useQuery<CalendarEventsData, ApiError>({
    queryKey: adminQueryKeys.calendarEvents(
      dateRange?.start ?? '',
      dateRange?.end ?? '',
      selectedProviderId || undefined
    ),
    queryFn: ({ signal }) => {
      if (!dateRange) return Promise.reject(new Error('No date range'));
      return getAdminCalendarEvents(dateRange.start, dateRange.end, selectedProviderId || undefined, signal);
    },
    enabled: isTimezoneReady && Boolean(dateRange?.start) && Boolean(dateRange?.end),
    staleTime: 15000,
    retry: (_failureCount, err) => {
      if (err?.status === 401) {
        handleUnauthorized();
      }
      return false;
    },
  });

  React.useEffect(() => {
    if (error?.status === 401) {
      handleUnauthorized();
    }
  }, [error, handleUnauthorized]);

  const handleDatesSet = useCallback((start: string, end: string) => {
    setDateRange({ start, end });
  }, []);

  const handleEventClick = useCallback(
    (kind: string, id: string) => {
      if (kind === 'booking') {
        navigate(`/admin/reservas/${id}`);
      }
    },
    [navigate]
  );

  const handleViewChange = useCallback((viewName: string) => {
    setUserSelectedView(viewName);
  }, []);

  const isEmpty = !isLoading && !isError && calendarData && calendarData.events.length === 0;

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-[#1f2a27] tracking-tight">Calendario</h1>
          <p className="text-[#66736e] text-sm mt-1">
            Visualiza citas y bloqueos por profesional en vista semanal, diaria o lista.
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label htmlFor="filter-calendar-provider" className="block text-xs font-medium text-[#66736e] mb-1.5">
              Profesional
            </label>
            <select
              id="filter-calendar-provider"
              className="w-full sm:w-64 px-3 py-2 bg-[#fffdf9] border border-[#dfe4df] rounded-xl text-sm text-[#1f2a27] focus:outline-none focus:ring-2 focus:ring-[#176b5b]"
              value={selectedProviderId}
              onChange={(e) => setSelectedProviderId(e.target.value)}
            >
              <option value="">Todos los profesionales</option>
              {providers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} {!p.is_active ? '(Inactivo)' : ''}
                </option>
              ))}
            </select>
          </div>
          <Link
            to="/admin/reservas/nueva"
            className="inline-flex justify-center items-center px-4 py-2 rounded-xl text-sm font-semibold text-white bg-[#176b5b] hover:bg-[#125548] transition-colors focus:outline-none focus:ring-2 focus:ring-[#176b5b] min-h-[38px]"
          >
            Nueva Reserva
          </Link>
        </div>
      </div>

      {/* Main Calendar Card */}
      <div className="p-4 sm:p-6 rounded-2xl bg-[#fffdf9] border border-[#dfe4df] flex flex-col relative min-h-[700px] shadow-xs">
        {/* Loading Overlay */}
        {(isLoading || isFetching) && (
          <div
            role="status"
            aria-live="polite"
            aria-busy="true"
            data-testid="calendar-loading-overlay"
            className="absolute inset-0 bg-white/80 backdrop-blur-xs flex flex-col items-center justify-center z-20 rounded-2xl"
          >
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[#176b5b] mb-2"></div>
            <span className="text-[#1f2a27] text-sm font-medium">Actualizando calendario...</span>
          </div>
        )}

        {/* Inline Error State */}
        {isError && error?.status !== 401 && (
          <div
            role="alert"
            className="p-6 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 mb-4"
          >
            <h3 className="text-base font-bold text-rose-950 mb-2">Error al cargar el calendario</h3>
            <p className="text-sm text-rose-800 mb-4">{error?.message || 'No fue posible conectar con el servidor.'}</p>
            <button
              type="button"
              onClick={() => refetch()}
              disabled={isFetching}
              className="px-4 py-2 bg-[#b33a3a] text-white rounded-xl text-sm font-medium hover:bg-rose-800 focus:outline-none focus:ring-2 focus:ring-rose-500 cursor-pointer"
            >
              {isFetching ? 'Reintentando...' : 'Reintentar'}
            </button>
          </div>
        )}

        {/* Explicit Empty State Banner */}
        {isEmpty && (
          <div
            role="status"
            className="p-4 mb-4 rounded-xl bg-[#f0eee9] border border-[#dfe4df] flex items-center gap-3 text-[#1f2a27] text-sm"
          >
            <svg
              className="w-5 h-5 text-[#66736e] shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            <span>No hay eventos registrados para el período y profesional seleccionados.</span>
          </div>
        )}

        {/* Calendar Body (Mounted only when timezone is available) */}
        <div className="flex-1 min-h-[600px]">
          {isTimezoneReady ? (
            <AdminCalendar
              events={calendarData?.events || []}
              timezone={timezone}
              onDatesSet={handleDatesSet}
              onEventClick={handleEventClick}
              userSelectedView={userSelectedView}
              onViewChange={handleViewChange}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-[#66736e] text-sm" aria-busy="true">
              Cargando configuración del negocio...
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
