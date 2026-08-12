# Implementation Plan — Milestone 6: Configuración Administrativa de Servicios y Profesionales (Actualizado v4)

Planificación técnica detallada para la porción vertical completa del **Milestone 6**, permitiendo la administración del catálogo de servicios, profesionales y asignaciones de servicios por profesional.

> [!IMPORTANT]
> **ESTADO DE PLANIFICACIÓN**: Este documento es exclusivamente un plan. No se ha escrito código de producto, migraciones ni pruebas en esta fase. Se requiere aprobación explícita antes de comenzar la ejecución.

---

## Precondiciones y Estado del Repositorio

- **Limpieza del Repositorio**: `git status --short` verificado como limpio.
- **Etiqueta Git**: Tag `milestone-5` presente en el repositorio.
- **Esquema de Base de Datos**: Los modelos `Service`, `Provider` y `ProviderService` ya existen con constraints compuestas de tenant `(business_id, id)`. **No se requieren nuevas migraciones Alembic**.

---

## Decisions & Design Intent

### 1. Reutilización del Modelo de Datos Existente
Los modelos SQLAlchemy y tablas PostgreSQL ya cuentan con la estructura necesaria:
- `services`: `id`, `business_id`, `name`, `description`, `duration_minutes`, `price_amount`, `is_active`, `sort_order`, `created_at`, `updated_at`.
- `providers`: `id`, `business_id`, `name`, `email`, `phone`, `bio`, `is_active`, `sort_order`, `created_at`, `updated_at`.
- `provider_services`: `business_id`, `provider_id`, `service_id`, `created_at` con clave primaria compuesta `(provider_id, service_id)` y FKs compuestas que restringen la pertenencia al mismo negocio.

### 2. Desactivación Físicamente Conservadora (Sin Delete Físico de Catálogo)
- Desde la interfaz administrativa, los servicios y profesionales **nunca se eliminan**. Se edita `is_active = false`.
- Las reservas históricas retienen sus snapshots (`service_name_snapshot`, `duration_minutes_snapshot`, `price_amount_snapshot`, `provider_name_snapshot`).
- En la reserva pública, los ítems inactivos no se muestran ni se pueden reservar.
- Ordenamiento predeterminado para listados: `sort_order ASC, name ASC`.

### 3. Asignación Concurrente, Atómica y Validación de IDs Duplicados (`PUT /api/admin/providers/{id}/services`)
- En `PUT /api/admin/providers/{id}/services`, se carga primero el profesional del negocio con `SELECT ... FOR UPDATE`:
  `select(Provider).filter_by(id=provider_id, business_id=business_id).with_for_update()`.
- **Serialización Concurrente y Criterio Determinista**:
  - Al tomar un bloqueo exclusivo en la fila del `Provider`, se serializan dos peticiones de reemplazo concurrentes sobre el mismo profesional, incluso cuando el conjunto previo de servicios asignados esté completamente vacío (`provider_services` no tenía filas preexistentes).
  - Ambos reemplazos válidos responden con éxito HTTP `200`.
  - Al finalizar ambas transacciones, el conjunto persistido resultante en `provider_services` debe ser **exactamente uno de los dos payloads completos enviados** (Payload A o Payload B). Nunca puede quedar una unión parcial, una intersección accidental ni duplicados.
  - La prueba de integración utilizará dos sesiones independientes de PostgreSQL coordinadas por una `threading.Barrier(2)` inmediatamente antes de llamar a `replace_provider_services` / tomar el `SELECT FOR UPDATE`, sin el uso de `sleep`.
- Dentro de la misma transacción:
  1. Validar unicidad en `service_ids` en la capa Pydantic (`@field_validator`). Si existen IDs duplicados (ej: `["s1", "s1"]`), responde HTTP `422` con el envelope estándar de validación sin consultar ni fallar en PostgreSQL.
  2. Si `service_ids` no está vacío, verificar que todos los servicios pertenezcan al negocio activo. Si alguno no existe o pertenece a otro negocio, responde `404 service_not_found` y hace `rollback()`.
  3. Eliminar asignaciones anteriores en `provider_services` e insertar las nuevas relaciones.
  4. Ejecutar `commit()`.
