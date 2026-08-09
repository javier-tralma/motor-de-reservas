---
name: booking-domain
description: Implementar y revisar lógica de reservas profesionales con disponibilidad por servicio y profesional, horarios semanales, bloqueos, zonas horarias, creación idempotente, estados y prevención de solapamientos en PostgreSQL. Usar al modificar modelos, migraciones, endpoints, servicios o tests relacionados con availability, bookings, provider services, availability rules, time off, cambios de estado, concurrencia o fechas de citas.
---

# Booking domain

## Preparar el cambio

1. Leer `docs/PRODUCT.md`, `docs/ARCHITECTURE.md` y `docs/DATA_MODEL.md` desde la raíz del proyecto.
2. Identificar la regla de negocio y la invariante que protege.
3. Trazar el cambio desde contrato HTTP hasta servicio, consulta, constraint y consumidor.
4. Enumerar casos de borde antes de editar código.
5. Mantener el cambio dentro de P0/P1; registrar P2 sin implementarlo.

Si los documentos contradicen la implementación, no normalizar la discrepancia en silencio. Proponer cuál debe ser la fuente de verdad y actualizar documentación, tests y código de forma atómica.

## Preservar invariantes

- Limitar toda lectura y escritura por `business_id`.
- Exigir que servicio, profesional, reglas, bloqueos y reserva pertenezcan al mismo negocio.
- Exigir servicio y profesional activos al crear una reserva.
- Exigir que el profesional ofrezca el servicio.
- Calcular `ends_at` en servidor desde la duración vigente del servicio.
- Guardar snapshots de nombre, duración, precio y profesional para el histórico.
- Exigir que la cita completa esté contenida en disponibilidad laboral.
- Rechazar solape con `time_off` o reservas no canceladas.
- Tratar solo `cancelled` como capacidad libre.
- Revalidar al confirmar; nunca confiar en disponibilidad vista anteriormente.
- Mantener idempotencia por `(business_id, client_request_id)`.
- Conservar la reserva si falla el email después del commit.
- Impedir doble reserva en PostgreSQL, no solo con un `SELECT` previo.

## Modelar el tiempo

- Usar intervalos semiabiertos `[start, end)`.
- Detectar solape con `a_start < b_end and b_start < a_end`.
- Permitir adyacencia: `[09:00, 10:00)` y `[10:00, 11:00)` no chocan.
- Persistir instantes como `timestamptz` en UTC.
- Interpretar `AvailabilityRule.start_time` y `end_time` en `business.timezone`.
- Usar `America/Santiago` como zona inicial; no codificar `-03:00` o `-04:00`.
- Recibir un reloj inyectable en lógica testeable; no leer la hora global en mitad del cálculo.
- Construir ventanas desde fecha y hora civiles con una librería IANA, no suponiendo días UTC de 24 horas.
- Definir explícitamente el comportamiento ante una hora local inexistente o ambigua y cubrirlo con tests.

No convertir una regla semanal a UTC de forma permanente: su offset puede cambiar según la fecha.

## Calcular disponibilidad

Implementar el cálculo en un servicio de dominio puro o casi puro. Aplicar esta secuencia:

1. Cargar negocio, configuración y servicio activo.
2. Validar fecha contra pasado, anticipación mínima y horizonte.
3. Resolver profesionales activos que ofrecen el servicio; limitar por `provider_id` si existe.
4. Cargar todas las reglas del día local y permitir múltiples intervalos.
5. Construir intervalos zonificados para esa fecha.
6. Generar comienzos alineados a `slot_interval_minutes`.
7. Calcular el final desde `service.duration_minutes`.
8. Conservar candidatos totalmente contenidos en un intervalo laboral.
9. Cargar en consultas acotadas reservas y bloqueos que intersecten la ventana.
10. Eliminar candidatos con cualquier solape.
11. Devolver resultados ordenados y con offset de la zona del negocio.

Para «Cualquier profesional»:

- agrupar slots equivalentes por inicio y fin para no duplicar horas en UI;
- mantener internamente profesionales elegibles en orden estable;
- elegir de manera determinista al confirmar;
- no cambiar silenciosamente la hora solicitada;
- no añadir balanceo inteligente sin requisito aprobado.

Evitar una consulta por slot o por profesional. Cargar reglas, reservas y bloqueos en lotes acotados al día o ventana relevante.

## Crear una reserva

Ejecutar una operación transaccional corta:

