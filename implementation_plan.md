# Implementation Plan — Milestone 7: Configuración Administrativa de Disponibilidad por Profesional

Planificación técnica detallada para el **Milestone 7**, permitiendo la administración del horario laboral semanal (`availability_rules`) y la gestión de bloqueos y ausencias excepcionales (`time_off`) por profesional en una interfaz dedicada dentro del panel administrativo.

> [!IMPORTANT]
> **ESTADO DE PLANIFICACIÓN**: Este documento es exclusivamente un plan de diseño técnico corregido. No se ha escrito código de producto ni modificado la base de datos en esta fase. Se requiere aprobación explícita antes de comenzar la ejecución.

---

## 1. Precondiciones y Estado del Repositorio

- **Limpieza del Repositorio**: `git status --short` limpio.
- **Etiqueta Git**: Tag `milestone-6` presente en el repositorio.
- **Esquema de Base de Datos**:
  - Los modelos `AvailabilityRule` y `TimeOff` ya existen en `backend/app/models/availability.py`.
  - Las tablas `availability_rules` y `time_off` ya fueron creadas por la migración `c2f6f70806e9_create_rules_and_time_off.py` con constraints de orden (`end_time > start_time`, `ends_at > starts_at`), día de semana (`weekday >= 0 AND weekday <= 6`) y Foreign Keys compuestas de tenant `(business_id, provider_id)`.
  - **No se requieren nuevas migraciones Alembic**.

---

## 2. Decisiones de Dominio y Manejo de Tiempo

### 2.1 Utilidades de Tiempo Compartidas (`app.domain.time_utils`)
Para evitar duplicación y discrepancias en la interpretación de instantes:
1. **Reutilización de `create_aware_datetime`**:
   - `create_aware_datetime(d: date, t: time, tz_name: str, fold: int = 0) -> datetime` ya existe en `app.domain.time_utils` y detecta saltos DST (gaps) mediante verificación round-trip lanzando `NonExistentTimeError`.
2. **Definición de Función Única de Serialización Local**:
   - Se añade a `app.domain.time_utils`:
     ```python
     def format_local_iso(dt: datetime, tz_name: str) -> str:
         """
         Convierte un instante timezone-aware (típicamente UTC) a la zona IANA del negocio
         y lo formatea como cadena ISO 8601 con su offset explícito (ej. '2026-08-15T09:00:00-04:00').
         """
         tz = ZoneInfo(tz_name)
         return dt.astimezone(tz).isoformat()
     ```
   - No se crean funciones locales paralelas en routers ni esquemas; todos los adaptadores consumen esta utilidad centralizada.

### 2.2 Interpretación Civil en `POST /api/admin/time-off`
1. **Payload Civil Puro**:
   El cliente envía strings de fecha y hora civil local (`starts_at_local` y `ends_at_local`) sin offset (formato ISO local `YYYY-MM-DDTHH:MM:SS` o `YYYY-MM-DDTHH:MM`). No se acepta ni documenta `starts_at` o `ends_at` con offset en el request.
2. **Resolución en `business.timezone`**:
   - El backend descompone cada string en `(date, time)`.
   - Se resuelve el instante consciente utilizando `create_aware_datetime(d, t, tz_name=business.timezone, fold=0)`.
3. **Manejo de Transiciones DST**:
   - **Hora inexistente (salto adelante / gap de primavera)**: `create_aware_datetime` lanza `NonExistentTimeError`, el cual es traducido a HTTP `422` con código de error `non_existent_local_time` y mensaje explicativo en español ("La hora seleccionada no existe debido al cambio de horario").
   - **Hora ambigua (salto atrás / solape de otoño)**: Se aplica explícitamente `fold=0` (primer instante cronológico antes del retraso del reloj), garantizando comportamiento determinista y documentado.