- Se permite enviar la lista vacía `[]` para desasignar todos los servicios de un profesional.

### 4. Conservación del Contrato Existente de `GET /api/admin/providers`
- Se adopta la **Opción 1 (Recomendada)** para minimizar la exposición innecesaria de PII:
  - `GET /api/admin/providers` se mantiene minimalista devolviendo `{id, name, is_active}` (usado por selectores y filtros de reservas).
  - Se añade `GET /api/admin/providers/{id}` para obtener el detalle completo de un profesional (`id, name, email, phone, bio, is_active, sort_order, created_at, updated_at`) únicamente al abrir su formulario de edición.
  - Se añade `GET /api/admin/providers/{id}/services` para obtener los `service_ids` asignados al profesional.
- Se documentarán estos 2 nuevos contratos en `docs/ARCHITECTURE.md`.

### 5. Semántica de PATCH, Validación y Normalización de Teléfono
- **Validación y Normalización de Teléfono**:
  - Tras `.strip()`, una cadena vacía `""` se normaliza a `None`/`null`.
  - Un valor no vacío de teléfono debe tener entre 7 y 32 caracteres y contener exclusivamente formato telefónico válido: dígitos, espacios, `+`, `-`, `(` y `)`. Regex: `^[0-9+() -]{7,32}$`.
  - Un formato de teléfono inválido (ej: `"abc"`, `"+569 abc"`, `"12345"` por tener menos de 7 caracteres) rechaza la petición con HTTP `422` y el envelope estándar. Valores válidos con espacios o símbolos telefónicos como `"+56912345678"` o `"+56 9 1234 5678"` son aceptados.
- **Semántica de PATCH**:
  - Los schemas de actualización (`AdminServiceUpdate` y `AdminProviderUpdate`) deben rechazar payloads vacíos `{}` con HTTP `422` (validando `@model_validator` o `len(self.model_fields_set) > 0`).
  - La capa de servicio utiliza `model_fields_set` para evaluar qué campos actualizar, **nunca comprobaciones por truthiness (`if value:`)**, de modo que valores legítimos falsy como `is_active=False`, `sort_order=0` o `description=""` se persistan correctamente.
  - El valor `null` es aceptado **únicamente** para `email` y `phone` en `AdminProviderUpdate` para permitir su limpieza. Los campos no anulables rechazan `null`.
  - Normalización: textos sufren `.strip()`. En el frontend, valores vacíos de email/teléfono se convierten a `null`/`None`, manteniendo la misma protección en el backend.

### 6. Tratamiento y Presentación de Servicios Inactivos Asignados
- En la UI del modal de asignaciones por profesional:
  - Se listan todos los servicios del negocio indicando con un badge `(Inactivo)` aquellos donde `is_active = false`.
  - Si un profesional ya tenía asignado un servicio que posteriormente fue desactivado, la casilla permanecerá marcada a menos que el administrador decida desmarcarla explícitamente.
  - Se confirma explícitamente que conservar servicios inactivos en las asignaciones no altera la reserva pública, ya que el motor de disponibilidad exige `Service.is_active == True AND Provider.is_active == True`.

---

## Detailed API Contracts

Todas las rutas administrativas requieren cookie HttpOnly de sesión `booking_admin_session`. Las peticiones mutativas (`POST`, `PATCH`, `PUT`) exigen el encabezado `Origin` coincidente con `FRONTEND_URL`. Los schemas Pydantic usan `ConfigDict(extra="forbid")`.

### 1. `GET /api/admin/services`
Retorna todos los servicios del negocio (activos e inactivos), ordenados por `sort_order ASC, name ASC`.
- **Respuesta 200**:
  ```json
  {
    "data": [
      {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "name": "Corte de Cabello",
        "description": "Corte clásico con lavado y peinado",
        "duration_minutes": 30,
        "price_amount": 15000,
        "is_active": true,
        "sort_order": 0,
        "created_at": "2026-08-10T10:00:00-04:00",
        "updated_at": "2026-08-10T10:00:00-04:00"
      }
    ]
  }
  ```

