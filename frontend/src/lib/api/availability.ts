import { apiFetch } from './client';
import { publicQueryKeys } from './queryKeys';

export interface SlotPublic {
  starts_at: string;
  ends_at: string;
}

export interface AvailabilityData {
  date: string;
  service_id: string;
  provider_id?: string | null;
  timezone: string;
  slots: SlotPublic[];
}

export function availabilityQueryKey(
  serviceId: string,
  date: string,
  providerId?: string | null
) {
  return publicQueryKeys.availability(serviceId, date, providerId);
}


export async function fetchPublicAvailability(params: {
  service_id: string;
  date: string;
  provider_id?: string | null;
  signal?: AbortSignal;
}): Promise<AvailabilityData> {
  const query = new URLSearchParams({
    service_id: params.service_id,
    date: params.date,
  });
  if (params.provider_id) {
    query.set('provider_id', params.provider_id);
  }

  return apiFetch<AvailabilityData>(`/public/availability?${query.toString()}`, {
    signal: params.signal,
  });
}
