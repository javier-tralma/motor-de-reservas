import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Calendar } from 'lucide-react';

const queryClient = new QueryClient();

function BookingApp() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl overflow-hidden">
        <div className="bg-blue-600 p-6 text-white flex items-center gap-3">
          <Calendar className="w-8 h-8" />
          <h1 className="text-2xl font-semibold">Reserva tu cita</h1>
        </div>
        <div className="p-6">
          <p className="text-gray-600 mb-6">Selecciona el servicio que necesitas y elige el horario que mejor te acomode.</p>
          <button className="w-full bg-blue-600 text-white rounded-lg py-3 font-medium hover:bg-blue-700 transition-colors">
            Comenzar
          </button>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/" element={<BookingApp />} />
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