### 2. `POST /api/admin/services`
Crea un nuevo servicio para el negocio.
- **Request Body** (`AdminServiceCreate`):
  ```json
  {
    "name": "Coloración Capilar",
    "description": "Tinte completo con hidratación",
    "duration_minutes": 90,
    "price_amount": 45000,
    "is_active": true,
    "sort_order": 1
  }
  ```
- **Validaciones Pydantic**:
  - `name`: `str`, min_length=1, max_length=120, `.strip()`.
  - `description`: `str`, max_length=1000, default `""`.
  - `duration_minutes`: `int`, `ge=5`, `le=720`.
  - `price_amount`: `int`, `ge=0`.
  - `is_active`: `bool`, default `True`.
  - `sort_order`: `int`, `ge=0`, default `0`.
- **Respuesta 201**: `{"data": AdminServiceDetail}`.

### 3. `PATCH /api/admin/services/{id}`
Edita parcialmente un servicio existente.
- **Request Body** (`AdminServiceUpdate`):
  Campos opcionales (`name`, `description`, `duration_minutes`, `price_amount`, `is_active`, `sort_order`).
  - Si el body es `{}` -> Responde HTTP `422` ("At least one field must be provided").
  - `is_active=false` y `sort_order=0` se persisten correctamente mediante `model_fields_set`.
- **Respuesta 200**: `{"data": AdminServiceDetail}`.
- **Respuesta 404**: `{"error": {"code": "service_not_found", "message": "Servicio no encontrado", ...}}` si el ID no existe o pertenece a otro negocio.

### 4. `GET /api/admin/providers`
Retorna la lista minimalista de profesionales del negocio (activos e inactivos) para selectores y filtros.
- **Respuesta 200**:
  ```json
  {
    "data": [
      {
        "id": "4bc85f64-5717-4562-b3fc-2c963f66afa7",
        "name": "Camila Rojas",
        "is_active": true
      }
    ]
  }
  ```

### 5. `GET /api/admin/providers/{id}`
Retorna el detalle completo de un profesional para edición (minimizando PII en listados generales).
- **Respuesta 200**:
  ```json
  {
    "data": {
      "id": "4bc85f64-5717-4562-b3fc-2c963f66afa7",
      "name": "Camila Rojas",
      "email": "camila@estudionomada.cl",
      "phone": "+56912345678",
      "bio": "Especialista en cortes y estilismo.",
      "is_active": true,
      "sort_order": 0,
      "created_at": "2026-08-10T10:00:00-04:00",
      "updated_at": "2026-08-10T10:00:00-04:00"
    }
  }
  ```
- **Respuesta 404**: `{"error": {"code": "provider_not_found", "message": "Profesional no encontrado", ...}}`.

### 6. `POST /api/admin/providers`
Crea un nuevo profesional para el negocio.
- **Request Body** (`AdminProviderCreate`):
  ```json
  {
    "name": "Gonzalo Valenzuela",
    "email": "gonzalo@estudionomada.cl",
    "phone": "+56987654321",
    "bio": "Barbero con 8 años de experiencia.",
    "is_active": true,
    "sort_order": 1
  }
  ```
- **Validaciones Pydantic**:
  - `name`: `str`, min_length=1, max_length=120, `.strip()`.
  - `email`: `EmailStr | None`, default `None`.
  - `phone`: `str | None`, normalización post `.strip()` (`""` -> `None`), validador regex `^[0-9+() -]{7,32}$` si no es `None`.
  - `bio`: `str`, max_length=1000, default `""`.
  - `is_active`: `bool`, default `True`.
  - `sort_order`: `int`, `ge=0`, default `0`.
- **Respuesta 201**: `{"data": AdminProviderDetail}`.