4. **Validación de Rango y Persistencia**:
   - Los instantes resueltos se convierten a UTC (`.astimezone(timezone.utc)`).
   - Se exige estrictamente `starts_at_utc < ends_at_utc`. Si `starts_at_utc >= ends_at_utc`, responde HTTP `422` con código `invalid_time_range`.
   - Se persiste en PostgreSQL en la columna `timestamptz` en UTC.
   - La respuesta serializa `starts_at` y `ends_at` en formato ISO 8601 con el offset de la zona IANA del negocio (`America/Santiago`, ej. `-03:00` en horario de verano o `-04:00` en horario estándar).

### 2.3 Horarios Semanales (`availability_rules`)
1. **Días de Semana**: `weekday` es un entero `0..6` donde `0 = Lunes` y `6 = Domingo`.
2. **Horas Civiles**: `start_time` y `end_time` son tipos `time` sin zona horaria, interpretados en `business.timezone`.
3. **Orden y Medianoche**: Exige `start_time < end_time`. No se permiten reglas que crucen medianoche en P0.
4. **Múltiples Intervalos y Adyacencia**:
   - Se permiten múltiples intervalos no solapados por día para representar pausas y turnos partidos.
   - El backend **permite intervalos adyacentes** (ej. `09:00-11:00` y `11:00-13:00`), considerándolos válidos.
   - El frontend los **fusiona automáticamente (normalización)** antes de enviar el `PUT` (ej. normaliza a `09:00-13:00`).
   - Solapamientos reales en el mismo día son rechazados con HTTP `422`.
5. **Reemplazo Atómico con `SELECT ... FOR UPDATE`**:
   - `PUT /api/admin/providers/{id}/availability-rules` carga el `Provider` con `SELECT ... FOR UPDATE` para serializar concurrencia.
   - Elimina las reglas anteriores del profesional e inserta las nuevas en una sola transacción.
   - Acepta `rules: []` para indicar que el profesional no tiene turnos laborales.

### 2.4 Invariante de Reservas Preexistentes
- La creación o eliminación de un `time_off` **nunca altera ni cancela automáticamente** reservas confirmadas preexistentes.
- Los bloqueos afectan de inmediato las consultas de disponibilidad pública `/api/public/availability`, excluyendo los slots que se solapen con el bloqueo.

---

## 3. Contratos HTTP Exactos

Todas las rutas administrativas exigen cookie de sesión `booking_admin_session`. Las mutaciones (`POST`, `PUT`, `DELETE`) verifican el encabezado `Origin` coincidente con `FRONTEND_URL` (CSRF). Pydantic utiliza `ConfigDict(extra="forbid")`.

### 3.1 `GET /api/admin/providers/{id}/availability-rules`
- **Request**: Obtiene las reglas semanales del profesional.
- **Procesamiento**:
  - Valida que `id` pertenezca al `business_id` de la sesión (`404 provider_not_found` si no existe).
  - Ordena establemente por `weekday ASC, start_time ASC`.
- **Response (200)**:
  ```json
  {
    "data": [
      { "weekday": 0, "start_time": "09:00:00", "end_time": "13:00:00" },
      { "weekday": 0, "start_time": "14:00:00", "end_time": "18:00:00" },
      { "weekday": 1, "start_time": "10:00:00", "end_time": "16:00:00" }
    ]
  }
  ```
- **Errores**: `401 unauthorized`, `404 provider_not_found`.

### 3.2 `PUT /api/admin/providers/{id}/availability-rules`
- **Request Body** (`AdminAvailabilityRulesReplace`):
  ```json
  {
    "rules": [
      { "weekday": 0, "start_time": "09:00", "end_time": "13:00" },
      { "weekday": 0, "start_time": "14:00", "end_time": "18:00" }
    ]
  }
  ```
- **Validaciones Pydantic**:
  - `start_time` y `end_time` en formato válido de hora, `start_time < end_time`.
  - `weekday`: `0 <= weekday <= 6`.
  - Solapamientos reales en el mismo día responden `422 validation_error`.
  - Intervalos adyacentes son aceptados.
- **Procesamiento**:
  - `SELECT ... FOR UPDATE` sobre `Provider`.
  - Reemplazo atómico de reglas en DB.
