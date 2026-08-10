import { apiFetch } from './client';

export interface BusinessPublic {
  name: string;
  slug: string;
  timezone: string;
  locale: string;
  currency: string;
  email: string;
  phone?: string | null;
  address?: string | null;
  booking_horizon_days: number;
}

export async function fetchPublicBusiness(signal?: AbortSignal): Promise<BusinessPublic> {
  return apiFetch<BusinessPublic>('/public/business', { signal });
}
