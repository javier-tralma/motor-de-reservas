import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Home } from './features/public-booking/Home';
import { Wizard } from './features/public-booking/Wizard';
import { Confirmation } from './features/public-booking/Confirmation';

import { AuthProvider } from './features/auth/AuthContext';
import { LoginPage } from './features/auth/LoginPage';
import { ProtectedRoute } from './features/auth/ProtectedRoute';
import { AdminLayout } from './features/admin/AdminLayout';
import { DashboardPage } from './features/admin/DashboardPage';
import { BookingsListPage } from './features/admin/BookingsListPage';
import { BookingDetailPage } from './features/admin/BookingDetailPage';
import { ServicesPage } from './features/admin/ServicesPage';
import { ProvidersPage } from './features/admin/ProvidersPage';
import { ProviderAvailabilityPage } from './features/admin/ProviderAvailabilityPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Home />} />
          <Route path="/reservar" element={<Wizard />} />
          <Route path="/reservar/confirmacion/:publicReference" element={<Confirmation />} />

          {/* Admin Routes */}
          <Route
            path="/admin/login"
            element={
              <AuthProvider>
                <LoginPage />
              </AuthProvider>
            }
          />
          <Route
            element={
              <AuthProvider>
                <ProtectedRoute />
              </AuthProvider>
            }
          >
            <Route element={<AdminLayout />}>
              <Route path="/admin" element={<DashboardPage />} />
              <Route path="/admin/reservas" element={<BookingsListPage />} />
              <Route path="/admin/reservas/:bookingId" element={<BookingDetailPage />} />
              <Route path="/admin/servicios" element={<ServicesPage />} />
              <Route path="/admin/profesionales" element={<ProvidersPage />} />
              <Route
                path="/admin/profesionales/:providerId/disponibilidad"
                element={<ProviderAvailabilityPage />}
              />
            </Route>
          </Route>
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}





export default App;