- **Response (200)**:
  ```json
  {
    "data": [
      { "weekday": 0, "start_time": "09:00:00", "end_time": "13:00:00" },
      { "weekday": 0, "start_time": "14:00:00", "end_time": "18:00:00" }
    ]
  }
  ```
- **Errores**: `401 unauthorized`, `403 forbidden` (CSRF), `404 provider_not_found`, `422 validation_error`.

### 3.3 `GET /api/admin/time-off?provider_id={uuid}`
- **Query Params**: `provider_id` es **estrictamente obligatorio** (sin filtros extras; si falta responde `422`).
- **Procesamiento**:
  - Valida pertenencia de `provider_id` al negocio (`404 provider_not_found` si no existe).
  - Filtra únicamente bloqueos vigentes o futuros: `ends_at > injected_now` (con reloj inyectable en testing; bloqueos pasados quedan excluidos).
  - Ordena por `starts_at ASC, id ASC`.
  - Serializa timestamps UTC al offset local del negocio usando `format_local_iso`.
- **Response (200)**:
  ```json
  {
    "data": [
      {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "provider_id": "4bc85f64-5717-4562-b3fc-2c963f66afa7",
        "starts_at": "2026-08-15T09:00:00-04:00",
        "ends_at": "2026-08-15T18:00:00-04:00",
        "reason": "Vacaciones de invierno",
        "created_at": "2026-08-10T10:00:00-04:00",
        "updated_at": "2026-08-10T10:00:00-04:00"
      }
    ]
  }
  ```
- **Errores**: `401 unauthorized`, `404 provider_not_found`, `422 validation_error`.

### 3.4 `POST /api/admin/time-off`
- **Request Body** (`AdminTimeOffCreate`):
  ```json
  {
    "provider_id": "4bc85f64-5717-4562-b3fc-2c963f66afa7",
    "starts_at_local": "2026-08-15T09:00:00",
    "ends_at_local": "2026-08-15T18:00:00",
    "reason": "Vacaciones"
  }
  ```
  *(No se acepta ni documenta `starts_at` ni `ends_at` con offset)*.
- **Validaciones**:
  - `provider_id`: UUID válido.
  - `starts_at_local` y `ends_at_local`: strings de fecha-hora civil local sin offset.
  - `reason`: `str | None`. Si contiene solo espacios o está vacío, se normaliza estrictamente a `None`/`null`. Máximo 240 caracteres.
  - Resolución de horas con `create_aware_datetime`: si cae en gap DST lanza `422 non_existent_local_time`.
  - Validación de orden: `resolved_start_utc < resolved_end_utc` (si no, responde `422 invalid_time_range`).
- **Procesamiento**:
  - Valida que `provider_id` pertenezca al negocio (permite definir `time_off` tanto para profesionales activos como inactivos).
  - Persiste instantes UTC en `TimeOff`.
  - Serializa respuesta con `format_local_iso`.
- **Response (201)**:
  ```json
  {
    "data": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "provider_id": "4bc85f64-5717-4562-b3fc-2c963f66afa7",
      "starts_at": "2026-08-15T09:00:00-04:00",
      "ends_at": "2026-08-15T18:00:00-04:00",
      "reason": "Vacaciones",
      "created_at": "2026-08-10T10:00:00-04:00",
      "updated_at": "2026-08-10T10:00:00-04:00"
    }
  }
  ```
- **Errores**: `401 unauthorized`, `403 forbidden` (CSRF), `404 provider_not_found`, `422 validation_error` / `422 non_existent_local_time` / `422 invalid_time_range`.

### 3.5 `DELETE /api/admin/time-off/{id}`
- **Request**: Elimina físicamente el bloqueo por ID.
- **Procesamiento**: Verifica existencia y pertenencia al `business_id` de la sesión.
- **Response (204)**: Sin contenido (`HTTP 204 No Content`).
- **Errores**: `401 unauthorized`, `403 forbidden` (CSRF), `404 time_off_not_found`.

---

## 4. Arquitectura de Query Keys e Invalidación Frontend

