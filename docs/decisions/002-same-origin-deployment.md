# ADR 002: Despliegue Same-Origin para Demostración Pública en Render

## Estado
Aceptado

## Contexto
El hito 14 prepara el MVP ("Sistema de Reservas") para una demostración pública profesional de coste cero, sirviendo como portfolio técnico demostrable.

La autenticación administrativa implementada en el hito 4 (ADR 001) se basa en sesiones opacas persistentes en PostgreSQL, transmitidas mediante cookies HTTP con flags `HttpOnly`, `SameSite=Lax`, `Path=/api/admin` y `Secure` (en producción).

Al evaluar topologías de despliegue gratuito compuesto (por ejemplo, frontend en Render Static Site o Vercel Hobby y backend en Render Web Service), surge un problema fundamental:
1. **Public Suffix List (PSL)**: El dominio `onrender.com` es un Public Suffix registrado. Por ello, dos subdominios como `https://frontend.onrender.com` y `https://api.onrender.com` son tratados por los navegadores como sitios completamente diferentes (cross-site).
2. **Restricción de Cookies**: En un contexto cross-site, las peticiones asíncronas (`fetch`) no envían cookies configuradas con `SameSite=Lax`. Además, los navegadores prohíben emitir cookies con alcance amplio como `Domain=.onrender.com`.
3. **Alternativas inviables o deficientes**:
   - Forzar `SameSite=None; Secure`: Convierte las cookies en cookies de terceros, las cuales son bloqueadas por defecto por navegadores como Safari (ITP) y Chrome en sus configuraciones de privacidad modernas, degradando la experiencia de usuario.
   - Vercel Hobby: Las condiciones de servicio de Vercel Hobby restringen explícitamente el uso a proyectos personales no comerciales, invalidando su uso para portfolios comerciales y demos freelance.
   - Exigir un dominio propio de pago upfront: Añade fricción y costes innecesarios a una demostración que debe ser reproducible y de coste cero.

## Decisión
Se decide adoptar una **arquitectura Same-Origin basada en un único Render Free Web Service**:

1. **Servicio Único**: Se despliega un único Web Service en Render (`https://<app>.onrender.com`).
2. **FastAPI como servidor unificado**:
   - Sirve todos los endpoints de API bajo `/api/*`.
   - Sirve los endpoints de salud y documentación del sistema (`/health`, `/docs`, `/openapi.json`).
   - Sirve los activos estáticos compilados de la SPA (`frontend/dist/assets/*`).
   - Proporciona un fallback a `index.html` únicamente para peticiones `GET` no-API, permitiendo la navegación directa y el refresco de rutas en React Router (ej. `/admin/dashboard`, `/reservar`).
   - Devuelve `404 Not Found` ante activos estáticos no encontrados (ej. `/assets/invalido.js`), sin emitir el HTML de la SPA.
3. **Base de Datos**: PostgreSQL alojado en **Neon Free** (instancia serverless con límites de 0.5 GB de almacenamiento y 100 CU-horas/mes).
4. **Cookies de Sesión**: Al estar en el mismo origen exacto, la cookie `booking_admin_session` se emite como host-only (sin atributo `Domain`) con `SameSite=Lax`, `HttpOnly` y `Secure` en producción, garantizando seguridad robusta sin depender de mecanismos cross-site.
5. **Configuración Frontend**: El cliente API del frontend se resuelve de manera relativa (`/api`) en producción cuando no se proporciona `VITE_API_BASE_URL`, eliminando la necesidad de variables de entorno con URLs absolutas en el despliegue unificado.

## Consecuencias

### Positivas:
- **Integridad de Autenticación**: Las cookies de sesión funcionan de manera transparente y segura bajo `SameSite=Lax` en todos los navegadores modernos sin riesgo de bloqueo por políticas de terceros.
- **Coste Cero Total**: Aprovecha el nivel gratuito de Render Web Service y Neon Free sin requerir servicios adicionales ni compras de dominios para la demostración técnica.
- **Simplicidad de Red y CORS**: Al operar bajo el mismo origen, se eliminan los preflights OPTIONS innecesarios para rutas relativas, manteniendo `verify_origin` para protección CSRF sobre el origen unificado.
- **Despliegue Atómico y Reproducible**: El artefacto completo se construye y levanta secuencialmente en un único proceso mediante `render.yaml`.

### Negativas / Trade-offs:
- **Cold Start**: Los servicios gratuitos de Render se suspenden tras 15 minutos de inactividad, pudiendo tardar aproximadamente 50–60 segundos en responder a la primera petición. Neon Free se suspende tras 5 minutos de inactividad. Esta limitación se documenta explícitamente en el README para los evaluadores del portfolio.
- **Build en Monorepo**: El comando de build debe ejecutar secuencialmente la compilación de Node.js y la sincronización de dependencias de Python con `uv`.

### Reversibilidad:
Si en el futuro se configura un dominio propio (ej. `midominio.com`), la arquitectura puede mantenerse unificada o separarse fácilmente en subdominios (ej. `app.midominio.com` y `api.midominio.com`) sin cambios en la lógica de negocio, configurando cookies bajo `Domain=midominio.com` o conservando el mismo origen mediante un reverse proxy / CDN (como Cloudflare o Nginx).
