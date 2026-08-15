export interface AdminBookingsFilters {
  date?: string;
  status?: string;
  provider_id?: string;
}

export const adminQueryKeys = {
  dashboard: () => ['admin', 'dashboard'] as const,
  bookingsRoot: () => ['admin', 'bookings'] as const,
  bookingsList: (filters?: AdminBookingsFilters) =>
    ['admin', 'bookings', filters ?? {}] as const,
  bookingDetail: (bookingId: string) => ['admin', 'booking', bookingId] as const,
  providersRoot: () => ['admin', 'providers'] as const,
  providers: () => ['admin', 'providers', { serviceId: null }] as const,
  providersForService: (serviceId: string) => ['admin', 'providers', { serviceId }] as const,
  services: () => ['admin', 'services'] as const,
  providerDetail: (providerId: string) => ['admin', 'provider', providerId] as const,
  providerServices: (providerId: string) => ['admin', 'provider', providerId, 'services'] as const,
  providerAvailabilityRules: (providerId: string) =>
    ['admin', 'provider', providerId, 'availability-rules'] as const,
  providerTimeOffs: (providerId: string) =>
    ['admin', 'provider', providerId, 'time-offs'] as const,
  calendarEventsRoot: () => ['admin', 'calendarEvents'] as const,
  calendarEvents: (start: string, end: string, providerId?: string) =>
    ['admin', 'calendarEvents', { start, end, providerId }] as const,
};

export const publicQueryKeys = {
  availability: (serviceId?: string, date?: string, providerId?: string | null) =>
    ['public-availability', serviceId ?? null, date ?? null, providerId ?? null] as const,
  availabilityRoot: () => ['public-availability'] as const,
};
