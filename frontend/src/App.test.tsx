import { render, screen } from '@testing-library/react';
import App from './App';
import { describe, it, expect } from 'vitest';

describe('App Foundation', () => {
  it('renders the main heading', () => {
    render(<App />);
    expect(screen.getByText('Reserva tu cita')).toBeDefined();
  });
});