### 4.1 Definición Centralizada en `frontend/src/lib/api/queryKeys.ts`
Se actualiza `queryKeys.ts` para contener tanto las claves administrativas como las públicas del sistema:
```typescript
export interface AdminBookingsFilters {
  date?: string;
  status?: string;
  provider_id?: string;
}

export const adminQueryKeys = {
  dashboard: () => ['admin', 'dashboard'] as const,
  bookingsList: (filters?: AdminBookingsFilters) => ['admin', 'bookings', filters ?? {}] as const,
  bookingDetail: (bookingId: string) => ['admin', 'booking', bookingId] as const,
  providers: () => ['admin', 'providers'] as const,
  services: () => ['admin', 'services'] as const,
  providerDetail: (providerId: string) => ['admin', 'provider', providerId] as const,
  providerServices: (providerId: string) => ['admin', 'provider', providerId, 'services'] as const,
  providerAvailabilityRules: (providerId: string) => ['admin', 'provider', providerId, 'availability-rules'] as const,
  providerTimeOffs: (providerId: string) => ['admin', 'provider', providerId, 'time-offs'] as const,
};

export const publicQueryKeys = {
  availability: (serviceId?: string, date?: string, providerId?: string | null) =>
    ['public-availability', serviceId ?? null, date ?? null, providerId ?? null] as const,
  availabilityRoot: () => ['public-availability'] as const,
};
```
*(Se actualiza también `frontend/src/lib/api/availability.ts` para que `availabilityQueryKey` use de forma consistente `publicQueryKeys.availability`)*.

### 4.2 Estrategia de Invalidación
- Al guardar reglas semanales (`PUT availability-rules`):
  - `queryClient.invalidateQueries({ queryKey: adminQueryKeys.providerAvailabilityRules(providerId) })`
  - `queryClient.invalidateQueries({ queryKey: publicQueryKeys.availabilityRoot() })`
- Al crear o eliminar un bloqueo (`POST` / `DELETE time-off`):
  - `queryClient.invalidateQueries({ queryKey: adminQueryKeys.providerTimeOffs(providerId) })`
  - `queryClient.invalidateQueries({ queryKey: publicQueryKeys.availabilityRoot() })`

---

## 5. UI y Comportamiento en Frontend

### 5.1 Ruta y Navegación
- Ruta: `/admin/profesionales/:providerId/disponibilidad`.
- En `ProvidersPage.tsx`, cada fila de profesional incluye el botón "Disponibilidad" que navega a `/admin/profesionales/:providerId/disponibilidad`.
- La página carga el detalle del profesional mediante `adminQueryKeys.providerDetail(providerId)`.

### 5.2 Editor Semanal y Normalización de Intervalos
- Presenta los 7 días de la semana (Lunes a Domingo, `0..6`).
- Cada día permite activar/desactivar atención y agregar/quitar tramos horarios (`start_time`, `end_time`).
- **Normalización de Adyacentes antes de Guardar**:
  - Función de normalización `normalizeIntervals(intervals)`: ordena los tramos por `start_time` y fusiona aquellos que sean adyacentes (ej. `09:00–11:00` y `11:00–13:00` se fusionan a `09:00–13:00`).
  - Si existen solapamientos reales en el formulario (ej. `09:00–12:00` y `10:00–14:00`), muestra alerta visual de solapamiento en el día correspondiente y deshabilita el botón de guardar.
- **Feedback y Estados**:
  - Estado de carga inicial con Skeleton.
  - Botón "Guardar horario" deshabilitado si no hay cambios (dirty state) o si hay errores de validación.
  - Indicador de spinner durante el submit y prevención de reentrada.
  - Alerta de éxito tras guardar y alerta de error con reintento.

