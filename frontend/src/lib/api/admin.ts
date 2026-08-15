import { apiFetch } from './client';

export interface AdminUser {
  id: string;
  display_name: string;
  email: string;
}

export interface BusinessInfo {
  name: string;
  timezone: string;
  locale: string;
}

export interface AuthData {
  admin: AdminUser;
  business: BusinessInfo;
}

export interface DashboardSummary {
  total: number;
  confirmed_remaining: number;
  completed: number;
  cancelled: number;
  no_show: number;
}

export interface BookingAgendaItem {
  id: string;
  starts_at: string;
  ends_at: string;
  customer_name: string;
  service_name: string;
  provider_name: string;
  status: 'confirmed' | 'completed' | 'cancelled' | 'no_show' | string;
}

export interface DashboardData {
  date: string;
  timezone: string;
  summary: DashboardSummary;
  next_booking: BookingAgendaItem | null;
  agenda: BookingAgendaItem[];
}

export async function loginAdmin(email: string, password: string): Promise<AuthData> {
  return apiFetch<AuthData>('/admin/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function logoutAdmin(): Promise<void> {
  return apiFetch<void>('/admin/auth/logout', {
    method: 'POST',
  });
}

export async function getAdminMe(): Promise<AuthData> {
  return apiFetch<AuthData>('/admin/auth/me', {
    method: 'GET',
  });
}

export async function getAdminDashboard(): Promise<DashboardData> {
  return apiFetch<DashboardData>('/admin/dashboard', {
    method: 'GET',
  });
}

export type BookingStatus = 'confirmed' | 'completed' | 'cancelled' | 'no_show';

export interface AdminBookingListItem {
  id: string;
  starts_at: string;
  ends_at: string;
  customer_name: string;
  service_name_snapshot: string;
  provider_name_snapshot: string;
  provider_id: string;
  status: BookingStatus;
  source: string;
}

export interface AdminBookingDetail {
  id: string;
  public_reference: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  customer_notes: string;
  starts_at: string;
  ends_at: string;
  status: BookingStatus;
  source: string;
  service_id: string;
  provider_id: string;
  service_name_snapshot: string;
  provider_name_snapshot: string;
  duration_minutes_snapshot: number;
  price_amount_snapshot: number;
  cancelled_at?: string | null;
  completed_at?: string | null;
  no_show_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminBookingCreateRequest {
  service_id: string;
  provider_id: string;
  starts_at: string;
  client_request_id: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  customer_notes?: string;
}

export interface AdminProviderListItem {
  id: string;
  name: string;
  is_active: boolean;
}

export async function getAdminBookings(params?: {
  date?: string;
  status?: string;
  provider_id?: string;
  signal?: AbortSignal;
}): Promise<AdminBookingListItem[]> {
  const query = new URLSearchParams();
  if (params?.date) query.set('date', params.date);
  if (params?.status) query.set('status', params.status);
  if (params?.provider_id) query.set('provider_id', params.provider_id);

  const qs = query.toString();
  return apiFetch<AdminBookingListItem[]>(`/admin/bookings${qs ? `?${qs}` : ''}`, {
    signal: params?.signal,
  });
}

export async function getAdminBookingDetail(
  bookingId: string,
  signal?: AbortSignal
): Promise<AdminBookingDetail> {
  return apiFetch<AdminBookingDetail>(`/admin/bookings/${bookingId}`, {
    signal,
  });
}

export async function updateAdminBookingStatus(
  bookingId: string,
  status: 'completed' | 'cancelled' | 'no_show'
): Promise<AdminBookingDetail> {
  return apiFetch<AdminBookingDetail>(`/admin/bookings/${bookingId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

export async function createAdminBooking(payload: AdminBookingCreateRequest): Promise<AdminBookingDetail> {
  return apiFetch<AdminBookingDetail>('/admin/bookings', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getAdminProviders(service_id?: string, signal?: AbortSignal): Promise<AdminProviderListItem[]> {
  const query = new URLSearchParams();
  if (service_id) {
    query.set('service_id', service_id);
  }
  const qs = query.toString();
  return apiFetch<AdminProviderListItem[]>(`/admin/providers${qs ? `?${qs}` : ''}`, {
    signal,
  });
}

export interface AdminServiceDetail {
  id: string;
  name: string;
  description: string;
  duration_minutes: number;
  price_amount: number;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface AdminServiceCreate {
  name: string;
  description?: string;
  duration_minutes: number;
  price_amount: number;
  is_active?: boolean;
  sort_order?: number;
}

export interface AdminServiceUpdate {
  name?: string;
  description?: string;
  duration_minutes?: number;
  price_amount?: number;
  is_active?: boolean;
  sort_order?: number;
}

export interface AdminProviderDetail {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  bio: string;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface AdminProviderCreate {
  name: string;
  email?: string | null;
  phone?: string | null;
  bio?: string;
  is_active?: boolean;
  sort_order?: number;
}

export interface AdminProviderUpdate {
  name?: string;
  email?: string | null;
  phone?: string | null;
  bio?: string;
  is_active?: boolean;
  sort_order?: number;
}

export interface AdminProviderServicesDetail {
  provider_id: string;
  service_ids: string[];
}

export async function getAdminServices(signal?: AbortSignal): Promise<AdminServiceDetail[]> {
  return apiFetch<AdminServiceDetail[]>('/admin/services', {
    signal,
  });
}

export async function createAdminService(data: AdminServiceCreate): Promise<AdminServiceDetail> {
  return apiFetch<AdminServiceDetail>('/admin/services', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateAdminService(
  id: string,
  data: AdminServiceUpdate
): Promise<AdminServiceDetail> {
  return apiFetch<AdminServiceDetail>(`/admin/services/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function getAdminProviderDetail(
  id: string,
  signal?: AbortSignal
): Promise<AdminProviderDetail> {
  return apiFetch<AdminProviderDetail>(`/admin/providers/${id}`, {
    signal,
  });
}

export async function createAdminProvider(
  data: AdminProviderCreate
): Promise<AdminProviderDetail> {
  return apiFetch<AdminProviderDetail>('/admin/providers', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateAdminProvider(
  id: string,
  data: AdminProviderUpdate
): Promise<AdminProviderDetail> {
  return apiFetch<AdminProviderDetail>(`/admin/providers/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function getAdminProviderServices(
  id: string,
  signal?: AbortSignal
): Promise<AdminProviderServicesDetail> {
  return apiFetch<AdminProviderServicesDetail>(`/admin/providers/${id}/services`, {
    signal,
  });
}

export async function replaceAdminProviderServices(
  id: string,
  serviceIds: string[]
): Promise<AdminProviderServicesDetail> {
  return apiFetch<AdminProviderServicesDetail>(`/admin/providers/${id}/services`, {
    method: 'PUT',
    body: JSON.stringify({ service_ids: serviceIds }),
  });
}

export interface AdminAvailabilityRuleItem {
  weekday: number;
  start_time: string;
  end_time: string;
}

export async function getAdminProviderAvailabilityRules(
  providerId: string,
  signal?: AbortSignal
): Promise<AdminAvailabilityRuleItem[]> {
  return apiFetch<AdminAvailabilityRuleItem[]>(
    `/admin/providers/${providerId}/availability-rules`,
    { signal }
  );
}

export async function replaceAdminProviderAvailabilityRules(
  providerId: string,
  rules: AdminAvailabilityRuleItem[]
): Promise<AdminAvailabilityRuleItem[]> {
  return apiFetch<AdminAvailabilityRuleItem[]>(
    `/admin/providers/${providerId}/availability-rules`,
    {
      method: 'PUT',
      body: JSON.stringify({ rules }),
    }
  );
}

export interface AdminTimeOffDetail {
  id: string;
  provider_id: string;
  starts_at: string;
  ends_at: string;
  reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminTimeOffCreate {
  provider_id: string;
  starts_at_local: string;
  ends_at_local: string;
  reason?: string | null;
}

export async function getAdminTimeOffs(
  providerId: string,
  signal?: AbortSignal
): Promise<AdminTimeOffDetail[]> {
  return apiFetch<AdminTimeOffDetail[]>(`/admin/time-off?provider_id=${providerId}`, {
    signal,
  });
}

export async function createAdminTimeOff(
  data: AdminTimeOffCreate
): Promise<AdminTimeOffDetail> {
  return apiFetch<AdminTimeOffDetail>('/admin/time-off', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function deleteAdminTimeOff(id: string): Promise<void> {
  return apiFetch<void>(`/admin/time-off/${id}`, {
    method: 'DELETE',
  });
}

export interface CalendarEventItem {
  id: string;
  kind: 'booking' | 'time_off';
  starts_at: string;
  ends_at: string;
  provider_id: string;
  provider_name: string;
  booking_status: string | null;
  customer_display_name: string | null;
  service_name: string | null;
  reason: string | null;
}

export interface CalendarEventsData {
  timezone: string;
  events: CalendarEventItem[];
}

export async function getAdminCalendarEvents(start: string, end: string, providerId?: string, signal?: AbortSignal): Promise<CalendarEventsData> {
  const params = new URLSearchParams();
  params.append('start', start);
  params.append('end', end);
  if (providerId) {
    params.append('provider_id', providerId);
  }
  return apiFetch<CalendarEventsData>(`/admin/calendar-events?${params.toString()}`, {
    method: 'GET',
    signal,
  });
}
