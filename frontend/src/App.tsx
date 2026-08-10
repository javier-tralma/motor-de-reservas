import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Home } from './features/public-booking/Home';
import { Wizard } from './features/public-booking/Wizard';
import { Confirmation } from './features/public-booking/Confirmation';

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
          <Route path="/" element={<Home />} />
          <Route path="/reservar" element={<Wizard />} />
          <Route path="/reservar/confirmacion/:publicReference" element={<Confirmation />} />
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