### 5.3 Gestión de Bloqueos y Ausencias (Time Off)
- Tabla listando bloqueos vigentes del profesional retornados por `GET /api/admin/time-off?provider_id={id}`.
- Botón "Añadir bloqueo" que abre `CreateTimeOffModal`:
  - Inputs para fecha/hora de inicio (`starts_at_local`) y fecha/hora de fin (`ends_at_local`) en formato civil local.
  - Campo de motivo opcional (`reason`).
  - Validación cliente de `starts_at_local < ends_at_local`.
  - Diálogo accesible (`role="dialog"`, `aria-modal="true"`, Focus Trap, tecla Escape para cerrar y restauración de foco al disparador).
- Botón de eliminación por bloqueo con diálogo de confirmación `ConfirmModal` y manejo de respuesta `204`.

### 5.4 Manejo de Errores y Autenticación (401)
- Si una query o mutación recibe `401 Unauthorized`, el cliente HTTP redirige de inmediato a `/admin/login` limpiando el estado de sesión.
- Estados de error de red ofrecen botón de reintento (`onRetry`).

---

## 6. Cambios Propuestos por Componente

### Backend

#### 1. Utilidades de Dominio: `backend/app/domain/time_utils.py` [MODIFY]
- Añadir `format_local_iso(dt: datetime, tz_name: str) -> str`.

#### 2. Schemas: `backend/app/schemas/availability_admin.py` [NEW]
- `AdminAvailabilityRuleItem`: `weekday: int (0..6)`, `start_time: time`, `end_time: time`. Validador `start_time < end_time`.
- `AdminAvailabilityRulesReplace`: `rules: list[AdminAvailabilityRuleItem]`. Validador de no solapamiento.
- `AdminTimeOffCreate`: `provider_id: UUID`, `starts_at_local: str`, `ends_at_local: str`, `reason: str | None`. Validador de normalización de espacios en `reason` (`""` / `"   "` -> `None`).
- `AdminTimeOffDetail`: `id: UUID`, `provider_id: UUID`, `starts_at: str`, `ends_at: str`, `reason: str | None`, `created_at: str`, `updated_at: str`.

#### 3. Services: `backend/app/services/availability_admin_service.py` [NEW]
- `get_provider_availability_rules(business_id: UUID, provider_id: UUID) -> list[AvailabilityRule]`
- `replace_provider_availability_rules(business_id: UUID, provider_id: UUID, rules: list[AdminAvailabilityRuleItem]) -> list[AvailabilityRule]`
  - `SELECT ... FOR UPDATE` sobre `Provider`.
- `list_provider_time_offs(business_id: UUID, provider_id: UUID, now_dt: datetime | None = None) -> list[TimeOff]`
  - Filtra `ends_at > now_dt`.
- `create_time_off(business_id: UUID, data: AdminTimeOffCreate) -> TimeOff`
  - Utiliza `create_aware_datetime` con `business.timezone` y `fold=0`.
  - Captura `NonExistentTimeError` y lanza `DomainError(422, "non_existent_local_time", ...)`.
  - Valida `starts_at_utc < ends_at_utc` (`invalid_time_range`).
- `delete_time_off(business_id: UUID, time_off_id: UUID) -> None`

#### 4. API Routers:
- `backend/app/api/admin/providers.py` [MODIFY]: Añadir `GET /{provider_id}/availability-rules` y `PUT /{provider_id}/availability-rules` (con `verify_origin`).
- `backend/app/api/admin/time_off.py` [NEW]: `GET /` (con `provider_id` obligatorio), `POST /` (con `verify_origin`), `DELETE /{id}` (status 204, con `verify_origin`).
- `backend/app/main.py` [MODIFY]: Registrar `admin_time_off.router` con prefijo `/api/admin/time-off`.

---

### Frontend

#### 1. API Client & Query Keys:
- `frontend/src/lib/api/queryKeys.ts` [MODIFY]: Añadir `adminQueryKeys.providerAvailabilityRules`, `adminQueryKeys.providerTimeOffs`, y `publicQueryKeys`.
- `frontend/src/lib/api/availability.ts` [MODIFY]: Reutilizar `publicQueryKeys.availability`.
- `frontend/src/lib/api/admin.ts` [MODIFY]:
  - Interfaces `AdminAvailabilityRuleItem`, `AdminTimeOffDetail`, `AdminTimeOffCreate`.
  - `getAdminProviderAvailabilityRules`, `replaceAdminProviderAvailabilityRules`.
  - `getAdminTimeOffs`, `createAdminTimeOff`, `deleteAdminTimeOff`.

