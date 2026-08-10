import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchPublicBusiness } from '../../lib/api/business';
import { Header } from '../../components/Header';
import { Skeleton } from '../../components/Skeleton';

export const Home: React.FC = () => {
  const { data: business, isLoading, isError } = useQuery({
    queryKey: ['public-business'],
    queryFn: ({ signal }) => fetchPublicBusiness(signal),
  });

  return (
    <div className="min-h-screen bg-[var(--color-canvas)] flex flex-col font-sans">
      <Header
        businessName={business?.name}
        businessEmail={business?.email}
        businessPhone={business?.phone}
      />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-12 sm:py-20 flex flex-col justify-center items-center text-center">
        {isLoading && <Skeleton className="h-64 w-full max-w-xl" />}

        {isError && (
          <div className="p-8 bg-[var(--color-surface)] rounded-2xl border border-[var(--color-border)] text-center">
            <h2 className="font-serif text-2xl font-bold text-[var(--color-ink)]">Estudio Nómada</h2>
            <p className="text-sm text-[var(--color-muted)] mt-2 mb-6">
              Barbería y estilismo profesional en Viña del Mar.
            </p>
            <Link
              to="/reservar"
              className="inline-flex items-center justify-center min-h-[44px] px-8 py-3 text-base font-semibold rounded-lg bg-[var(--color-primary)] text-white hover:opacity-95 transition-opacity focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2f7fd3]"
            >
              Reservar hora
            </Link>
          </div>
        )}

        {business && (
          <div className="w-full max-w-3xl flex flex-col items-center">
            <span className="text-xs uppercase tracking-widest font-semibold text-[var(--color-accent)] mb-3">
              Barbería & Estilismo · Viña del Mar
            </span>
            <h1 className="font-serif text-4xl sm:text-5xl font-extrabold text-[var(--color-ink)] tracking-tight mb-6">
              {business.name}
            </h1>
            <p className="text-lg sm:text-xl text-[var(--color-muted)] max-w-xl mb-10 leading-relaxed font-normal">
              Un espacio dedicado al cuidado personal, cortes estructurados y perfilado tradicional con atención personalizada.
            </p>

            <Link
              to="/reservar"
              className="inline-flex items-center justify-center min-h-[48px] px-9 py-3.5 text-lg font-semibold rounded-xl bg-[var(--color-primary)] text-white hover:bg-[#125548] active:bg-[#0e443a] transition-colors shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2f7fd3] focus-visible:ring-offset-2"
            >
              Reservar hora
            </Link>

            <div className="mt-16 pt-8 border-t border-[var(--color-border)] w-full grid grid-cols-1 sm:grid-cols-2 gap-6 text-sm text-[var(--color-muted)] text-left sm:text-center">
              <div>
                <span className="font-semibold block text-[var(--color-ink)] mb-1 uppercase tracking-wider text-xs">
                  Ubicación
                </span>
                <span>{business.address || 'Calle Valparaíso 123, Viña del Mar'}</span>
              </div>
              <div>
                <span className="font-semibold block text-[var(--color-ink)] mb-1 uppercase tracking-wider text-xs">
                  Contacto
                </span>
                <span>{business.email} {business.phone ? `· ${business.phone}` : ''}</span>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="py-6 text-center text-xs text-[var(--color-muted)] border-t border-[var(--color-border)] bg-[var(--color-surface)]">
        <p>© {new Date().getFullYear()} Estudio Nómada. Todos los derechos reservados.</p>
      </footer>
    </div>
  );
};
