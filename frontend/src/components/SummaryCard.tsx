import React from 'react';
import { formatCLP } from '../lib/format/currency';
import { formatLocalDate, formatTimeRange } from '../lib/format/date';

interface SummaryCardProps {
  serviceName?: string;
  serviceDuration?: number;
  servicePrice?: number;
  providerName?: string;
  dateStr?: string;
  startsAtISO?: string;
  endsAtISO?: string;
  timezone?: string;
}

export const SummaryCard: React.FC<SummaryCardProps> = ({
  serviceName,
  serviceDuration,
  servicePrice,
  providerName,
  dateStr,
  startsAtISO,
  endsAtISO,
  timezone = 'America/Santiago',
}) => {
  const hasSelection = serviceName || providerName || startsAtISO;

  if (!hasSelection) {
    return (
      <div className="bg-[#fffdf9] p-5 rounded-2xl border border-[#dfe4df] text-[#66736e] text-sm">
        <p className="font-semibold text-[#1f2a27] mb-1">Tu reserva</p>
        <p>Selecciona un servicio para comenzar.</p>
      </div>
    );
  }

  return (
    <div className="bg-[#fffdf9] p-5 rounded-2xl border border-[#dfe4df] shadow-sm flex flex-col gap-4">
      <h3 className="font-bold text-[#1f2a27] text-lg border-b border-[#dfe4df] pb-3">
        Resumen de la cita
      </h3>

      {serviceName && (
        <div className="flex justify-between items-start gap-2">
          <div>
            <span className="block font-semibold text-[#1f2a27] text-base">{serviceName}</span>
            {serviceDuration && (
              <span className="text-xs text-[#66736e]">{serviceDuration} minutos</span>
            )}
          </div>
          {servicePrice !== undefined && (
            <span className="font-bold text-[#176b5b] text-base">
              {formatCLP(servicePrice)}
            </span>
          )}
        </div>
      )}

      {providerName && (
        <div className="border-t border-[#dfe4df] pt-3">
          <span className="block text-xs uppercase tracking-wider font-semibold text-[#66736e]">
            Atención por
          </span>
          <span className="font-medium text-[#1f2a27] text-sm">{providerName}</span>
        </div>
      )}

      {dateStr && (
        <div className="border-t border-[#dfe4df] pt-3">
          <span className="block text-xs uppercase tracking-wider font-semibold text-[#66736e]">
            Fecha
          </span>
          <span className="font-medium text-[#1f2a27] text-sm capitalize">
            {formatLocalDate(dateStr, timezone)}
          </span>
        </div>
      )}

      {startsAtISO && endsAtISO && (
        <div className="border-t border-[#dfe4df] pt-3">
          <span className="block text-xs uppercase tracking-wider font-semibold text-[#66736e]">
            Horario
          </span>
          <span className="font-semibold text-[#176b5b] text-base">
            {formatTimeRange(startsAtISO, endsAtISO, timezone)}
          </span>
          <span className="block text-[11px] text-[#66736e] mt-0.5">
            Hora local ({timezone})
          </span>
        </div>
      )}
    </div>
  );
};
