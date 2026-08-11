# ADR 001: Autenticación Administrativa mediante Sesiones Opacas Persistentes

## Estado
Aceptado

## Contexto
El hito 4 introduce el panel de administración. Se requiere una estrategia de autenticación para administradores que acceden a través de navegador web, garantizando seguridad, revocación inmediata y scoping multi-tenant transparente por negocio (`business_id`).

Se evaluaron dos enfoques principales:
1. Tokens JWT (JSON Web Tokens) en cookies o Web Storage.
2. Sesiones opacas persistentes en PostgreSQL almacenadas en cookies HTTP-only.

## Decisión
Se decide implementar **Sesiones Opacas Persistentes almacenadas en PostgreSQL** combinadas con cookies `HttpOnly`, `SameSite=Lax` y scoping estricto por `business_id`.

### Detalles de la solución:
- **Cookie**: Nombre `booking_admin_session`, flags `HttpOnly`, `SameSite=Lax`, `Path=/api/admin`, `Secure` (en producción).
- **Token de Sesión**: Generado con CSPRNG (`secrets.token_urlsafe(32)`) proporcionando al menos 256 bits de entropía. El token crudo solo existe en la cookie del navegador.
- **Almacenamiento**: La base de datos almacena únicamente el HMAC-SHA-256 del token utilizando una clave secreta del servidor (`SESSION_SECRET`). El token en texto plano nunca se guarda en base de datos ni se registra en logs.
- **Tabla `admin_sessions`**: Almacena `id`, `business_id`, `admin_user_id`, `token_hash`, `expires_at`, `revoked_at` y `created_at`. Tiene FKs y restricciones compuestas para asegurar la coherencia de negocio.
- **Expiración y Revocación**: TTL fijo absoluto de 8 horas (`ADMIN_SESSION_TTL_HOURS`). Las sesiones se pueden revocar explícitamente (`revoked_at = now()`) al hacer logout o por invalidez administrativa.
- **Protección CSRF**: Las peticiones mutativas (`POST`, `PUT`, `PATCH`, `DELETE`) en el área administrativa validan la coincidencia estricta del header `Origin` con `FRONTEND_URL`.

## Consecuencias

### Positivas:
- **Revocación instantánea**: Al revocar una sesión en la base de datos o expirar su timestamp, cualquier petición posterior responde `401 Unauthorized` de inmediato.
- **Seguridad en cliente**: Al utilizar cookies `HttpOnly`, el token no es accesible desde JavaScript, mitigando el riesgo de exfiltración por ataques XSS (a diferencia de Web Storage).
- **Sin tokens flotantes**: No existen tokens auto-contenidos que sigan siendo válidos tras la baja de un administrador o cambio de credenciales.

### Negativas / Trade-offs:
- **Consulta a BD por petición**: Cada petición administrativa autenticada requiere una consulta en `admin_sessions` para validar la sesión y obtener el usuario/negocio. Dada la baja tasa de tráfico de la administración en P0, este coste es insignificante y garantiza máxima consistencia.
- **Limpieza de sesiones**: Se requiere una tarea periódica de limpieza de sesiones expiradas en el futuro si la tabla crece significativamente.
