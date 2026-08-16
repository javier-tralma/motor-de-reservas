import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from './useAuth';
import { ApiError } from '../../lib/api/client';

const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'El email es requerido')
    .email('Formato de email inválido')
    .max(254, 'El email es demasiado largo'),
  password: z
    .string()
    .min(1, 'La contraseña es requerida')
    .max(128, 'La contraseña es demasiado larga'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export const LoginPage: React.FC = () => {
  const { isAuthenticated, isLoading: isAuthLoading, login } = useAuth();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const [isNetworkError, setIsNetworkError] = useState<boolean>(false);


  const {
    register,
    handleSubmit,
    setFocus,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  if (isAuthLoading) {
    return (
      <div className="min-h-screen bg-[#f7f5f0] flex items-center justify-center p-4">
        <div className="w-8 h-8 border-4 border-[#176b5b]/20 border-t-[#176b5b] rounded-full animate-spin" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/admin" replace />;
  }

  const onSubmit = async (data: LoginFormData) => {
    if (isSubmitting) return;
    setServerError(null);
    setIsNetworkError(false);

    try {
      await login(data.email, data.password);
      navigate('/admin', { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === 'invalid_credentials' || err.status === 401) {
          setServerError('Credenciales inválidas. Verifica tu correo y contraseña.');
        } else if (err.code === 'origin_mismatch') {
          setServerError('Origen no autorizado para la sesión.');
        } else {
          setServerError(err.message || 'Ocurrió un error inesperado.');
        }
        setTimeout(() => setFocus('email'), 0);
      } else {
        setIsNetworkError(true);
        setServerError('No se pudo conectar con el servidor. Verifica tu conexión a internet.');
      }
    }
  };

  const onFormSubmit = handleSubmit(onSubmit);

  return (
    <div className="min-h-screen bg-[#f7f5f0] text-[#1f2a27] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="text-center">
          <span className="inline-block p-3 rounded-2xl bg-[#176b5b]/10 border border-[#176b5b]/20 mb-4 text-[#176b5b] font-bold text-xl tracking-tight">
            Estudio Nómada
          </span>
          <h1 className="text-3xl font-bold tracking-tight text-[#1f2a27]">
            Panel de Administración
          </h1>
          <p className="mt-2 text-sm text-[#66736e]">
            Ingresa tus credenciales para acceder a la agenda
          </p>
        </div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-[#fffdf9] border border-[#dfe4df] py-8 px-6 shadow-xl rounded-2xl sm:px-10">
          <form className="space-y-6" onSubmit={onFormSubmit} noValidate>
            {serverError && (
              <div
                role="alert"
                tabIndex={-1}
                className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-sm flex flex-col gap-2"
              >
                <span>{serverError}</span>
                {isNetworkError && (
                  <button
                    type="submit"
                    className="self-start text-xs font-semibold text-rose-700 hover:text-rose-950 underline focus:outline-none focus:ring-2 focus:ring-rose-500"
                  >
                    Reintentar conexión
                  </button>
                )}
              </div>
            )}

            <div>
              <label
                htmlFor="admin-email"
                className="block text-xs font-medium text-[#66736e] mb-1"
              >
                Correo electrónico
              </label>
              <input
                id="admin-email"
                type="email"
                autoComplete="username"
                disabled={isSubmitting}
                {...register('email')}
                className={`w-full px-4 py-3 rounded-xl bg-[#fffdf9] border text-[#1f2a27] placeholder-[#66736e]/60 focus:outline-none focus:ring-2 focus:ring-[#176b5b] transition-colors ${
                  errors.email
                    ? 'border-rose-500 focus:ring-rose-500'
                    : 'border-[#dfe4df] hover:border-[#ccd3cc]'
                }`}
                placeholder="admin@ejemplo.cl"
              />
              {errors.email && (
                <p className="mt-1 text-xs text-rose-600" id="email-error">
                  {errors.email.message}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="admin-password"
                className="block text-xs font-medium text-[#66736e] mb-1"
              >
                Contraseña
              </label>
              <input
                id="admin-password"
                type="password"
                autoComplete="current-password"
                disabled={isSubmitting}
                {...register('password')}
                className={`w-full px-4 py-3 rounded-xl bg-[#fffdf9] border text-[#1f2a27] placeholder-[#66736e]/60 focus:outline-none focus:ring-2 focus:ring-[#176b5b] transition-colors ${
                  errors.password
                    ? 'border-rose-500 focus:ring-rose-500'
                    : 'border-[#dfe4df] hover:border-[#ccd3cc]'
                }`}
                placeholder="••••••••"
              />
              {errors.password && (
                <p className="mt-1 text-xs text-rose-600" id="password-error">
                  {errors.password.message}
                </p>
              )}
            </div>

            <div>
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full flex justify-center items-center py-3 px-4 rounded-xl shadow-xs text-sm font-semibold text-white bg-[#176b5b] hover:bg-[#125548] focus:outline-none focus:ring-2 focus:ring-[#176b5b] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
              >
                {isSubmitting ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Iniciando sesión...
                  </span>
                ) : (
                  'Iniciar sesión'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
