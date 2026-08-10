import { apiFetch } from './client';

export interface ServicePublic {
  id: string;
  name: string;
  description: string;
  duration_minutes: number;
  price_amount: number;
}

export interface ProviderPublic {
  id: string;
  name: string;
  bio: string;
}

export async function fetchPublicServices(signal?: AbortSignal): Promise<ServicePublic[]> {
  return apiFetch<ServicePublic[]>('/public/services', { signal });
}

export async function fetchServiceProviders(
  serviceId: string,
  signal?: AbortSignal
): Promise<ProviderPublic[]> {
  return apiFetch<ProviderPublic[]>(`/public/services/${serviceId}/providers`, { signal });
}
