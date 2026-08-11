import React, { useEffect, useState, useCallback } from 'react';
import { getAdminMe, loginAdmin, logoutAdmin, type AdminUser, type BusinessInfo } from '../../lib/api/admin';
import { ApiError } from '../../lib/api/client';
import { useQueryClient } from '@tanstack/react-query';
import { AuthContext } from './useAuth';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AdminUser | null>(null);
  const [business, setBusiness] = useState<BusinessInfo | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);
  const queryClient = useQueryClient();

  const handleUnauthorized = useCallback(() => {
    setUser(null);
    setBusiness(null);
    setError(null);
    setIsLoading(false);
    queryClient.clear();
  }, [queryClient]);

  const refreshUser = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getAdminMe();
      setUser(data.admin);
      setBusiness(data.business);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        handleUnauthorized();
      } else {
        setError(err instanceof Error ? err : new Error('Error de conexión'));
      }
    } finally {
      setIsLoading(false);
    }
  }, [handleUnauthorized]);

  useEffect(() => {
    let active = true;
    getAdminMe()
      .then((data) => {
        if (active) {
          setUser(data.admin);
          setBusiness(data.business);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) {
          if (err instanceof ApiError && err.status === 401) {
            setUser(null);
            setBusiness(null);
            setError(null);
          } else {
            setError(err instanceof Error ? err : new Error('Error de conexión'));
          }
        }
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);


  const login = async (email: string, password: string): Promise<void> => {
    const data = await loginAdmin(email, password);
    setUser(data.admin);
    setBusiness(data.business);
    setError(null);
  };

  const logout = async (): Promise<void> => {
    try {
      await logoutAdmin();
      handleUnauthorized();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        handleUnauthorized();
      } else {
        throw err;
      }
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        business,
        isLoading,
        isAuthenticated: !!user,
        error,
        login,
        logout,
        refreshUser,
        handleUnauthorized,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

