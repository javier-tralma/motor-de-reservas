export interface AdminBookingsFilters {
  date?: string;
  status?: string;
  provider_id?: string;
}

export const adminQueryKeys = {
  dashboard: () => ['admin', 'dashboard'] as const,
  bookingsList: (filters?: AdminBookingsFilters) =>
    ['admin', 'bookings', filters ?? {}] as const,
  bookingDetail: (bookingId: string) => ['admin', 'booking', bookingId] as const,
  providers: () => ['admin', 'providers'] as const,
  services: () => ['admin', 'services'] as const,
  providerDetail: (providerId: string) => ['admin', 'provider', providerId] as const,
  providerServices: (providerId: string) => ['admin', 'provider', providerId, 'services'] as const,
  providerAvailabilityRules: (providerId: string) =>
    ['admin', 'provider', providerId, 'availability-rules'] as const,
  providerTimeOffs: (providerId: string) =>
    ['admin', 'provider', providerId, 'time-offs'] as const,
};

export const publicQueryKeys = {
  availability: (serviceId?: string, date?: string, providerId?: string | null) =>
    ['public-availability', serviceId ?? null, date ?? null, providerId ?? null] as const,
  availabilityRoot: () => ['public-availability'] as const,
};
