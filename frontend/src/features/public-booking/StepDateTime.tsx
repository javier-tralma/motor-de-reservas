import React, { useMemo, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchPublicAvailability, availabilityQueryKey, type SlotPublic } from '../../lib/api/availability';
import type { ServicePublic, ProviderPublic } from '../../lib/api/services';
import { Skeleton } from '../../components/Skeleton';
import { InlineAlert } from '../../components/InlineAlert';
import { Button } from '../../components/Button';
import {
  formatLocalDate,
  formatTimeSlot,
  getSlotHourInTimezone,
  getUpcomingDatesInTimezone,
} from '../../lib/format/date';

interface StepDateTimeProps {
  service: ServicePublic;
  provider: ProviderPublic | null;
  selectedDate: string;
  selectedSlot: SlotPublic | null;
  bookingHorizonDays?: number;
  timeZone?: string;
  onSelectDate: (dateStr: string) => void;
  onSelectSlot: (slot: SlotPublic) => void;
  onNext: () => void;
  onBack: () => void;
  conflictMessage?: string | null;
}

export const StepDateTime: React.FC<StepDateTimeProps> = ({
  service,
  provider,
  selectedDate,
  selectedSlot,
  bookingHorizonDays = 60,
  timeZone = 'America/Santiago',
  onSelectDate,
  onSelectSlot,
  onNext,
  onBack,
  conflictMessage,
}) => {
  const conflictAlertRef = useRef<HTMLDivElement | null>(null);

  // Focus urgent conflict alert on mount or when conflict message appears
  useEffect(() => {
    if (conflictMessage) {
      conflictAlertRef.current?.focus();
    }
  }, [conflictMessage]);

  // Generate list of available dates in business timezone
  const availableDates = useMemo(() => {
    return getUpcomingDatesInTimezone(Math.min(bookingHorizonDays, 14), timeZone);
  }, [bookingHorizonDays, timeZone]);

  // Set default selected date if empty
  React.useEffect(() => {
    if (!selectedDate && availableDates.length > 0) {
      onSelectDate(availableDates[0].dateStr);
    }
  }, [selectedDate, availableDates, onSelectDate]);

  // Fetch slots for selected date
  const { data: availability, isLoading, isError, error, refetch } = useQuery({
    queryKey: availabilityQueryKey(service.id, selectedDate, provider?.id),
    queryFn: ({ signal }) =>
      fetchPublicAvailability({
        service_id: service.id,
        date: selectedDate,
        provider_id: provider ? provider.id : null,
        signal,
      }),
    enabled: !!selectedDate,
  });

  const slots = useMemo(() => availability?.slots || [], [availability?.slots]);

  // Group slots by morning / afternoon in business timezone
  const { morningSlots, afternoonSlots } = useMemo(() => {
    const morning: SlotPublic[] = [];
    const afternoon: SlotPublic[] = [];

    slots.forEach((slot) => {
      const hour = getSlotHourInTimezone(slot.starts_at, timeZone);
      if (hour < 13) {
        morning.push(slot);
      } else {
        afternoon.push(slot);
      }
    });

    return { morningSlots: morning, afternoonSlots: afternoon };
  }, [slots, timeZone]);

  const handleNextDay = () => {
    const currentIndex = availableDates.findIndex((d) => d.dateStr === selectedDate);
    if (currentIndex >= 0 && currentIndex < availableDates.length - 1) {
      onSelectDate(availableDates[currentIndex + 1].dateStr);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-xl sm:text-2xl font-bold text-[#1f2a27]">
          Elige una fecha y una hora
        </h2>
        <p className="text-sm text-[#66736e] mt-1">
          {service.name} {provider ? `con ${provider.name}` : '(Cualquier profesional)'}
        </p>
      </div>

      {/* Conflicto 409 alert */}
      {conflictMessage && (
        <InlineAlert
          ref={conflictAlertRef}
          type="error"
          isUrgent={true}
          tabIndex={-1}
          title="Horario no disponible"
          message={conflictMessage}
        />
      )}

      {/* Date Strip */}
      <div className="flex flex-col gap-2">
        <label className="text-sm font-semibold text-[#1f2a27]">Selecciona un día</label>
        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin">
          {availableDates.map((item) => {
            const isSelected = selectedDate === item.dateStr;
            return (
              <button
                key={item.dateStr}
                type="button"
                onClick={() => onSelectDate(item.dateStr)}
                className={`flex flex-col items-center justify-center min-w-[72px] p-2.5 rounded-xl border text-center transition-all cursor-pointer min-h-[54px] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2f7fd3] ${
                  isSelected
                    ? 'bg-[#176b5b] text-white border-[#176b5b] font-bold shadow-sm'
                    : 'bg-[#fffdf9] border-[#dfe4df] text-[#1f2a27] hover:border-[#66736e]'
                }`}
              >
                <span className="text-xs uppercase tracking-wider font-semibold capitalize">
                  {item.label}
                </span>
                <span className="text-xs mt-0.5 opacity-90">{item.sublabel}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Slot Selection */}
      <div className="flex flex-col gap-4">
        <div className="flex justify-between items-center">
          <label className="text-sm font-semibold text-[#1f2a27] capitalize">
            Horarios para {formatLocalDate(selectedDate, timeZone)}
          </label>
          <span className="text-xs text-[#66736e]">
            Zona: {availability?.timezone || timeZone}
          </span>
        </div>

        {isLoading && <Skeleton count={4} className="h-12 w-full" />}

        {isError && (
          <InlineAlert
            type="error"
            isUrgent={true}
            title="Error al cargar horarios"
            message={error instanceof Error ? error.message : 'No pudimos cargar los horarios'}
            onRetry={() => refetch()}
          />
        )}

        {!isLoading && !isError && slots.length === 0 && (
          <div className="p-6 text-center bg-[#fffdf9] rounded-2xl border border-[#dfe4df] flex flex-col items-center gap-3">
            <p className="text-[#66736e] font-medium text-sm">
              No quedan horas disponibles ese día. Prueba con la fecha siguiente.
            </p>
            <Button variant="outline" onClick={handleNextDay} className="text-sm">
              Ver próximo día disponible
            </Button>
          </div>
        )}

        {!isLoading && !isError && slots.length > 0 && (
          <div className="flex flex-col gap-6">
            {morningSlots.length > 0 && (
              <div>
                <span className="block text-xs uppercase tracking-wider font-bold text-[#66736e] mb-2">
                  Mañana
                </span>
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                  {morningSlots.map((slot) => {
                    const isSelected = selectedSlot?.starts_at === slot.starts_at;
                    const timeStr = formatTimeSlot(slot.starts_at, timeZone);

                    return (
                      <button
                        key={slot.starts_at}
                        type="button"
                        onClick={() => onSelectSlot(slot)}
                        className={`min-h-[44px] px-3 py-2 text-sm font-semibold rounded-lg border transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2f7fd3] ${
                          isSelected
                            ? 'bg-[#176b5b] text-white border-[#176b5b] ring-2 ring-[#176b5b]'
                            : 'bg-[#fffdf9] border-[#dfe4df] text-[#1f2a27] hover:border-[#176b5b]'
                        }`}
                      >
                        {timeStr}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {afternoonSlots.length > 0 && (
              <div>
                <span className="block text-xs uppercase tracking-wider font-bold text-[#66736e] mb-2">
                  Tarde
                </span>
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                  {afternoonSlots.map((slot) => {
                    const isSelected = selectedSlot?.starts_at === slot.starts_at;
                    const timeStr = formatTimeSlot(slot.starts_at, timeZone);

                    return (
                      <button
                        key={slot.starts_at}
                        type="button"
                        onClick={() => onSelectSlot(slot)}
                        className={`min-h-[44px] px-3 py-2 text-sm font-semibold rounded-lg border transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2f7fd3] ${
                          isSelected
                            ? 'bg-[#176b5b] text-white border-[#176b5b] ring-2 ring-[#176b5b]'
                            : 'bg-[#fffdf9] border-[#dfe4df] text-[#1f2a27] hover:border-[#176b5b]'
                        }`}
                      >
                        {timeStr}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="pt-4 flex justify-between items-center border-t border-[#dfe4df]">
        <Button variant="outline" onClick={onBack}>
          Volver
        </Button>
        <Button onClick={onNext} disabled={!selectedSlot || isLoading || isError}>
          Continuar
        </Button>
      </div>
    </div>
  );
};
