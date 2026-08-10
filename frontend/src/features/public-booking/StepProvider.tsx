import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchServiceProviders, type ProviderPublic, type ServicePublic } from '../../lib/api/services';
import { RadioCard } from '../../components/RadioCard';
import { Skeleton } from '../../components/Skeleton';
import { InlineAlert } from '../../components/InlineAlert';
import { Button } from '../../components/Button';

interface StepProviderProps {
  service: ServicePublic;
  selectedProvider: ProviderPublic | null;
  isAnyProvider: boolean;
  onSelectProvider: (provider: ProviderPublic | null, isAny: boolean) => void;
  onNext: () => void;
  onBack: () => void;
}

export const StepProvider: React.FC<StepProviderProps> = ({
  service,
  selectedProvider,
  isAnyProvider,
  onSelectProvider,
  onNext,
  onBack,
}) => {
  const { data: providers, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['service-providers', service.id],
    queryFn: ({ signal }) => fetchServiceProviders(service.id, signal),
  });

  const canContinue = !isLoading && !isError && !!providers && providers.length > 0;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-xl sm:text-2xl font-bold text-[#1f2a27]">
          ¿Con quién prefieres atenderte?
        </h2>
        <p className="text-sm text-[#66736e] mt-1">
          Servicio seleccionado: <span className="font-semibold text-[#1f2a27]">{service.name}</span>
        </p>
      </div>

      {isLoading && <Skeleton count={3} className="h-20 w-full" />}

      {isError && (
        <InlineAlert
          type="error"
          title="Error al cargar profesionales"
          message={error instanceof Error ? error.message : 'No pudimos cargar los profesionales'}
          onRetry={() => refetch()}
        />
      )}

      {providers && providers.length === 0 && (
        <div className="p-8 text-center bg-[#fffdf9] rounded-2xl border border-[#dfe4df]">
          <p className="text-[#66736e] font-medium">
            No hay profesionales disponibles para este servicio.
          </p>
        </div>
      )}

      {providers && providers.length > 0 && (
        <div className="flex flex-col gap-3">
          {/* Opción 1: Cualquier profesional */}
          <RadioCard
            id="provider-any"
            name="provider_selection"
            value="any"
            checked={isAnyProvider}
            onChange={() => onSelectProvider(null, true)}
            title="Cualquier profesional"
            description="Te asignaremos a alguien disponible para el horario que elijas."
          />

          {/* Opciones individuales */}
          {providers.map((provider) => (
            <RadioCard
              key={provider.id}
              id={`provider-${provider.id}`}
              name="provider_selection"
              value={provider.id}
              checked={!isAnyProvider && selectedProvider?.id === provider.id}
              onChange={() => onSelectProvider(provider, false)}
              title={provider.name}
              description={provider.bio || 'Profesional del equipo'}
            />
          ))}
        </div>
      )}

      <div className="pt-4 flex justify-between items-center border-t border-[#dfe4df]">
        <Button variant="outline" onClick={onBack}>
          Volver
        </Button>
        <Button onClick={onNext} disabled={!canContinue}>
          Continuar
        </Button>
      </div>
    </div>
  );
};
