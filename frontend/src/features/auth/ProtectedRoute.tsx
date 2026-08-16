import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './useAuth';

export const ProtectedRoute: React.FC = () => {
  const { isLoading, isAuthenticated, error, refreshUser } = useAuth();

  if (isLoading) {
    return (
      <div
        className="min-h-screen bg-[#f7f5f0] flex items-center justify-center p-4"
        aria-busy="true"
        aria-live="polite"
      >
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-[#176b5b]/20 border-t-[#176b5b] rounded-full animate-spin" />
          <p className="text-[#66736e] text-sm font-medium">Verificando sesión...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#f7f5f0] flex items-center justify-center p-4 text-center">
        <div className="bg-[#fffdf9] p-6 rounded-2xl max-w-sm border border-[#dfe4df] shadow-sm">
          <p className="text-rose-700 font-medium mb-4 text-sm">{error.message || 'Error de conexión'}</p>
          <button
            onClick={() => void refreshUser()}
            className="px-4 py-2 bg-[#176b5b] hover:bg-[#125548] text-white rounded-xl font-semibold text-xs transition-colors"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/admin/login" replace />;
  }

  return <Outlet />;
};