#### 2. Features & Pages:
- `frontend/src/features/admin/ProviderAvailabilityPage.tsx` [NEW]: Página completa de disponibilidad por profesional con editor semanal, normalización de adyacentes y tabla de bloqueos.
- `frontend/src/features/admin/CreateTimeOffModal.tsx` [NEW]: Modal accesible para registrar bloqueos con campos `starts_at_local`, `ends_at_local` y `reason`.
- `frontend/src/features/admin/ProvidersPage.tsx` [MODIFY]: Añadir botón de acción "Disponibilidad" con enlace a `/admin/profesionales/:providerId/disponibilidad`.
- `frontend/src/App.tsx` [MODIFY]: Registrar ruta `/admin/profesionales/:providerId/disponibilidad`.

---

## 7. Matriz de Pruebas Extensiva

### 7.1 Backend API & Integración (`pytest`)

1. **Horarios Semanales (`test_admin_availability_rules_api.py`)**:
   - **Autenticación y CSRF**: Petición unauth responde 401; `PUT` sin `Origin` responde 403.
   - **Lectura**: `GET` retorna reglas ordenadas por `weekday ASC, start_time ASC` o `[]` si no hay reglas.
   - **Reemplazo Semanal (`PUT`)**:
     - Asignación de múltiples tramos por día (pausas y turnos partidos).
     - Payload vacío `{"rules": []}` limpia los horarios correctamente.
     - Tramos adyacentes (`09:00-11:00` y `11:00-13:00`) aceptados por el backend sin error.
     - `start_time >= end_time` responde `422`.
     - Solapamiento real en el mismo día responde `422` sin modificar la BD.
     - `weekday` fuera de `0..6` responde `422`.
     - Profesional de otro negocio responde `404 provider_not_found`.
   - **Concurrencia Determinista PostgreSQL y Cleanup**:
     - 2 hilos ejecutan `PUT` simultáneamente sobre el mismo profesional sincronizados con `threading.Barrier(2)` antes de `replace_provider_availability_rules` / `SELECT ... FOR UPDATE` (sin `sleep`).
     - Ambos retornan 200 y el estado final en DB es EXACTAMENTE el Payload A o el Payload B.
     - Cleanup riguroso al finalizar el test (rollback / eliminación de fixtures creados) garantizando cero residuos en la base de datos de test.

2. **Bloqueos y Ausencias (`test_admin_time_off_api.py`)**:
   - **Autenticación y CSRF**: 401 unauth, 403 sin Origin en mutaciones.
   - **Validación de Parámetros**: `GET` sin `provider_id` responde `422`.
   - **Filtro de Bloqueos Vigentes/Futuros**: Con reloj inyectado, retorna solo bloqueos con `ends_at > injected_now`. Bloqueos con `ends_at <= injected_now` no aparecen.
   - **Creación (`POST`)**:
     - Bloqueo de medio día, día completo y múltiples días cruzando medianoche.
     - **Normalización de Reason**: `reason` con espacios `"   "` o vacío `""` se persiste y retorna como `None`/`null`.
     - **Horario de Verano y Offsets de Chile**:
       - Fecha en horario estándar (invierno, ej. Julio): responde con offset `-04:00`.
       - Fecha en horario de verano (ej. Enero): responde con offset `-03:00`.
     - **Hora Inexistente en Salto DST**: Petición en hora de salto (gap) responde HTTP `422` con código `non_existent_local_time`.
     - **Hora Ambigua en DST**: Resuelve deterministamente con `fold=0`.
     - `starts_at_local >= ends_at_local` responde `422 invalid_time_range`.
     - `reason` > 240 caracteres responde `422`.
     - Profesional inexistente o de otro negocio responde `404 provider_not_found`.
     - Permite agendar `time_off` para profesionales inactivos.
   - **Eliminación (`DELETE`)**:
     - Eliminación exitosa responde `204 No Content` y borra el registro.
     - ID inexistente o de otro negocio responde `404 time_off_not_found`.
   - **Regresión Pública y Conservación de Reservas**:
     - Crear un bloqueo elimina de inmediato los slots afectados en `/api/public/availability`.
     - Eliminar el bloqueo restaura los slots en `/api/public/availability`.
     - Reservas preexistentes en el intervalo bloqueado se mantienen intactas en estado `confirmed`.

