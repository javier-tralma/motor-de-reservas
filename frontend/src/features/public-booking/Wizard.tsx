import React, { useRef, useEffect, useState } from 'react';
import { availabilityQueryKey } from '../../lib/api/availability';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchPublicBusiness } from '../../lib/api/business';
import { useBookingWizard } from './useBookingWizard';
import { StepService } from './StepService';
import { StepProvider } from './StepProvider';
import { StepDateTime } from './StepDateTime';
import { StepCustomer } from './StepCustomer';
import { SummaryCard } from '../../components/SummaryCard';
import { Header } from '../../components/Header';

const STEPS = [
  { id: 1, title: 'Servicio' },
  { id: 2, title: 'Profesional' },
  { id: 3, title: 'Horario' },
  { id: 4, title: 'Tus datos' },
];

export const Wizard: React.FC = () => {
  const navigate = useNavigate();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const [conflictMessage, setConflictMessage] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: business } = useQuery({
    queryKey: ['public-business'],
    queryFn: ({ signal }) => fetchPublicBusiness(signal),
  });

  const {
    state,
    setStep,
    selectService,
    selectProvider,
    selectDate,
    selectSlot,
    setCustomerData,
    clearSlotForConflict,
    getClientRequestId,
  } = useBookingWizard();

  // Focus heading on step change for screen readers
  useEffect(() => {
    headingRef.current?.focus();
  }, [state.step]);

  const handleSlotConflict = (message: string) => {
    setConflictMessage(message);
    if (state.selectedService && state.selectedDate) {
      queryClient.invalidateQueries({
        queryKey: availabilityQueryKey(
          state.selectedService.id,
          state.selectedDate,
          state.isAnyProvider ? null : state.selectedProvider?.id
        ),
      });
    }
    clearSlotForConflict();
  };

  return (
    <div className="min-h-screen bg-[var(--color-canvas)] flex flex-col font-sans">
      <Header
        businessName={business?.name}
        businessEmail={business?.email}
        businessPhone={business?.phone}
      />

      <main className="flex-1 max-w-5xl w-full mx-auto p-4 sm:p-8">
        {/* Step Progress Header */}
        <nav aria-label="Progreso de reserva" className="mb-8">
          <ol className="flex items-center justify-between gap-2 border-b border-[var(--color-border)] pb-4">
            {STEPS.map((s) => {
              const isCurrent = state.step === s.id;
              const isCompleted = state.step > s.id;

              return (
                <li key={s.id} className="flex-1">
                  <button
                    type="button"
                    onClick={() => {
                      if (isCompleted) setStep(s.id as 1 | 2 | 3 | 4);
                    }}
                    disabled={!isCompleted}
                    aria-current={isCurrent ? 'step' : undefined}
                    className={`flex items-center gap-2 text-xs sm:text-sm font-semibold transition-colors w-full text-left min-h-[44px] ${
                      isCurrent
                        ? 'text-[var(--color-primary)]'
                        : isCompleted
                        ? 'text-[var(--color-ink)] cursor-pointer hover:underline'
                        : 'text-[var(--color-muted)] opacity-60 cursor-not-allowed'
                    }`}
                  >
                    <span
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                        isCurrent
                          ? 'bg-[var(--color-primary)] text-white'
                          : isCompleted
                          ? 'bg-[var(--color-ink)] text-white'
                          : 'bg-[#dfe4df] text-[var(--color-muted)]'
                      }`}
                    >
                      {s.id}
                    </span>
                    <span className="hidden sm:inline">{s.title}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        </nav>

        {/* Layout: Wizard + Summary Sidebar */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          <div className="lg:col-span-2 bg-[var(--color-surface)] p-6 sm:p-8 rounded-2xl border border-[var(--color-border)] shadow-sm">
            <h1
              ref={headingRef}
              tabIndex={-1}
              className="sr-only focus:outline-none"
            >
              Paso {state.step} de 4: {STEPS[state.step - 1].title}
            </h1>

            {state.step === 1 && (
              <StepService
                selectedService={state.selectedService}
                onSelectService={selectService}
                onNext={() => setStep(2)}
              />
            )}

            {state.step === 2 && state.selectedService && (
              <StepProvider
                service={state.selectedService}
                selectedProvider={state.selectedProvider}
                isAnyProvider={state.isAnyProvider}
                onSelectProvider={selectProvider}
                onNext={() => setStep(3)}
                onBack={() => setStep(1)}
              />
            )}

            {state.step === 3 && state.selectedService && (
              <StepDateTime
                service={state.selectedService}
                provider={state.isAnyProvider ? null : state.selectedProvider}
                selectedDate={state.selectedDate}
                selectedSlot={state.selectedSlot}
                bookingHorizonDays={business?.booking_horizon_days}
                timeZone={business?.timezone}
                onSelectDate={(d) => {
                  setConflictMessage(null);
                  selectDate(d);
                }}
                onSelectSlot={(slot) => {
                  setConflictMessage(null);
                  selectSlot(slot);
                }}
                onNext={() => setStep(4)}
                onBack={() => setStep(2)}
                conflictMessage={conflictMessage}
              />
            )}

            {state.step === 4 && state.selectedService && state.selectedSlot && (
              <StepCustomer
                service={state.selectedService}
                provider={state.isAnyProvider ? null : state.selectedProvider}
                selectedDate={state.selectedDate}
                selectedSlot={state.selectedSlot}
                getClientRequestId={getClientRequestId}
                initialCustomerData={state.customerData}
                onBack={() => setStep(3)}
                onSuccess={(ref) => navigate(`/reservar/confirmacion/${ref}`)}
                onSlotConflict={handleSlotConflict}
                onCustomerDataChange={setCustomerData}
                timeZone={business?.timezone}
              />
            )}
          </div>

          {/* Right Column / Mobile Summary */}
          <div className="lg:col-span-1">
            <SummaryCard
              serviceName={state.selectedService?.name}
              serviceDuration={state.selectedService?.duration_minutes}
              servicePrice={state.selectedService?.price_amount}
              providerName={
                state.isAnyProvider
                  ? 'Cualquier profesional'
                  : state.selectedProvider?.name
              }
              dateStr={state.selectedDate}
              startsAtISO={state.selectedSlot?.starts_at}
              endsAtISO={state.selectedSlot?.ends_at}
              timezone={business?.timezone}
            />
          </div>
        </div>
      </main>
    </div>
  );
};
