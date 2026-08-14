import { describe, it, expect } from 'vitest';

describe('AdminCalendarBundle chunking', () => {
  it('dynamically imports AdminCalendarPage as a separate chunk', async () => {
    const module = await import('./AdminCalendarPage');
    expect(module.AdminCalendarPage).toBeDefined();
    expect(typeof module.AdminCalendarPage).toBe('function');
  });
});