1. Validar el comando y resolver el negocio desde contexto, no desde input público.
2. Buscar una reserva previa con la misma clave de idempotencia.
3. Si existe y el comando representa la misma operación, devolverla; si la clave fue reutilizada con otro payload, devolver conflicto.
4. Volver a cargar servicio, profesionales candidatos y reglas vigentes.
5. Recalcular el intervalo solicitado.
6. Intentar insertar una reserva `confirmed` con snapshots.
7. Hacer commit y traducir la exclusión conocida a `409 slot_unavailable`.
8. Despachar confirmación por email después del commit.
9. Registrar resultado del email sin PII completa.

No mantener la transacción abierta durante una llamada externa. No capturar todo `IntegrityError` como conflicto de horario: distinguir constraint de exclusión, idempotencia y errores inesperados.

## Proteger concurrencia en PostgreSQL

Mantener una exclusión GiST conceptualmente equivalente a:

```sql
EXCLUDE USING gist (
  provider_id WITH =,
  tstzrange(starts_at, ends_at, '[)') WITH &&
)
WHERE (status <> 'cancelled')
```

Habilitar `btree_gist` mediante migración. Probar la constraint en PostgreSQL real.

No sustituir esta garantía por locks en proceso, debounce de frontend, caché ni aislamiento asumido. La aplicación puede revalidar para mejorar UX; la base resuelve la carrera final.

## Cambiar estados

Permitir en P0:

```text
confirmed -> completed
confirmed -> cancelled
confirmed -> no_show
```

- Rechazar transiciones no definidas con conflicto explícito.
- Escribir timestamp correspondiente dentro de la misma transacción.
- Invalidar agenda, dashboard y disponibilidad después de una cancelación.
- Conservar filas históricas; no eliminar reservas.
- No reabrir reservas terminales sin una decisión de producto.

## Modificar horarios y bloqueos

- Validar `start_time < end_time`.
- Rechazar reglas semanales que crucen medianoche; dividirlas por día en P0.
- Permitir varios intervalos no solapados por día.
- Reemplazar el horario de un profesional en una sola transacción.
- Permitir que `time_off` cruce días y que varios bloqueos se solapen.
- Consultar el impacto en disponibilidad inmediatamente después de una mutación.
- No cancelar reservas existentes automáticamente al crear un bloqueo; detectar el conflicto y pedir una decisión administrativa explícita.

## Mantener contratos seguros

- No aceptar `business_id`, `ends_at`, precio, snapshots, estado o campos de entrega desde la API pública.
- Devolver instantes ISO 8601 con offset en respuestas y fechas civiles como `YYYY-MM-DD`.
- Usar códigos de error estables.
- Devolver `404` para recursos ajenos al negocio actual.
- Entregar en confirmación pública solo el resumen necesario; nunca IDs internos o metadata de email.
- Conservar datos personales del formulario en cliente al recibir `409`, refrescar slots y pedir nueva selección.

## Probar por matriz, no por anécdotas

Cubrir como mínimo:

### Intervalos

- encaje exacto antes y después de otro intervalo;
- solape por inicio y por final;
- contención completa en ambas direcciones;
- intervalos idénticos;
- duración que cabe exactamente al final de la jornada;
- duración que excede por un minuto;
- múltiples bloques laborales y pausa intermedia;
- granularidad que no divide exactamente una duración.

### Reglas

- profesional sin regla ese día;
- profesional inactivo o no asignado al servicio;
- servicio inactivo;
- bloqueo parcial, total y de varios días;
- reserva cancelada frente a confirmada, completada y no-show;
- anticipación mínima en el borde;
- fecha pasada y último día del horizonte.

### Zona horaria

- conversión local ↔ UTC;
- cambio de horario de verano en `America/Santiago`;
- hora ambigua o inexistente según política acordada;
- ejecución del servidor en una zona distinta sin cambiar resultados.

### Persistencia y carrera

- scoping y relaciones entre dos negocios;
- exclusión de solapamiento y permiso de adyacencia;
- dos transacciones concurrentes para el mismo slot: una sola confirma;
- misma clave idempotente repetida;
- misma clave con payload incompatible;
- fallo de email después de commit.

Usar PostgreSQL real para rangos, GiST y concurrencia. Usar reloj fijo y factories explícitas; no `sleep` ni dependencia de «hoy».

## Revisar antes de terminar

- Confirmar que ninguna consulta omitió `business_id`.
- Confirmar que el frontend no se volvió autoridad de reglas.
- Confirmar que la transacción no incluye red.
- Confirmar que constraints e índices tienen migración.
- Confirmar que los errores conocidos llegan como `409` y los inesperados no se ocultan.
- Confirmar que cancelar libera el slot y otros estados no.
- Confirmar que los tests incluyen bordes, timezone y concurrencia según el cambio.
- Ejecutar lint, tipos, tests y build pertinentes definidos en `AGENTS.md`.
- Actualizar documentos cuando cambie un contrato o una invariante.

