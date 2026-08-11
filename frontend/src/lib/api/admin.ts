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
