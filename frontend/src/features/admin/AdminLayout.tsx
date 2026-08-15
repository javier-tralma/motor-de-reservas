import React, { useState, useRef } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';
import { useFocusTrap } from '../../hooks/useFocusTrap';

export const AdminLayout: React.FC = () => {
  const { user, business, logout } = useAuth();
  const navigate = useNavigate();
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);

  const mainRef = useRef<HTMLElement | null>(null);
  const asideRef = useRef<HTMLElement | null>(null);
  const menuButtonRef = useRef<HTMLButtonElement | null>(null);

  // Focus trap for mobile drawer:
  // - Confines Tab/Shift+Tab inside asideRef
  // - Applies `inert` exclusively to mainRef
  // - Closes on Escape
  // - Restores focus to menuButtonRef upon close
  useFocusTrap(asideRef, isMobileOpen, {
    onEscape: () => setIsMobileOpen(false),
    disableEscape: isLoggingOut,
    returnFocusRef: menuButtonRef,
    inertRefs: [mainRef],
  });

  const handleLogout = async () => {
    setIsLoggingOut(true);
    setLogoutError(null);
    try {
      await logout();
      navigate('/admin/login', { replace: true });
    } catch {
      setLogoutError('Error al cerrar sesión. Intenta nuevamente.');
    } finally {
      setIsLoggingOut(false);
    }
  };

  const navItems = [
    { label: 'Resumen', path: '/admin', active: true, end: true },
    { label: 'Calendario', path: '/admin/calendario', active: true },
    { label: 'Reservas', path: '/admin/reservas', active: true },
    { label: 'Servicios', path: '/admin/servicios', active: true },
    { label: 'Profesionales', path: '/admin/profesionales', active: true },
    { label: 'Horarios', path: '#', active: false },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col md:flex-row">
      {/* Mobile Top Navigation */}
      <header className="md:hidden bg-slate-900 border-b border-slate-800 px-4 py-3 flex items-center justify-between sticky top-0 z-30">
        <div>
          <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider block">
            {business?.name || 'Estudio Nómada'}
          </span>
          <span className="text-sm font-bold text-white">Panel Admin</span>
        </div>
        <button
          ref={menuButtonRef}
          type="button"
          onClick={() => setIsMobileOpen(!isMobileOpen)}
          aria-expanded={isMobileOpen}
          aria-label={isMobileOpen ? 'Cerrar menú de navegación' : 'Abrir menú de navegación'}
          className="p-2 rounded-xl bg-slate-800 text-slate-300 hover:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {isMobileOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </header>

      {/* Mobile Drawer Overlay */}
      {isMobileOpen && (
        <div
          className="md:hidden fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-40"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar (Desktop + Mobile Drawer) */}
      <aside
        ref={asideRef}
        aria-label="Panel lateral de administración"
        className={`fixed md:static inset-y-0 left-0 z-50 w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between transform transition-transform duration-200 ease-in-out ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div>
          {/* Header */}
          <div className="p-6 border-b border-slate-800">
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider block">
              {business?.name || 'Estudio Nómada'}
            </span>
            <h2 className="text-xl font-bold text-white font-serif mt-1">Administración</h2>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1" aria-label="Navegación principal">
            {navItems.map((item) =>
              item.active ? (
                <NavLink
                  key={item.label}
                  to={item.path}
                  onClick={() => setIsMobileOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                    }`
                  }
                  end={item.end}
                >
                  {item.label}
                </NavLink>
              ) : (
                <span
                  key={item.label}
                  aria-disabled="true"
                  title="Próximamente disponible"
                  className="flex items-center justify-between px-4 py-3 rounded-xl text-sm font-medium text-slate-600 cursor-not-allowed opacity-60 select-none"
                >
                  <span>{item.label}</span>
                  <span className="text-[10px] bg-slate-800 text-slate-500 px-2 py-0.5 rounded-full border border-slate-700/50">
                    Pronto
                  </span>
                </span>
              )
            )}
          </nav>
        </div>

        {/* User Footer & Logout */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/50">
          {logoutError && (
            <p className="text-xs text-rose-400 mb-2 px-1" role="alert">
              {logoutError}
            </p>
          )}
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-white truncate">
                {user?.display_name || 'Administrador'}
              </p>
              <p className="text-xs text-slate-400 truncate">{user?.email}</p>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              disabled={isLoggingOut}
              aria-label="Cerrar sesión"
              aria-busy={isLoggingOut ? 'true' : undefined}
              className="p-2 rounded-xl bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 border border-slate-700/50 hover:border-rose-500/30 transition-colors focus:outline-none focus:ring-2 focus:ring-rose-500 disabled:opacity-50"
            >
              {isLoggingOut ? (
                <span className="w-5 h-5 block border-2 border-slate-400 border-t-transparent rounded-full animate-spin" aria-hidden="true" />
              ) : (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main ref={mainRef} className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  );
};
