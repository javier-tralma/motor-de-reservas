import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { resolveApiBaseUrl, buildApiUrl, apiFetch, ApiError } from './client';

describe('API Client Base URL Resolution', () => {
  it('uses explicitly provided VITE_API_BASE_URL (trimming trailing slashes)', () => {
    expect(resolveApiBaseUrl('http://127.0.0.1:8001/api/', false)).toBe('http://127.0.0.1:8001/api');
    expect(resolveApiBaseUrl('https://api.example.com/api', true)).toBe('https://api.example.com/api');
    expect(resolveApiBaseUrl('/api///', true)).toBe('/api');
  });

  it('falls back to relative /api when envVar is empty or undefined in production', () => {
    expect(resolveApiBaseUrl('', true)).toBe('/api');
    expect(resolveApiBaseUrl('   ', true)).toBe('/api');
    expect(resolveApiBaseUrl(undefined, true)).toBe('/api');
  });

  it('falls back to http://localhost:8000/api when envVar is empty or undefined in development', () => {
    expect(resolveApiBaseUrl('', false)).toBe('http://localhost:8000/api');
    expect(resolveApiBaseUrl('   ', false)).toBe('http://localhost:8000/api');
    expect(resolveApiBaseUrl(undefined, false)).toBe('http://localhost:8000/api');
  });

  it('buildApiUrl builds properly formatted endpoints with leading slashes', () => {
    expect(buildApiUrl('/public/services', '/api')).toBe('/api/public/services');
    expect(buildApiUrl('public/services', '/api')).toBe('/api/public/services');
    expect(buildApiUrl('/admin/login', 'http://localhost:8000/api')).toBe('http://localhost:8000/api/admin/login');
  });
});

describe('apiFetch execution', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('performs successful json request and unwraps data payload', async () => {
    const mockData = { services: [{ id: '1', name: 'Corte' }] };
    const mockResponse = {
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: vi.fn().mockResolvedValue({ data: mockData }),
    };
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

    const result = await apiFetch<typeof mockData>('/public/services');
    expect(result).toEqual(mockData);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/public/services'),
      expect.objectContaining({ credentials: 'include' })
    );
  });

  it('throws ApiError with structured payload when response is not ok', async () => {
    const errorPayload = {
      error: {
        code: 'slot_unavailable',
        message: 'El horario ya no está disponible',
        request_id: 'req-123',
      },
    };
    const mockResponse = {
      ok: false,
      status: 409,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: vi.fn().mockResolvedValue(errorPayload),
    };
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

    await expect(apiFetch('/public/bookings')).rejects.toThrow(ApiError);
    await expect(apiFetch('/public/bookings')).rejects.toMatchObject({
      status: 409,
      code: 'slot_unavailable',
      message: 'El horario ya no está disponible',
      requestId: 'req-123',
    });
  });
});