### 7.2 Frontend Component & Integration Tests (`vitest`)

1. **Disponibilidad por Profesional (`ProviderAvailability.test.tsx`)**:
   - Renderiza detalle del profesional, horario semanal y lista de bloqueos.
   - **Normalización**: Al ingresar `09:00-11:00` y `11:00-13:00`, la función de normalización los fusiona a `09:00-13:00` antes de enviar el `PUT`.
   - **Validación Visual**: Al ingresar tramos con solapamiento real, muestra alerta de error y bloquea el submit.
   - **Estados Asíncronos**: Skeletons en loading, feedback de spinner durante guardado, alerta de éxito tras guardar.
   - **Manejo de Errores y 401**: Simulación de error de red muestra alerta con reintento (`onRetry`); simulación de 401 dispara redirección a `/admin/login`.
   - **Creación y Eliminación de Bloqueos**:
     - Apertura de `CreateTimeOffModal` con Focus Trap, validación de fechas civiles y creación exitosa.
     - Eliminación de bloqueo tras confirmación en modal y actualización de lista ante respuesta 204.
     - Cierre de modales con Escape y devolución de foco al disparador.

---

## 8. Comandos de Verificación

```bash
# Backend checks
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run alembic check
git diff --check

# Frontend checks
cd ../frontend
npm run lint
npm run typecheck
npm run test -- --run
npm run build
```

---

## 9. Criterios de Aceptación

1. **Horarios Semanales**:
   - Es posible consultar y reemplazar el horario semanal de un profesional con soporte para turnos partidos y pausas.
   - El backend acepta intervalos adyacentes; el frontend los fusiona automáticamente antes de guardar.
   - Solapamientos reales en el mismo día son rechazados tanto en frontend como en backend con HTTP `422`.
   - Dos peticiones concurrentes `PUT` sobre el mismo profesional se serializan sin corrupción ni duplicados (exactamente Payload A o Payload B).
2. **Bloqueos (Time Off)**:
   - `POST /api/admin/time-off` recibe estrictamente `starts_at_local` y `ends_at_local` como fechas-horas civiles sin offset y `reason` opcional (normalizado a `None` si contiene solo espacios).
   - Se resuelven en `business.timezone` usando `create_aware_datetime(..., fold=0)`; horas inexistentes responden `422 non_existent_local_time`.
   - La respuesta expone timestamps con el offset de la zona IANA del negocio (`-03:00` / `-04:00`).
   - `GET /api/admin/time-off?provider_id={uuid}` exige `provider_id` obligatorio y retorna solo bloqueos con `ends_at > injected_now`.
   - `DELETE /api/admin/time-off/{id}` elimina el bloqueo y responde `204 No Content`.
3. **Integración con Disponibilidad Pública**:
   - Crear un bloqueo elimina inmediatamente los slots solapados en `/api/public/availability`.
   - Eliminar el bloqueo restaura los slots.
   - Las reservas preexistentes en el intervalo bloqueado se conservan intactas en estado `confirmed`.
4. **Experiencia y Accesibilidad**:
   - La interfaz en `/admin/profesionales/:providerId/disponibilidad` maneja estados loading, error/retry y 401.
   - Modales cumplen Focus Trap, cierre con Escape y restauración de foco accesible.
5. **Calidad de Código y Suites**:
   - Cero errores en `ruff`, `typecheck`, `pytest`, `vitest` y `build`.
