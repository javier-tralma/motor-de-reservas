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
};
