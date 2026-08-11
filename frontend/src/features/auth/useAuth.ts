import { createContext, useContext } from 'react';
import { type AdminUser, type BusinessInfo } from '../../lib/api/admin';

export interface AuthContextType {
  user: AdminUser | null;
  business: BusinessInfo | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: Error | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  handleUnauthorized: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth debe ser usado dentro de un AuthProvider');
  }
  return context;
};
