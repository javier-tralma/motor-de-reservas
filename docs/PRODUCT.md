# Producto: motor de reservas para negocios por cita

## 1. Propósito

Construir un MVP profesional y reutilizable para negocios que atienden mediante citas: peluquerías, barberías, consultas, talleres, estudios y servicios profesionales.

La demostración inicial usa un negocio ficticio —**Estudio Nómada**, en Viña del Mar—, pero el dominio y la interfaz no contienen conceptos exclusivos de peluquería. Una instalación sirve a un negocio. Todas las entidades incluyen `business_id` para facilitar una futura evolución a multi-tenancy, sin exponer organizaciones, cambio de negocio ni facturación SaaS en el MVP.

El producto debe demostrar más que un CRUD: disponibilidad correcta, concurrencia segura, manejo explícito de zonas horarias, una experiencia pública cuidada y una operación administrativa realista.

## 2. Principios y prioridades

En caso de conflicto, decidir en este orden:

1. **Correctness:** nunca confirmar una cita inválida o superpuesta.
2. **Maintainability:** reglas de negocio explícitas, cohesivas y testeables.
3. **User experience:** reservar debe ser claro, rápido y confiable.
4. **Testability:** la lógica crítica debe poder probarse sin navegador ni servicios externos.
5. **Performance:** optimizar después de medir, salvo índices y consultas obviamente necesarios.

Una funcionalidad no entra al MVP si debilita una de estas prioridades o retrasa el flujo principal.

## 3. Usuarios

### Cliente

Persona que quiere reservar un servicio desde el teléfono o computador, sin crear una cuenta.

Necesita:

- entender servicios, duración y precio;
- elegir profesional o «cualquier profesional»;
- ver solamente horarios realmente reservables;
- entregar sus datos una sola vez;
- recibir una confirmación clara en pantalla y por email.

### Administrador del negocio

Dueño, recepcionista o encargado de agenda.

Necesita:

- saber qué ocurre hoy y qué viene después;
- ver reservas por día, semana y lista;
- consultar el detalle de una reserva;
- cancelar, completar o marcar inasistencia;
- gestionar servicios, profesionales y horarios semanales;
- bloquear ausencias, vacaciones o intervalos excepcionales.

## 4. Objetivos del MVP

- Completar una reserva pública de extremo a extremo.
- Evitar dobles reservas incluso ante solicitudes concurrentes.
- Calcular disponibilidad por servicio, profesional y fecha.
- Permitir la operación diaria del negocio desde un panel autenticado.
- Enviar confirmaciones por email mediante una abstracción compatible con Resend.
- Ofrecer una base presentable en portafolio y adaptable a un futuro cliente.
- Mantener las reglas críticas cubiertas por tests unitarios y de integración.

## 5. Alcance

### P0 — imprescindible para considerar funcional el MVP

#### Área pública

- Listado de servicios activos con nombre, descripción, duración y precio.
- Listado de profesionales activos que ofrecen el servicio elegido.
- Opción «Cualquier profesional».
- Consulta de disponibilidad por fecha.
- Selección de un horario y captura de nombre, email, teléfono y nota opcional.
- Creación de reserva con revalidación en servidor.
- Pantalla de confirmación con resumen completo.
- Email de confirmación después de persistir la reserva.

#### Panel administrativo

- Inicio y cierre de sesión para administrador.
- Dashboard con resumen y agenda del día.
- Calendario con vistas de día, semana y lista.
- Listado, filtros básicos y detalle de reservas.
- Cambio de estado: confirmada, completada, cancelada o inasistencia.
- CRUD de servicios y profesionales; desactivar antes que eliminar.
- Asignación de servicios a profesionales.
- Edición de uno o más intervalos de disponibilidad por día de semana.
- Creación y eliminación de bloqueos excepcionales (`time_off`).

#### Plataforma

