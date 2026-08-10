import { apiFetch } from './client';

export interface BookingCreatePayload {
  service_id: string;
  provider_id?: string | null;
  starts_at: string;
  client_request_id: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  customer_notes?: string;
}

export interface BookingPublicCreatedData {
  public_reference: string;
  status: string;
  service: {
    name: string;
    duration_minutes: number;
    price_amount: number;
  };
  provider: {
    name: string;
  };
  starts_at: string;
  ends_at: string;
  customer_email: string;
}

export interface BusinessContactPublic {
  name: string;
  email: string;
  phone?: string | null;
  address?: string | null;
  timezone?: string;
}

export interface BookingConfirmationData {
  public_reference: string;
  status: string;
  service: {
    name: string;
    duration_minutes: number;
    price_amount: number;
  };
  provider: {
    name: string;
  };
  starts_at: string;
  ends_at: string;
  customer_email_masked: string;
  business: BusinessContactPublic;
}

export async function createPublicBooking(
  payload: BookingCreatePayload,
  signal?: AbortSignal
): Promise<BookingPublicCreatedData> {
  return apiFetch<BookingPublicCreatedData>('/public/bookings', {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  });
}

export async function fetchBookingConfirmation(
  publicReference: string,
  signal?: AbortSignal
): Promise<BookingConfirmationData> {
  return apiFetch<BookingConfirmationData>(
    `/public/bookings/${publicReference}/confirmation`,
    { signal }
  );
}
