import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import App from './App';

vi.stubGlobal(
  'fetch',
  vi.fn(() =>
    Promise.resolve({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () =>
        Promise.resolve({
          data: {
            name: 'Estudio Nómada',
            slug: 'estudio-nomada',
            timezone: 'America/Santiago',
            locale: 'es-CL',
            currency: 'CLP',
            email: 'hola@estudionomada.cl',
            phone: '+56912345678',
            address: 'Calle Valparaíso 123',
            booking_horizon_days: 60,
          },
        }),
    })
  )
);

describe('App Home Page', () => {
  it('renders business name and CTA link', async () => {
    render(<App />);
    expect(await screen.findByText('Estudio Nómada')).toBeDefined();
    expect(await screen.findByRole('link', { name: /Reservar hora/i })).toBeDefined();
  });
});