- PostgreSQL y migraciones Alembic reproducibles.
- Datos demo idempotentes para Estudio Nómada.
- Configuración por variables de entorno y `.env.example` sin secretos.
- Logs útiles sin datos personales innecesarios.
- Tests del motor de disponibilidad, creación concurrente y endpoints críticos.

### P1 — antes de presentar públicamente

- Creación manual de reservas desde el panel con `source = admin`.
- Estados vacíos, skeletons y recuperación de errores en todas las pantallas.
- Suite E2E del camino feliz y conflictos principales.
- Revisión responsive y accesibilidad con teclado.
- CI para lint, tipos, tests y builds.
- README, capturas, diagrama de arquitectura y despliegue de demo.

### P2 — explícitamente fuera del MVP

- Multiempresa visible, invitaciones, roles o permisos granulares.
- Pagos, suscripciones o facturación.
- Reprogramación y cancelación autoservicio desde email.
- Recordatorios, SMS o WhatsApp.
- Lista de espera.
- Múltiples sucursales, salas o recursos.
- Sincronización con Google Calendar u Outlook.
- Reservas recurrentes, paquetes o bonos.
- Marketplace, aplicación móvil nativa o branding configurable desde el panel.
- Analytics avanzados.

P2 no se implementa hasta que P0 esté terminado, testeado y demostrable. Las extensiones futuras se anotan como decisiones o issues; no se anticipan con abstracciones especulativas.

## 6. Flujos principales

### 6.1 Reserva pública

1. El cliente elige un servicio.
2. Elige un profesional o «Cualquier profesional».
3. Elige una fecha dentro del horizonte permitido.
4. El sistema muestra slots disponibles en la zona horaria del negocio.
5. El cliente elige un slot e ingresa sus datos.
6. El servidor vuelve a validar el servicio, profesional, intervalo y reglas vigentes.
7. PostgreSQL confirma la reserva o rechaza un conflicto concurrente.
8. La API responde con un resumen seguro para mostrar al cliente.
9. El sistema intenta enviar el email de confirmación sin revertir una reserva ya confirmada si Resend falla.

Para «Cualquier profesional», cada slot se presenta una sola vez. El servidor selecciona de forma determinista un profesional disponible al crear la reserva; no se promete balanceo inteligente en P0.

### 6.2 Operación administrativa

1. El administrador inicia sesión.
2. Revisa la agenda de hoy o navega al calendario.
3. Abre una reserva para consultar servicio, profesional, cliente, horario, estado y notas.
4. Cambia su estado mediante acciones explícitas y confirmadas.
5. Los cambios que afectan capacidad invalidan la disponibilidad correspondiente.

### 6.3 Configurar disponibilidad

1. El administrador asigna servicios a un profesional.
2. Define intervalos semanales, por ejemplo 09:00–13:00 y 14:00–18:00.
3. Añade bloqueos excepcionales con inicio, fin y motivo opcional.
4. El sistema valida que los intervalos sean coherentes antes de guardarlos.

## 7. Reglas de negocio

### Tiempo e intervalos

- La zona horaria inicial del negocio es `America/Santiago` y se guarda como identificador IANA.
- Los instantes persistidos se guardan en UTC con tipos conscientes de zona horaria.
- Las reglas semanales se interpretan en la zona horaria del negocio.
- Los intervalos usan semántica semiabierta `[inicio, fin)`: una cita que termina a las 10:00 no choca con otra que comienza a las 10:00.
- La duración de la reserva proviene del servicio al confirmar y queda guardada como snapshot.
- No se acepta un slot cuya duración no quepa completamente dentro de un intervalo laboral.

### Disponibilidad

- El profesional debe estar activo y ofrecer el servicio activo elegido.
- El slot debe estar dentro de la disponibilidad semanal del profesional.
- El slot no puede solaparse con un bloqueo ni con una reserva no cancelada.
- Se respetan `minimum_booking_notice_minutes`, `booking_horizon_days` y `slot_interval_minutes` del negocio.
- Slots pasados o fuera del horizonte nunca se devuelven.
- La disponibilidad mostrada es informativa; siempre se recalcula al reservar.

