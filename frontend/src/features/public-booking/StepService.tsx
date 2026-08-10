import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchPublicServices, type ServicePublic } from '../../lib/api/services';
import { RadioCard } from '../../components/RadioCard';
import { Skeleton } from '../../components/Skeleton';
import { InlineAlert } from '../../components/InlineAlert';
import { Button } from '../../components/Button';
import { formatCLP } from '../../lib/format/currency';

interface StepServiceProps {
  selectedService: ServicePublic | null;
  onSelectService: (service: ServicePublic) => void;
  onNext: () => void;
}

export const StepService: React.FC<StepServiceProps> = ({
  selectedService,
  onSelectService,
  onNext,
}) => {
  const { data: services, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['public-services'],
    queryFn: ({ signal }) => fetchPublicServices(signal),
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-xl sm:text-2xl font-bold text-[#1f2a27]">¿Qué quieres reservar?</h2>
        <p className="text-sm text-[#66736e] mt-1">
          Selecciona un servicio para ver los profesionales y horarios disponibles.
        </p>
      </div>

      {isLoading && <Skeleton count={3} className="h-20 w-full" />}

      {isError && (
        <InlineAlert
          type="error"
          title="Error al cargar servicios"
          message={error instanceof Error ? error.message : 'No pudimos cargar los servicios'}
          onRetry={() => refetch()}
        />
      )}

      {services && services.length === 0 && (
        <div className="p-8 text-center bg-[#fffdf9] rounded-2xl border border-[#dfe4df]">
          <p className="text-[#66736e] font-medium">No hay servicios disponibles en este momento.</p>
        </div>
      )}

      {services && services.length > 0 && (
        <div className="flex flex-col gap-3">
          {services.map((service) => (
            <RadioCard
              key={service.id}
              id={`service-${service.id}`}
              name="service_selection"
              value={service.id}
              checked={selectedService?.id === service.id}
              onChange={() => onSelectService(service)}
              title={service.name}
              description={service.description}
              badgeRight={formatCLP(service.price_amount)}
              subtitleRight={`${service.duration_minutes} minutos`}
            />
          ))}
        </div>
      )}

      <div className="pt-4 flex justify-end border-t border-[#dfe4df]">
        <Button
          onClick={onNext}
          disabled={!selectedService}
          className="w-full sm:w-auto"
        >
          Continuar
        </Button>
      </div>
    </div>
  );
};