### 7. `PATCH /api/admin/providers/{id}`
Edita parcialmente un profesional existente.
- **Request Body** (`AdminProviderUpdate`):
  Campos opcionales (`name`, `email`, `phone`, `bio`, `is_active`, `sort_order`).
  - Body `{}` responde HTTP `422`.
  - `phone` inválido (ej: `"abc"`, `"+569 abc"`, `"12345"`) responde HTTP `422`.
  - `email: null` y `phone: null` limpian explícitamente el campo en DB.
  - Campos no anulables (`name`, `bio`, `is_active`, `sort_order`) rechazan `null` con HTTP `422`.
- **Respuesta 200**: `{"data": AdminProviderDetail}`.
- **Respuesta 404**: `{"error": {"code": "provider_not_found", ...}}`.

### 8. `GET /api/admin/providers/{id}/services`
Obtiene los `service_ids` asignados al profesional.
- **Respuesta 200**:
  ```json
  {
    "data": {
      "provider_id": "4bc85f64-5717-4562-b3fc-2c963f66afa7",
      "service_ids": ["3fa85f64-5717-4562-b3fc-2c963f66afa6"]
    }
  }
  ```

### 9. `PUT /api/admin/providers/{id}/services`
Reemplaza de forma atómica e idempotente el conjunto de servicios asignados a un profesional.
- **Request Body** (`AdminProviderServicesReplace`):
  ```json
  {
    "service_ids": [
      "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "8aa85f64-5717-4562-b3fc-2c963f66afa9"
    ]
  }
  ```
- **Validaciones Pydantic**:
  - `service_ids`: `list[UUID]`, validador de unicidad que rechaza duplicados con HTTP `422` antes de tocar la base de datos.
- **Procesamiento de Negocio**:
  1. Ejecuta `SELECT ... FOR UPDATE` sobre el `Provider` para serializar concurrencia. Si no existe o es de otro negocio -> `404 provider_not_found`.
  2. Verifica pertenencia de todos los `service_ids` al negocio. Si alguno falla -> `404 service_not_found`.
  3. Elimina asignaciones previas e inserta los nuevos registros `ProviderService`.
  4. Realiza `commit()`.
- **Respuesta 200**: `{"data": {"provider_id": "...", "service_ids": [...]}}`.

---

## Proposed Changes & File Modifications

