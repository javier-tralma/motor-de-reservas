import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './useAuth';

export const ProtectedRoute: React.FC = () => {
  const { isLoading, isAuthenticated, error, refreshUser } = useAuth();

  if (isLoading) {
    return (
      <div
        className="min-h-screen bg-slate-900 flex items-center justify-center p-4"
        aria-busy="true"
        aria-live="polite"
      >
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-emerald-500/20 border-t-emerald-400 rounded-full animate-spin" />
          <p className="text-slate-400 text-sm font-medium">Verificando sesión...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4 text-center">
        <div className="bg-slate-800 p-6 rounded-lg max-w-sm border border-red-500/20">
          <p className="text-red-400 font-medium mb-4">{error.message || 'Error de conexión'}</p>
          <button
            onClick={() => void refreshUser()}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded font-medium transition-colors"
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

