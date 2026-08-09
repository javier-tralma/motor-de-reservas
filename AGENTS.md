# Reglas del proyecto

Este repositorio contiene un MVP profesional de reservas para negocios que trabajan por cita. Estas reglas se aplican a todo el repositorio. Un `AGENTS.md` más cercano puede añadir reglas locales, pero no contradecir las invariantes de producto y datos sin una decisión explícita.

## 1. Orden de prioridades

Tomar decisiones en este orden:

1. Correctness.
2. Maintainability.
3. User experience.
4. Testability.
5. Performance medida.

No optimizar velocidad de implementación a costa de una reserva incorrecta, código difícil de mantener o una experiencia incompleta.

## 2. Fuentes de verdad

Leer antes de planificar cambios relevantes:

- `docs/PRODUCT.md`: alcance, flujos, reglas y criterios de aceptación.
- `docs/ARCHITECTURE.md`: límites, contratos y decisiones técnicas.
- `docs/DATA_MODEL.md`: esquema, constraints e invariantes persistentes.
- `docs/DESIGN.md`: interacción, contenido, responsive y accesibilidad.
- `.agents/skills/booking-domain/SKILL.md`: obligatorio para disponibilidad, reservas, horarios, bloqueos, estados, concurrencia o zonas horarias.

Si los documentos discrepan, detener la implementación del punto ambiguo, explicar el conflicto y proponer la corrección documental mínima. No elegir silenciosamente.

## 3. Alcance

P0 y P1 están definidos en `docs/PRODUCT.md`. Todo P2 está fuera de alcance hasta que P0 esté completo y verificado.

No añadir como «preparación»:

- pagos;
- roles o organizaciones;
- multi-tenancy visible;
- sucursales o capacidad múltiple;
- recordatorios o WhatsApp;
- sincronización de calendarios;
- colas o microservicios;
- abstracciones sin un consumidor actual.

Mantener `business_id` y scoping desde el inicio, pero una instalación sigue representando un negocio.

## 4. Stack y límites técnicos

### Frontend

- React, TypeScript y Vite.
- React Router.
- TanStack Query para datos remotos.
- React Hook Form y Zod para formularios.
- Tailwind CSS y tokens CSS.
- FullCalendar solo en administración.
- Vitest, Testing Library y Playwright.

No usar `any` salvo una integración externa que lo haga inevitable; aislarlo y justificarlo con comentario. No duplicar respuestas del servidor en stores globales.

### Backend

- FastAPI, Pydantic, SQLAlchemy 2, PostgreSQL y Alembic.
- Pytest para tests.
- Ruff para lint y formato.
- Argon2id para hashes de contraseña.
- Resend detrás de `EmailService`.

No soportar SQLite como sustituto de PostgreSQL en tests de integración. No llamar Resend directamente desde rutas o servicios de dominio.

### Dependencias

Antes de añadir una dependencia:

1. comprobar que el stack actual no resuelve el problema;
2. explicar propósito, coste y alternativa;
3. elegir una opción mantenida y acotada;
4. actualizar lockfile y documentación relevante;
5. ejecutar las verificaciones afectadas.

## 5. Flujo de trabajo para agentes

Para cada tarea:

1. Inspeccionar implementación, tests, migraciones y documentos relacionados.
2. Definir el comportamiento esperado y los casos de borde.
3. Identificar módulos afectados y el cambio mínimo coherente.
4. Actualizar primero tests de la regla cuando sea razonable.
5. Implementar una porción vertical terminada.
6. Ejecutar verificaciones proporcionales al riesgo.
7. Revisar el diff completo y cambios no relacionados.
8. Resumir resultado, decisiones, tests ejecutados y riesgos restantes.

No afirmar que una tarea está terminada si falla una verificación relevante. No borrar, revertir ni reformatear cambios ajenos no relacionados.

## 6. Arquitectura de código

- Rutas FastAPI: contratos HTTP, dependencias y traducción de errores.
- Servicios: casos de uso, reglas y límites de transacción.
- Repositorios: persistencia y consultas complejas, sin reglas escondidas.
- Modelos ORM: estructura persistente; no son contratos HTTP.
- Schemas Pydantic: entrada y salida explícitas.
- Features React: UI, queries, mutations y estado efímero cohesivo.
- Componentes compartidos: primitivas visuales reutilizadas de verdad.

Evitar handlers extensos, módulos «utils» sin cohesión, ciclos de importación, commits dentro de repositorios y lógica de negocio duplicada entre frontend y backend.

## 7. Invariantes del dominio

- Usar intervalos semiabiertos `[inicio, fin)`.
- Persistir instantes en UTC; interpretar reglas semanales con la zona IANA del negocio.
- Zona inicial: `America/Santiago`; nunca codificar un offset fijo.
- El profesional debe estar activo y ofrecer el servicio activo.
- Una reserva debe caber completamente en disponibilidad laboral.
- Una reserva no puede solaparse con `time_off` ni otra reserva no cancelada.
- El servidor calcula `ends_at`, duración, precio y snapshots.
- Disponibilidad consultada nunca autoriza por sí sola una reserva: revalidar al crear.
- PostgreSQL debe impedir conflictos concurrentes mediante exclusión de rangos.
- `cancelled` es el único estado que libera capacidad.
- Toda operación se limita por `business_id`.
- Una clave de idempotencia repetida no crea una segunda reserva.
- Un fallo de email no revierte una reserva confirmada.