### Documentation
- **[docs/ARCHITECTURE.md](file:///home/jtralma/Desarrollo/Sistema%20de%20reservas/docs/ARCHITECTURE.md)**: Actualizar la sección 6 (Contratos HTTP) incluyendo `GET /api/admin/providers/{id}` y `GET /api/admin/providers/{id}/services`.

### Backend Components

#### 1. Schemas: `backend/app/schemas/catalog_admin.py` [NEW]
- `AdminServiceCreate`, `AdminServiceUpdate` (validador de body no vacío), `AdminServiceDetail`.
- `AdminProviderCreate`, `AdminProviderUpdate` (validador de body no vacío, validador de teléfono regex `^[0-9+() -]{7,32}$` y `null` permitido solo en email/phone), `AdminProviderDetail`, `AdminProviderListItem` (`id`, `name`, `is_active`).
- `AdminProviderServicesReplace` (validador de unicidad en `service_ids`), `AdminProviderServicesDetail`.

#### 2. Services: `backend/app/services/catalog_service.py` [NEW]
- `list_services(business_id)`: Orden `sort_order ASC, name ASC`.
- `create_service(business_id, data)`
- `update_service(business_id, service_id, data)`: Usa `model_fields_set`.
- `list_providers(business_id)`: Retorna `AdminProviderListItem` con `sort_order ASC, name ASC`.
- `get_provider_detail(business_id, provider_id)`: Retorna `AdminProviderDetail`.
- `create_provider(business_id, data)`
- `update_provider(business_id, provider_id, data)`: Usa `model_fields_set`.
- `get_provider_services(business_id, provider_id)`
- `replace_provider_services(business_id, provider_id, service_ids)`: `SELECT ... FOR UPDATE` sobre Provider.

#### 3. API Routers:
- `backend/app/api/admin/services.py` [NEW]: `GET /`, `POST /`, `PATCH /{id}` (con `verify_origin`).
- `backend/app/api/admin/providers.py` [MODIFY]: `GET /`, `GET /{id}`, `POST /`, `PATCH /{id}`, `GET /{id}/services`, `PUT /{id}/services` (con `verify_origin` en mutaciones).
- `backend/app/main.py` [MODIFY]: Registrar `admin_services`.

---

### Frontend Components

#### 1. Client & Query Keys
- `frontend/src/lib/api/admin.ts` [MODIFY]:
  - `getAdminServices()`
  - `createAdminService()`
  - `updateAdminService()`
  - `getAdminProviders()` (mantiene lista minimalista)
  - `getAdminProviderDetail(id)`
  - `createAdminProvider()`
  - `updateAdminProvider()`
  - `getAdminProviderServices(id)`
  - `replaceAdminProviderServices(id, serviceIds)`
- `frontend/src/lib/api/queryKeys.ts` [MODIFY]:
  - `adminQueryKeys.services()`
  - `adminQueryKeys.providers()`
  - `adminQueryKeys.providerDetail(providerId)`
  - `adminQueryKeys.providerServices(providerId)`

#### 2. Layout & Routes
- `frontend/src/features/admin/AdminLayout.tsx` [MODIFY]: Activar enlaces "Servicios" (`/admin/servicios`) y "Profesionales" (`/admin/profesionales`).
- `frontend/src/App.tsx` [MODIFY]: Registrar rutas `/admin/servicios` y `/admin/profesionales`.

#### 3. Features & Pages
- `frontend/src/features/admin/ServicesPage.tsx` [NEW]: Listado de servicios, filtro de estado, precios en `es-CL`, modal/drawer crear/editar.
- `frontend/src/features/admin/ProvidersPage.tsx` [NEW]: Listado de profesionales con acciones para editar y "Asignar servicios".
- `frontend/src/features/admin/AssignServicesModal.tsx` [NEW]:
  - **Accesibilidad**: Diálogo semántico con `role="dialog"`, `aria-modal="true"`, atrapado de foco (Focus Trap), foco inicial seguro, cierre con `Escape`, devolución de foco al disparador.
  - **Estados propios**: Skeletons de carga propios para el detalle del profesional y la lista de asignaciones; estado de error con reintento.
  - **Prevención de Doble Submit**: Botones e inputs deshabilitados durante el estado de submit pendiente.
  - **Servicios Inactivos**: Muestra badge `(Inactivo)` en servicios desactivados sin desmarcarlos automáticamente.

---

## Implementation Sequence (Vertical Slices)

### Slice 1: Documentation & Backend Services API & Tests
1. Actualizar `docs/ARCHITECTURE.md`.
2. Crear `catalog_admin.py` schemas y `catalog_service.py`.
3. Crear router `backend/app/api/admin/services.py` y registrar en `main.py`.
4. Escribir tests en `backend/tests/api/test_admin_services_api.py` (incluyendo body vacío 422, `is_active=false` y `sort_order=0`).

### Slice 2: Backend Providers API & Atomic Assignment Endpoint & Tests
1. Actualizar router `backend/app/api/admin/providers.py` con `GET /{id}`, `POST /`, `PATCH /{id}`, `GET /{id}/services` y `PUT /{id}/services`.
2. Implementar `replace_provider_services` con `SELECT FOR UPDATE` y validaciones.
3. Escribir tests en `backend/tests/api/test_admin_providers_api.py`:
   - `GET /providers` minimalista vs `GET /providers/{id}` detalle.
   - Validación de teléfono: formatos inválidos (ej: `"abc"`, `"+569 abc"`, `"12345"`) responden 422; teléfono válido (ej: `"+56912345678"`, `"+56 9 1234 5678"`) es aceptado; teléfono vacío o con espacios se normaliza a `null`.
   - Limpieza de `email` y `phone` enviando `null`.
   - Duplicados en `service_ids` respondiendo HTTP `422`.
   - Asignar `service_id` de otro negocio respondiendo HTTP `404` sin alterar DB.
   - **Test de Concurrencia PostgreSQL Determinista**: 2 hilos que ejecutan `PUT /services` simultáneamente coordinados con `threading.Barrier(2)` inmediatamente antes de llamar a `replace_provider_services` / tomar el lock `FOR UPDATE` (sin `sleep`). Se verifica que ambas peticiones retornan 200 y que el estado persistido final en `provider_services` es EXACTAMENTE igual al Payload A completo o al Payload B completo (nunca unión, intersección ni duplicados).
   - Regresión: Servicio o profesional inactivo no aparece en disponibilidad pública.

### Slice 3: Frontend Catalog Management & Modal Accessibility
1. Actualizar `admin.ts` y `queryKeys.ts`.
2. Implementar `ServicesPage.tsx`.
3. Implementar `ProvidersPage.tsx` y `AssignServicesModal.tsx` (cumpliendo accesibilidad completa de `ConfirmModal`).
4. Activar rutas en `AdminLayout.tsx` y `App.tsx`.
5. Escribir tests de frontend en `frontend/src/features/admin/Catalog.test.tsx`.

---

## Verification Matrix & Test Plan

### Backend Unit & API Tests (`pytest`)
- **Autenticación y CSRF**: Peticiones unauth devuelven 401; mutaciones sin `Origin` devuelven 403.
- **Servicios CRUD**: Creación y edición válidas; validación de `duration_minutes` (5..720) y `price_amount` (>=0); rechazo con 422 ante campos extra o body vacío; persistencia correcta de `is_active=false` y `sort_order=0`; scoping por `business_id` (404 ante ID ajeno); desactivación preservando registro en DB.
- **Profesionales CRUD**: `GET /providers` lista mínima; `GET /providers/{id}` detalle completo; edición con `model_fields_set`; asignación de `email: null` o `phone: null` limpia el campo; teléfono inválido (ej: `"abc"`, `"+569 abc"`, `"12345"`) responde 422; teléfono en formato internacional con espacios aceptado.
- **Asignación Atómica y Concurrente (`PUT /services`)**:
  - Reemplazo exitoso por conjunto de servicios o lista vacía `[]`.
  - Envío de `service_ids` duplicados responde `422` (validado en Pydantic).
  - Intento de asignar un `service_id` de otro negocio devuelve `404` y no modifica la DB.
  - **Concurrencia Determinista**: 2 hilos que ejecutan `PUT /services` simultáneamente sobre el mismo profesional coordinados por `threading.Barrier(2)` sin `sleep`. Ambos retornan 200 y el estado final en DB coincide exactamente con el Payload A o con el Payload B.
- **Regresión Pública**: Servicio o profesional con `is_active = false` es excluido del endpoint de disponibilidad pública `/api/public/availability`.

### Frontend Component & Integration Tests (`vitest`)
- **Visualización y Filtros**: Listados de servicios y profesionales con badges activo/inactivo y precios en `es-CL`.
- **Formularios Zod**: Validación en cliente de campos requeridos, duraciones, precios y teléfonos.
- **Modal de Asignación**: Focus Trap, selección/deselección de checkboxes, badge `(Inactivo)` para servicios desactivados, submit con reentrada bloqueada, estados loading/error propios y refresco de TanStack Query.
- **Accesibilidad**: Navegación por teclado, foco devuelto al disparador tras cerrar modal.

---

## Verification Commands

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

## Out of Scope for Milestone 6 (Deferred to Milestone 7+)

- Configuración de horarios semanales por profesional (`availability_rules`).
- Bloqueos de agenda (`time_off`).
- Calendario administrativo interactivo (FullCalendar).
- Creación manual de reservas administrativas (`source = admin`).
- Reprogramación de citas.
- Integraciones externas adicionales o notificaciones por Resend nuevas.
