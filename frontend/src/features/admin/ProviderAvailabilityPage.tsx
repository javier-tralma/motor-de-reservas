import React, { useMemo, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../auth/useAuth';
import {
  getAdminProviderDetail,
  getAdminProviderAvailabilityRules,
  replaceAdminProviderAvailabilityRules,
  getAdminTimeOffs,
  deleteAdminTimeOff,
  type AdminAvailabilityRuleItem,
  type AdminTimeOffDetail,
} from '../../lib/api/admin';
import { ApiError } from '../../lib/api/client';
import { adminQueryKeys, publicQueryKeys } from '../../lib/api/queryKeys';
import { normalizeIntervals } from '../../lib/utils/availabilityUtils';
import { CreateTimeOffModal } from './CreateTimeOffModal';
import { ConfirmModal } from '../../components/ConfirmModal';

interface DaySchedule {
  active: boolean;
  intervals: { start_time: string; end_time: string }[];
}

const DAYS = [
  { index: 0, label: 'Lunes' },
  { index: 1, label: 'Martes' },
  { index: 2, label: 'Miércoles' },
  { index: 3, label: 'Jueves' },
  { index: 4, label: 'Viernes' },
  { index: 5, label: 'Sábado' },
  { index: 6, label: 'Domingo' },
];

function buildScheduleFromRules(rules?: AdminAvailabilityRuleItem[]): Record<number, DaySchedule> {
  const initialSchedule: Record<number, DaySchedule> = {
    0: { active: false, intervals: [] },
    1: { active: false, intervals: [] },
    2: { active: false, intervals: [] },
    3: { active: false, intervals: [] },
    4: { active: false, intervals: [] },
    5: { active: false, intervals: [] },
    6: { active: false, intervals: [] },
  };

  if (rules) {
    for (const rule of rules) {
      const d = initialSchedule[rule.weekday];
      if (d) {
        d.active = true;
        d.intervals.push({
          start_time: rule.start_time.slice(0, 5),
          end_time: rule.end_time.slice(0, 5),
        });
      }
    }
  }
  return initialSchedule;
}

export const ProviderAvailabilityPage: React.FC = () => {
  const { providerId } = useParams<{ providerId: string }>();
  const navigate = useNavigate();
  const { business, handleUnauthorized } = useAuth();
  const queryClient = useQueryClient();

  const [userSchedule, setUserSchedule] = useState<Record<number, DaySchedule> | null>(null);
  const [scheduleSuccess, setScheduleSuccess] = useState<string | null>(null);
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const [timeOffDeleteError, setTimeOffDeleteError] = useState<string | null>(null);

  // Time off modal & delete confirmation
  const [isCreateTimeOffOpen, setIsCreateTimeOffOpen] = useState(false);
  const [timeOffToDelete, setTimeOffToDelete] = useState<AdminTimeOffDetail | null>(null);
  const addTimeOffBtnRef = useRef<HTMLButtonElement>(null);
  const deleteBtnRef = useRef<HTMLButtonElement>(null);

  // 1. Fetch Provider Details
  const {
    data: provider,
    isLoading: isLoadingProvider,
    isError: isErrorProvider,
    error: providerError,
    refetch: refetchProvider,
  } = useQuery({
    queryKey: adminQueryKeys.providerDetail(providerId || ''),
    queryFn: ({ signal }) => getAdminProviderDetail(providerId || '', signal),
    enabled: !!providerId,
    retry: (_cnt, err) => {
      if ((err as ApiError)?.status === 401) {
        handleUnauthorized();
      }
      return false;
    },
  });

  // 2. Fetch Availability Rules
  const {
    data: rulesData,
    isLoading: isLoadingRules,
    isError: isErrorRules,
    error: rulesError,
    refetch: refetchRules,
  } = useQuery({
    queryKey: adminQueryKeys.providerAvailabilityRules(providerId || ''),
    queryFn: ({ signal }) => getAdminProviderAvailabilityRules(providerId || '', signal),
    enabled: !!providerId,
    retry: (_cnt, err) => {
      if ((err as ApiError)?.status === 401) {
        handleUnauthorized();
      }
      return false;
    },
  });

  // 3. Fetch Time Offs
  const {
    data: timeOffs = [],
    isLoading: isLoadingTimeOffs,
    isError: isErrorTimeOffs,
    refetch: refetchTimeOffs,
  } = useQuery({
    queryKey: adminQueryKeys.providerTimeOffs(providerId || ''),
    queryFn: ({ signal }) => getAdminTimeOffs(providerId || '', signal),
    enabled: !!providerId,
    retry: (_cnt, err) => {
      if ((err as ApiError)?.status === 401) {
        handleUnauthorized();
      }
      return false;
    },
  });

  const schedule = useMemo(
    () => userSchedule ?? buildScheduleFromRules(rulesData),
    [userSchedule, rulesData]
  );
  const isScheduleDirty = userSchedule !== null;

  // Mutations
  const replaceRulesMutation = useMutation({
    mutationFn: (rules: AdminAvailabilityRuleItem[]) =>
      replaceAdminProviderAvailabilityRules(providerId || '', rules),
    onSuccess: (savedRules) => {
      queryClient.setQueryData(
        adminQueryKeys.providerAvailabilityRules(providerId || ''),
        savedRules
      );
      queryClient.invalidateQueries({
        queryKey: publicQueryKeys.availabilityRoot(),
      });
      setUserSchedule(null);
      setScheduleSuccess('Horarios guardados correctamente.');
      setScheduleError(null);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.status === 401) {
        handleUnauthorized();
        return;
      }
      const msg = err instanceof Error ? err.message : 'Error al guardar los horarios.';
      setScheduleError(msg);
      setScheduleSuccess(null);
    },
  });

  const deleteTimeOffMutation = useMutation({
    mutationFn: (id: string) => deleteAdminTimeOff(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.providerTimeOffs(providerId || '') });
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.calendarEventsRoot() });
      queryClient.invalidateQueries({ queryKey: publicQueryKeys.availabilityRoot() });
      setTimeOffToDelete(null);
      setTimeOffDeleteError(null);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.status === 401) {
        handleUnauthorized();
        return;
      }
      const msg = err instanceof Error ? err.message : 'Error al eliminar el bloqueo.';
      setTimeOffDeleteError(msg);
    },
  });

  // Toggle day active
  const handleToggleDay = (dayIndex: number) => {
    const current = schedule[dayIndex];
    const nextActive = !current.active;
    const nextIntervals =
      nextActive && current.intervals.length === 0
        ? [{ start_time: '09:00', end_time: '18:00' }]
        : current.intervals;

    setUserSchedule({
      ...schedule,
      [dayIndex]: {
        active: nextActive,
        intervals: nextIntervals,
      },
    });
    setScheduleSuccess(null);
  };

  // Add interval to a day
  const handleAddInterval = (dayIndex: number) => {
    const current = schedule[dayIndex];
    const intervals = [...current.intervals, { start_time: '14:00', end_time: '18:00' }];
    setUserSchedule({
      ...schedule,
      [dayIndex]: {
        active: true,
        intervals,
      },
    });
    setScheduleSuccess(null);
  };

  // Remove interval from a day
  const handleRemoveInterval = (dayIndex: number, intervalIndex: number) => {
    const current = schedule[dayIndex];
    const intervals = current.intervals.filter((_, i) => i !== intervalIndex);
    setUserSchedule({
      ...schedule,
      [dayIndex]: {
        active: intervals.length > 0,
        intervals,
      },
    });
    setScheduleSuccess(null);
  };

  // Update interval time
  const handleIntervalTimeChange = (
    dayIndex: number,
    intervalIndex: number,
    field: 'start_time' | 'end_time',
    value: string
  ) => {
    const current = schedule[dayIndex];
    const intervals = current.intervals.map((item, i) =>
      i === intervalIndex ? { ...item, [field]: value } : item
    );
    setUserSchedule({
      ...schedule,
      [dayIndex]: {
        ...current,
        intervals,
      },
    });
    setScheduleSuccess(null);
  };

  // Validate Schedule
  const getDayErrors = (dayIndex: number): string[] => {
    const day = schedule[dayIndex];
    if (!day.active || day.intervals.length === 0) return [];
    const errors: string[] = [];

    // Check invalid start >= end
    for (let i = 0; i < day.intervals.length; i++) {
      const { start_time, end_time } = day.intervals[i];
      if (start_time >= end_time) {
        errors.push(`Tramo ${i + 1}: La hora de inicio (${start_time}) debe ser anterior a la de término (${end_time}).`);
      }
    }

    // Check overlaps within day
    for (let i = 0; i < day.intervals.length; i++) {
      for (let j = i + 1; j < day.intervals.length; j++) {
        const a = day.intervals[i];
        const b = day.intervals[j];
        // Semi-open interval overlap check
        if (a.start_time < b.end_time && b.start_time < a.end_time) {
          errors.push(`Conflicto de solape entre tramos (${a.start_time}-${a.end_time} y ${b.start_time}-${b.end_time}).`);
        }
      }
    }

    return errors;
  };

  const hasScheduleErrors = DAYS.some((d) => getDayErrors(d.index).length > 0);

  const handleSaveSchedule = () => {
    if (hasScheduleErrors || !isScheduleDirty) return;

    const rawRules: AdminAvailabilityRuleItem[] = [];
    for (const d of DAYS) {
      const dayData = schedule[d.index];
      if (dayData.active) {
        for (const item of dayData.intervals) {
          rawRules.push({
            weekday: d.index,
            start_time: item.start_time,
            end_time: item.end_time,
          });
        }
      }
    }

    const normalized = normalizeIntervals(rawRules);
    replaceRulesMutation.mutate(normalized);
  };

  const formatDateTime = (isoStr?: string): string => {
    if (!isoStr) return '—';
    try {
      const date = new Date(isoStr);
      const timeZone = business?.timezone || 'America/Santiago';
      return new Intl.DateTimeFormat('es-CL', {
        dateStyle: 'medium',
        timeStyle: 'short',
        timeZone,
      }).format(date);
    } catch {
      return isoStr;
    }
  };

  if (isLoadingProvider || isLoadingRules) {
    return (
      <div className="space-y-6 max-w-5xl" aria-busy="true" aria-live="polite">
        <div className="h-8 w-48 bg-slate-900 rounded-lg animate-pulse" />
        <div className="h-40 bg-slate-900 border border-slate-800 rounded-2xl animate-pulse" />
        <div className="h-96 bg-slate-900 border border-slate-800 rounded-2xl animate-pulse" />
      </div>
    );
  }

  if (isErrorProvider || isErrorRules || !provider) {
    const errMessage =
      (providerError as ApiError)?.message ||
      (rulesError as ApiError)?.message ||
      'No fue posible cargar la información del profesional o sus horarios.';

    return (
      <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 max-w-xl space-y-4">
        <h2 className="text-base font-bold text-rose-200">Error al cargar disponibilidad</h2>
        <p className="text-sm text-rose-300">{errMessage}</p>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate('/admin/profesionales')}
            className="px-4 py-2 bg-slate-800 text-slate-200 rounded-xl text-sm font-medium hover:bg-slate-700"
          >
            Volver a Profesionales
          </button>
          <button
            type="button"
            onClick={() => {
              refetchProvider();
              refetchRules();
            }}
            className="px-4 py-2 bg-rose-500 text-white rounded-xl text-sm font-medium hover:bg-rose-600"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Navigation Header */}
      <div>
        <button
          type="button"
          onClick={() => navigate('/admin/profesionales')}
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors mb-4"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span>Volver a Profesionales</span>
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl sm:text-3xl font-bold text-white font-serif tracking-tight">
                Disponibilidad y Horarios
              </h1>
              <span
                className={`px-3 py-0.5 rounded-full border text-xs font-semibold ${
                  provider.is_active
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                {provider.is_active ? 'Activo' : 'Inactivo'}
              </span>
            </div>
            <p className="text-sm text-slate-400">
              Profesional: <strong className="text-white">{provider.name}</strong>
              {provider.email ? ` • ${provider.email}` : ''}
              {provider.phone ? ` • ${provider.phone}` : ''}
            </p>
          </div>
        </div>
      </div>

      {/* Alerts */}
      {scheduleSuccess && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-sm text-emerald-300 flex items-center justify-between">
          <span>{scheduleSuccess}</span>
          <button
            type="button"
            onClick={() => setScheduleSuccess(null)}
            className="text-emerald-400 font-bold hover:text-white"
          >
            ×
          </button>
        </div>
      )}
      {scheduleError && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-sm text-rose-300 flex items-center justify-between" role="alert">
          <span>{scheduleError}</span>
          <button
            type="button"
            onClick={() => setScheduleError(null)}
            className="text-rose-400 font-bold hover:text-white"
          >
            ×
          </button>
        </div>
      )}

      {/* Section 1: Weekly Schedule */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-lg font-bold text-white font-serif">Horario Semanal Habitual</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Configura los turnos y franjas de atención por día de la semana.
            </p>
          </div>

          <button
            type="button"
            onClick={handleSaveSchedule}
            disabled={!isScheduleDirty || hasScheduleErrors || replaceRulesMutation.isPending}
            className="px-5 py-2 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold rounded-xl text-xs transition-colors disabled:opacity-50 flex items-center gap-2 self-start sm:self-auto"
          >
            {replaceRulesMutation.isPending ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                <span>Guardando...</span>
              </>
            ) : (
              'Guardar Horarios'
            )}
          </button>
        </div>

        {/* Days List */}
        <div className="space-y-4">
          {DAYS.map((day) => {
            const dayData = schedule[day.index];
            const errors = getDayErrors(day.index);

            return (
              <div
                key={day.index}
                className={`p-4 rounded-xl border transition-colors ${
                  dayData.active
                    ? 'bg-slate-950/60 border-slate-800'
                    : 'bg-slate-950/20 border-slate-800/40 opacity-70'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  {/* Day Label & Toggle */}
                  <div className="flex items-center gap-4 min-w-[140px]">
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={dayData.active}
                        onChange={() => handleToggleDay(day.index)}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500" />
                    </label>
                    <span className="text-sm font-bold text-white">{day.label}</span>
                  </div>

                  {/* Intervals or Inactive message */}
                  <div className="flex-1">
                    {!dayData.active ? (
                      <span className="text-xs text-slate-500 italic">Sin atención (Día libre)</span>
                    ) : (
                      <div className="space-y-2">
                        {dayData.intervals.map((interval, idx) => (
                          <div key={idx} className="flex flex-wrap items-center gap-2">
                            <input
                              type="time"
                              value={interval.start_time}
                              onChange={(e) =>
                                handleIntervalTimeChange(day.index, idx, 'start_time', e.target.value)
                              }
                              aria-label={`Hora inicio ${day.label} tramo ${idx + 1}`}
                              className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
                            />
                            <span className="text-slate-500 text-xs">—</span>
                            <input
                              type="time"
                              value={interval.end_time}
                              onChange={(e) =>
                                handleIntervalTimeChange(day.index, idx, 'end_time', e.target.value)
                              }
                              aria-label={`Hora término ${day.label} tramo ${idx + 1}`}
                              className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
                            />

                            <button
                              type="button"
                              onClick={() => handleRemoveInterval(day.index, idx)}
                              className="p-1 text-slate-500 hover:text-rose-400 transition-colors"
                              title="Eliminar tramo"
                              aria-label={`Eliminar tramo ${idx + 1} de ${day.label}`}
                            >
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          </div>
                        ))}

                        <button
                          type="button"
                          onClick={() => handleAddInterval(day.index)}
                          className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400 hover:text-emerald-300 mt-1"
                        >
                          + Añadir tramo
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Day Errors */}
                {errors.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-rose-500/20 space-y-1">
                    {errors.map((err, errIdx) => (
                      <p key={errIdx} className="text-xs text-rose-400">
                        • {err}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Section 2: Time Off Blocks */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-lg font-bold text-white font-serif">Bloqueos y Ausencias (Time Off)</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Periodos específicos donde el profesional no estará disponible para reservas.
            </p>
          </div>

          <button
            ref={addTimeOffBtnRef}
            type="button"
            onClick={() => setIsCreateTimeOffOpen(true)}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-xl text-xs transition-colors flex items-center gap-2 self-start sm:self-auto"
          >
            <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>Añadir Bloqueo</span>
          </button>
        </div>

        {/* Inline Delete Error */}
        {timeOffDeleteError && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-sm text-rose-300 flex items-center justify-between" role="alert">
            <span>{timeOffDeleteError}</span>
            <button
              type="button"
              onClick={() => setTimeOffDeleteError(null)}
              className="text-rose-400 font-bold hover:text-white"
            >
              ×
            </button>
          </div>
        )}

        {/* Time Off Table */}
        {isLoadingTimeOffs ? (
          <div className="space-y-2 py-4">
            {[1, 2].map((n) => (
              <div key={n} className="h-12 bg-slate-800 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : isErrorTimeOffs ? (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs text-center">
            Error al cargar la lista de bloqueos.
            <button
              type="button"
              onClick={() => refetchTimeOffs()}
              className="ml-2 font-semibold underline text-white"
            >
              Reintentar
            </button>
          </div>
        ) : timeOffs.length === 0 ? (
          <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl text-slate-400 text-xs">
            No hay bloqueos activos o futuros registrados para este profesional.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="border-b border-slate-800 text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-3 px-3">Inicio</th>
                  <th className="py-3 px-3">Término</th>
                  <th className="py-3 px-3">Motivo</th>
                  <th className="py-3 px-3 text-right">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {timeOffs.map((to) => (
                  <tr key={to.id} className="hover:bg-slate-950/40 transition-colors">
                    <td className="py-3 px-3 font-medium text-white">{formatDateTime(to.starts_at)}</td>
                    <td className="py-3 px-3 font-medium text-white">{formatDateTime(to.ends_at)}</td>
                    <td className="py-3 px-3 text-slate-400">{to.reason || '—'}</td>
                    <td className="py-3 px-3 text-right">
                      <button
                        ref={deleteBtnRef}
                        type="button"
                        onClick={() => {
                          setTimeOffDeleteError(null);
                          setTimeOffToDelete(to);
                        }}
                        className="px-2.5 py-1 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded-lg text-[11px] font-medium transition-colors"
                      >
                        Eliminar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Time Off Modal */}
      <CreateTimeOffModal
        isOpen={isCreateTimeOffOpen}
        onClose={() => setIsCreateTimeOffOpen(false)}
        providerId={provider.id}
        providerName={provider.name}
        timezone={business?.timezone || 'America/Santiago'}
        triggerRef={addTimeOffBtnRef}
      />

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={!!timeOffToDelete}
        title="Eliminar Bloqueo de Disponibilidad"
        description="¿Confirmas que deseas eliminar este bloqueo? Los horarios dentro de este rango volverán a estar disponibles para reserva pública inmediatamente."
        confirmText="Eliminar Bloqueo"
        cancelText="Volver"
        isDestructive={true}
        isLoading={deleteTimeOffMutation.isPending}
        onConfirm={() => {
          if (timeOffToDelete) {
            deleteTimeOffMutation.mutate(timeOffToDelete.id);
          }
        }}
        onClose={() => {
          setTimeOffToDelete(null);
          setTimeOffDeleteError(null);
        }}
        triggerRef={deleteBtnRef}
      />
    </div>
  );
};