No debilitar una constraint para hacer pasar un test. Corregir la implementación o documentar una decisión de dominio.

## 8. Base de datos y migraciones

- Toda modificación de esquema lleva migración Alembic.
- No editar una migración aplicada en entornos compartidos; añadir otra.
- Mantener upgrade determinista y downgrade cuando sea seguro y razonable.
- Probar migraciones contra PostgreSQL limpio.
- Añadir constraints de base aunque exista validación en Pydantic.
- Mantener FKs y consultas protegidas contra relaciones entre negocios.
- Usar eager loading o consultas específicas para evitar N+1; no cargar tablas completas para calcular un día.
- No hacer llamadas externas con una transacción abierta.
- Seeds son idempotentes y están separados de migraciones estructurales.

Al tocar reservas o disponibilidad, probar la exclusión GiST y la carrera entre dos transacciones reales.

## 9. API y errores

- No devolver modelos ORM directamente.
- No aceptar campos controlados por servidor como `ends_at`, estado, precio o `business_id` en la API pública.
- Mantener el envelope de error definido en `docs/ARCHITECTURE.md`.
- Usar códigos de error estables; el frontend no analiza mensajes humanos.
- Traducir conflictos conocidos de base de datos a `409`, no a `500`.
- No exponer existencia de recursos de otro negocio.
- No incluir stack traces, secretos o datos personales completos en respuestas o logs.

Los cambios incompatibles de contrato requieren actualizar consumidores, tests y documentación en la misma tarea.

## 10. Frontend y experiencia

- La reserva pública es mobile-first y no usa una grilla de calendario compleja.
- Mantener selección y datos válidos al volver entre pasos o recibir `409`.
- Implementar loading, vacío, error, éxito y disabled en cada interacción asíncrona.
- No persistir datos personales del formulario en `localStorage`.
- Formatear con `Intl`, locale `es-CL` y zona del negocio.
- HTML semántico, labels, foco visible y navegación por teclado son parte del terminado.
- El color no es el único indicador.
- No introducir texto genérico, lorem ipsum ni métricas inventadas en la demo.

Una UI visualmente atractiva que no maneja errores o teclado está incompleta.

## 11. Seguridad y privacidad

- Secretos solo por variables de entorno.
- Contraseñas con Argon2id; nunca registrar credenciales o tokens.
- Preferir cookie `HttpOnly`, `Secure` en producción y `SameSite=Lax` para sesión admin.
- CORS y orígenes permitidos explícitos.
- Validar longitud y formato en servidor.
- Minimizar PII en logs; enmascarar email y teléfono.
- No enviar datos personales a analytics en P0.
- Aplicar rate limiting a login y creación pública antes de exponer producción.

## 12. Testing obligatorio

### Cambios de dominio

Como mínimo:

- unitarios de intervalos y regla nueva;
- integración con PostgreSQL de constraints/consulta;
- regresión del caso reportado;
- bordes de zona horaria si toca fechas u horas;
- concurrencia si toca creación o estados que bloquean.

### Cambios de API

- camino feliz;
- entrada inválida;
- recurso de otro negocio;
- autenticación si corresponde;
- código y cuerpo de error esperado.

### Cambios de frontend

- estado normal;
- loading, vacío y error;
- interacción por teclado relevante;
- recuperación ante conflicto;
- viewport móvil si cambia layout.

Preferir factories/builders explícitos y un reloj inyectable. No usar esperas reales ni depender de la fecha del sistema.

## 13. Comandos de verificación

Usar los scripts reales del repositorio. La foundation debe proporcionar equivalentes a:

```text
frontend:
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  npm run e2e

backend:
  ruff check .
  ruff format --check .
  pytest
  alembic upgrade head
```

Durante desarrollo se puede ejecutar una selección rápida, pero antes de cerrar un hito ejecutar la suite completa pertinente con PostgreSQL. Si un comando aún no existe, no fingir su ejecución: crearlo en Foundation o declarar la limitación.

## 14. Definición de terminado

Una tarea está terminada cuando:

- cumple criterios de aceptación y casos de borde acordados;
- conserva todas las invariantes;
- tiene migración si cambió persistencia;
- incluye tests que fallaban antes y pasan después cuando aplica;
- maneja estados de UI y accesibilidad correspondientes;
- no añade secretos, datos demo accidentales ni código muerto;
- lint, tipos, tests y build relevantes pasan;
- documentos y `.env.example` están actualizados si cambió un contrato;
- el diff final no incluye cambios no relacionados;
- el resumen final distingue claramente lo hecho de lo pendiente.

## 15. Cambios de arquitectura

Antes de cambiar stack, límites, auth, tenancy, estrategia de email, modelo de tiempo o garantía de concurrencia:

1. describir el problema concreto;
2. presentar alternativas y trade-offs;
3. identificar migración y compatibilidad;
4. registrar una ADR en `docs/decisions/` si se aprueba;
5. actualizar los documentos fuente en la misma entrega.

No ejecutar una decisión arquitectónica irreversible basándose solo en conveniencia inmediata.

