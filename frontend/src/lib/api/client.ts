export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: unknown;
  request_id?: string;
}

export class ApiError extends Error {
  code: string;
  status: number;
  details?: unknown;
  requestId?: string;

  constructor(status: number, payload: ApiErrorPayload) {
    super(payload.message || 'Error de servidor');
    this.name = 'ApiError';
    this.status = status;
    this.code = payload.code || 'unknown_error';
    this.details = payload.details;
    this.requestId = payload.request_id;
  }
}

export function resolveApiBaseUrl(envVar?: string, isProd: boolean = false): string {
  if (envVar !== undefined && envVar.trim() !== '') {
    return envVar.trim().replace(/\/+$/, '');
  }
  return isProd ? '/api' : 'http://localhost:8000/api';
}

export function getApiBaseUrl(): string {
  return resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL, import.meta.env.PROD);
}

export function buildApiUrl(endpoint: string, baseUrl: string = getApiBaseUrl()): string {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${baseUrl}${cleanEndpoint}`;
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = buildApiUrl(endpoint);
  
  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    credentials: 'include',
    headers,
  });

  const contentType = response.headers.get('content-type');
  const isJson = contentType && contentType.includes('application/json');
  const responseData = isJson ? await response.json() : null;

  if (!response.ok) {
    const errorEnvelope = responseData?.error as ApiErrorPayload | undefined;
    if (errorEnvelope) {
      throw new ApiError(response.status, errorEnvelope);
    }
    throw new ApiError(response.status, {
      code: 'http_error',
      message: response.statusText || 'Error de conexión',
    });
  }

  return responseData?.data as T;
}
