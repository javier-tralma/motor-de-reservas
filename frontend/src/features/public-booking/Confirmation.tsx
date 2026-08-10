import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchBookingConfirmation } from '../../lib/api/bookings';
import { Header } from '../../components/Header';
import { Skeleton } from '../../components/Skeleton';
import { InlineAlert } from '../../components/InlineAlert';
import { formatCLP } from '../../lib/format/currency';
import { formatLocalDate, formatTimeRange } from '../../lib/format/date';

export const Confirmation: React.FC = () => {
  const { publicReference } = useParams<{ publicReference: string }>();

  const { data: booking, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['booking-confirmation', publicReference],
    queryFn: ({ signal }) => fetchBookingConfirmation(publicReference || '', signal),
    enabled: !!publicReference,
  });

  const timeZone = booking?.business?.timezone || 'America/Santiago';

  return (
    <div className="min-h-screen bg-[#f7f5f0] flex flex-col">
      <Header
        businessName={booking?.business?.name}
        businessEmail={booking?.business?.email}
        businessPhone={booking?.business?.phone}
      />

      <main className="flex-1 max-w-2xl w-full mx-auto p-4 sm:p-8 flex flex-col justify-center items-center">
        {isLoading && <Skeleton className="h-96 w-full" />}

        {isError && (
          <div className="w-full bg-[#fffdf9] p-8 rounded-3xl border border-[#dfe4df] text-center flex flex-col gap-4">
            <InlineAlert
              type="error"
              title="Reserva no encontrada"
              message={
                error instanceof Error ? error.message : 'No pudimos consultar la confirmación.'
              }
              onRetry={() => refetch()}
            />
            <Link
              to="/"
              className="inline-flex items-center justify-center min-h-[44px] min-w-[44px] px-5 py-2.5 text-base font-medium rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2f7fd3] border border-[#dfe4df] text-[#1f2a27] bg-[#fffdf9] hover:bg-[#f7f5f0]"
            >
              Volver al inicio
            </Link>
          </div>
        )}

        {booking && (
          <div className="bg-[#fffdf9] p-6 sm:p-10 rounded-3xl border border-[#dfe4df] shadow-md w-full flex flex-col gap-6 text-center sm:text-left">
            {/* Header Success Badge */}
            <div className="flex flex-col sm:flex-row items-center gap-4 border-b border-[#dfe4df] pb-6">
              <div className="w-14 h-14 rounded-full bg-[#247a57] text-white flex items-center justify-center text-2xl font-bold">
                ✓
              </div>
              <div>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-[#1f2a27]">
                  ¡Reserva confirmada!
                </h1>
                <p className="text-sm text-[#66736e] mt-0.5">
                  Tu cita ha sido agendada con éxito en {booking.business.name}.
                </p>
              </div>
            </div>

            {/* Public Reference Code */}
            <div className="bg-[#f7f5f0] p-4 rounded-xl border border-[#dfe4df] flex flex-col sm:flex-row items-center justify-between gap-2">
              <span className="text-xs uppercase tracking-wider font-bold text-[#66736e]">
                Código de reserva
              </span>
              <span className="font-mono text-lg font-bold text-[#176b5b] tracking-wider">
                {booking.public_reference}
              </span>
            </div>

            {/* Details Grid */}
            <div className="flex flex-col gap-4">
              <div className="flex justify-between items-start border-b border-[#dfe4df] pb-3">
                <div>
                  <span className="block text-xs uppercase tracking-wider font-semibold text-[#66736e]">
                    Servicio
                  </span>
                  <span className="font-bold text-[#1f2a27] text-base sm:text-lg">
                    {booking.service.name}
                  </span>
                  <span className="block text-xs text-[#66736e]">
                    {booking.service.duration_minutes} minutos
                  </span>
                </div>
                <span className="font-bold text-[#176b5b] text-base sm:text-lg">
                  {formatCLP(booking.service.price_amount)}
                </span>
              </div>

              <div className="border-b border-[#dfe4df] pb-3">
                <span className="block text-xs uppercase tracking-wider font-semibold text-[#66736e]">
                  Profesional asignado
                </span>
                <span className="font-semibold text-[#1f2a27] text-base">
                  {booking.provider.name}
                </span>
              </div>

              <div className="border-b border-[#dfe4df] pb-3">
                <span className="block text-xs uppercase tracking-wider font-semibold text-[#66736e]">
                  Fecha y horario
                </span>
                <span className="font-semibold text-[#1f2a27] text-base block capitalize">
                  {formatLocalDate(booking.starts_at.split('T')[0], timeZone)}
                </span>
                <span className="font-bold text-[#176b5b] text-lg block mt-0.5">
                  {formatTimeRange(booking.starts_at, booking.ends_at, timeZone)}
                </span>
                <span className="block text-xs text-[#66736e] mt-0.5">
                  Hora local ({timeZone})
                </span>
              </div>

              <div className="border-b border-[#dfe4df] pb-3">
                <span className="block text-xs uppercase tracking-wider font-semibold text-[#66736e]">
                  Correo de confirmación
                </span>
                <span className="font-medium text-[#1f2a27] text-sm">
                  {booking.customer_email_masked}
                </span>
              </div>

              <div>
                <span className="block text-xs uppercase tracking-wider font-semibold text-[#66736e]">
                  Ubicación y contacto
                </span>
                <span className="font-semibold text-[#1f2a27] text-sm block">
                  {booking.business.name}
                </span>
                {booking.business.address && (
                  <span className="text-xs text-[#66736e] block mt-0.5">
                    {booking.business.address}
                  </span>
                )}
                {booking.business.phone && (
                  <span className="text-xs text-[#66736e] block mt-0.5">
                    Tel: {booking.business.phone}
                  </span>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="pt-4 border-t border-[#dfe4df] flex justify-center sm:justify-start">
              <Link
                to="/"
                className="inline-flex items-center justify-center min-h-[44px] min-w-[44px] px-5 py-2.5 text-base font-medium rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2f7fd3] border border-[#dfe4df] text-[#1f2a27] bg-[#fffdf9] hover:bg-[#f7f5f0] w-full sm:w-auto"
              >
                Volver al inicio
              </Link>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