### Reservas

- Estados: `confirmed`, `completed`, `cancelled`, `no_show`.
- Una reserva nueva entra como `confirmed`; no existe pago ni estado `pending` en P0.
- Solamente `cancelled` deja de bloquear el intervalo.
- El final lo calcula el servidor; el cliente no puede imponerlo.
- El precio, duración y nombre de servicio visibles en el histórico se conservan como snapshots.
- `source` es `public` o `admin`.
- Repetir una misma petición con la misma clave de idempotencia no crea dos reservas.
- El motor de aplicación mejora el mensaje de error, pero la base de datos es la autoridad final ante concurrencia.

### Datos y borrado

- Cada consulta de negocio se filtra por `business_id`, incluso mientras exista una sola instalación.
- Servicios y profesionales referenciados se desactivan; no se borran físicamente desde el producto.
- Los datos personales no se exponen en endpoints públicos ni se incluyen completos en logs.

## 8. Criterios de aceptación

### Disponibilidad

- Devuelve slots alineados a la granularidad configurada.
- Acepta un servicio que termina exactamente cuando comienza otra reserva.
- Rechaza solapamientos por inicio, final, contención total o igualdad.
- Considera múltiples intervalos laborales en un mismo día.
- Considera bloqueos parciales y de día completo.
- Excluye profesionales que no ofrecen el servicio.
- Aplica anticipación mínima y horizonte usando un reloj inyectable.
- Se comporta correctamente en cambios de horario de verano de `America/Santiago`.

### Creación de reserva

- Ignora cualquier `ends_at` enviado por el cliente y lo calcula desde el servicio.
- Revalida dentro de la operación de creación.
- Dos solicitudes concurrentes por el mismo profesional e intervalo producen exactamente una reserva confirmada; la otra recibe `409 Conflict`.
- Repetir la misma clave de idempotencia devuelve la reserva original.
- Un fallo de email queda observable y no elimina la reserva.

### Experiencia pública

- El camino feliz se completa sin cuenta y funciona desde 320 px de ancho.
- Cada paso conserva la selección anterior y permite volver sin perder datos válidos.
- Loading, vacío, conflicto y error de red tienen mensajes y acciones claras.
- La confirmación muestra servicio, profesional, fecha, hora y email de destino.

### Administración

- Las rutas requieren sesión válida.
- Cambiar una reserva a `cancelled` libera el slot en una consulta posterior.
- Un bloqueo nuevo elimina del resultado los slots afectados.
- Desactivar un servicio o profesional impide nuevas reservas sin alterar el histórico.

## 9. Indicadores de calidad

No son métricas comerciales del MVP; son señales de que el producto está listo para demostrarse:

- cero fallos en tests de dominio y concurrencia;
- camino público crítico cubierto por E2E;
- cero errores de tipos, lint o build;
- navegación completa con teclado en el flujo público;
- reserva pública normal completada en menos de dos minutos;
- ningún secreto, stack trace o dato personal sensible visible al usuario.

## 10. Entrega por hitos

1. **Foundation:** monorepo, entornos, PostgreSQL, migraciones, lint, tests y CI.
2. **Dominio:** modelos, disponibilidad y tests exhaustivos.
3. **Primera reserva vertical:** disponibilidad → reserva → persistencia.
4. **Flujo público:** experiencia completa y responsive.
5. **Administración:** auth, agenda, calendario y configuración.
6. **Notificaciones:** Resend, plantilla y manejo de fallos.
7. **Hardening:** concurrencia, zonas horarias, accesibilidad y E2E.
8. **Portafolio:** datos demo, despliegue, documentación y material visual.

Cada hito debe terminar funcionando verticalmente. No acumular grandes capas incompletas ni iniciar P2 como «preparación».

