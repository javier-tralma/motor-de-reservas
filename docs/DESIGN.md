# Diseño de producto e interfaz

## 1. Dirección

La experiencia debe parecer un producto que un negocio real podría adoptar, no un panel genérico de tutorial. La demo de **Estudio Nómada** combina calidez local, calma y precisión. El sistema sigue siendo reutilizable: marca, textos y datos demo se concentran en configuración y tokens, no en lógica de negocio.

Personalidad:

- **clara:** cada pantalla tiene una acción principal;
- **humana:** textos directos, sin jerga técnica;
- **confiable:** fechas, precios, estados y consecuencias siempre visibles;
- **serena:** espacio generoso, jerarquía tipográfica y color con intención;
- **eficiente:** el panel favorece lectura y acción rápida.

Evitar gradientes decorativos excesivos, tarjetas dentro de tarjetas, iconos ambiguos y dashboards saturados.

## 2. Principios UX

1. Mostrar decisiones de una en una en el flujo público.
2. No pedir cuenta ni información antes de elegir horario.
3. No mostrar slots que el servidor no considera válidos.
4. Mantener visible el resumen de la selección.
5. Conservar datos válidos cuando ocurre un conflicto o se vuelve atrás.
6. Explicar errores con una acción siguiente.
7. Diseñar primero para móvil en el área pública y para escritorio adaptable en administración.
8. Usar un calendario complejo solo donde aporta: el panel, no la reserva pública.

## 3. Sistema visual

### Tokens base

Los valores son una dirección inicial, no colores codificados directamente en componentes.

```css
:root {
  --color-canvas: #f7f5f0;
  --color-surface: #fffdf9;
  --color-ink: #1f2a27;
  --color-muted: #66736e;
  --color-primary: #176b5b;
  --color-primary-hover: #125548;
  --color-accent: #d98b5f;
  --color-border: #dfe4df;
  --color-success: #247a57;
  --color-warning: #9a6416;
  --color-danger: #b33a3a;
  --color-focus: #2f7fd3;

  --radius-sm: 0.5rem;
  --radius-md: 0.875rem;
  --radius-lg: 1.25rem;

  --shadow-sm: 0 1px 2px rgb(31 42 39 / 0.06);
  --shadow-md: 0 12px 32px rgb(31 42 39 / 0.10);
}
```

Mantener contraste WCAG AA. El color nunca es el único indicador de estado.

### Tipografía

- Sans legible de interfaz con fallback de sistema.
- Títulos expresivos pero sobrios; cuerpo entre 16 y 18 px en el flujo público.
- Números y horarios con cifras tabulares cuando ayude a alinear agenda.
- Máximo de ancho de lectura aproximado: 65 caracteres para textos largos.

### Espaciado y superficie

- Escala de 4 px con saltos principales de 8, 12, 16, 24, 32 y 48.
- Bordes sutiles y sombras reservadas para capas elevadas.
- Un solo contenedor destacado por sección; evitar envolver cada dato en una tarjeta.
- Targets táctiles mínimos de 44 × 44 px.

## 4. Arquitectura de información

### Público

```text
/
/reservar
/reservar/confirmacion/:publicReference
```

`/` puede ser una portada breve del negocio con CTA «Reservar hora». `/reservar` contiene el wizard completo y puede representar el paso actual en query string sin exponer datos personales.

### Administración

```text
/admin/login
/admin
/admin/calendario
/admin/reservas
/admin/reservas/:id
/admin/servicios
/admin/profesionales
/admin/disponibilidad
/admin/configuracion
```

En P0, Configuración muestra datos del negocio y ajustes seguros; zona horaria y moneda pueden ser de solo lectura.

## 5. Flujo público

### Shell

Cabecera compacta con marca y enlace de ayuda/contacto. En escritorio, contenido principal y resumen forman dos columnas; en móvil, el resumen es una banda compacta o un acordeón antes de la acción final.

Indicador de progreso textual:

```text
1 Servicio  →  2 Profesional  →  3 Horario  →  4 Tus datos
```

No depender solo del número: anunciar el nombre del paso y marcar el actual con `aria-current="step"`.

### Paso 1 — Servicio

Título: «¿Qué quieres reservar?»

Cada opción muestra:

- nombre;
- descripción breve;
- duración;
- precio formateado en CLP;
- indicador de selección.

Toda la fila es seleccionable. No usar un botón «Ver más» si el contenido cabe en la opción.

### Paso 2 — Profesional

Título: «¿Con quién prefieres atenderte?»

La primera opción es «Cualquier profesional» con ayuda: «Te asignaremos a alguien disponible». Después aparecen profesionales elegibles para el servicio, ordenados por `sort_order` y nombre.

Si solo existe uno, mantener el paso pero permitir confirmarlo con una interacción mínima; no cambiar el modelo mental entre negocios.

### Paso 3 — Fecha y hora

Título: «Elige una fecha y una hora»

- Navegador horizontal de días cercanos con día de semana, número y etiqueta «Hoy»/«Mañana».
- Botón para abrir un selector mensual accesible cuando se necesiten fechas lejanas.
- Horarios como botones en una grilla simple, agrupados por mañana y tarde solo si hay suficientes.
- Mostrar hora local; no pedir al cliente interpretar offsets.
- Nunca renderizar slots deshabilitados como si fueran opciones. Si se quiere explicar un día sin cupos, mostrar el estado del día, no una grilla de horas tachadas.

Estado vacío:

> No quedan horas disponibles ese día. Prueba con la fecha siguiente.

Acciones: «Ver próximo día disponible» y navegación de fecha.

### Paso 4 — Tus datos

Campos:

- nombre completo;
- email;
- teléfono;
- nota opcional con contador y límite visible.

Mostrar errores junto al campo y un resumen al inicio solo cuando facilite corregir varios. No borrar campos ante error de red o `409`.

El botón principal usa una consecuencia explícita: «Confirmar reserva», no «Enviar».

Antes del botón, resumen final:

```text
Corte clásico · 45 min
Camila Rojas
martes 11 de agosto · 15:15–16:00
$14.000
```

No ocultar el precio ni la zona contextual del negocio.

### Conflicto al confirmar

Ante `slot_unavailable`:

1. mantener servicio, profesional y datos personales;
2. volver al paso de fecha/hora;
3. refrescar disponibilidad;
4. anunciar el mensaje con `role="alert"`;
5. destacar alternativas cercanas sin seleccionarlas automáticamente.

Texto recomendado:

> Esa hora acaba de ser reservada. Actualizamos los horarios para que elijas otra.

### Confirmación

La pantalla contiene:

- señal visual de éxito acompañada de texto;
- referencia pública;
- servicio, profesional, fecha, inicio y final;
- email al que se intentó enviar la confirmación;
- contacto y dirección del negocio;
- CTA secundario «Volver al inicio».

No mostrar detalles técnicos del envío. Si el email falla de forma conocida, la reserva sigue confirmada y la UI indica cómo contactar al negocio.

## 6. Panel administrativo

### Navegación

Sidebar en escritorio y drawer en pantallas estrechas:

```text
Resumen
Calendario
Reservas
Servicios
Profesionales
Disponibilidad
Configuración
```

Mostrar el nombre del negocio y la cuenta activa. La acción de cerrar sesión está separada de las acciones operativas.

### Dashboard

Encabezado:

```text
Buenas tardes, Javier
Esta es la agenda de hoy.
```

Indicadores útiles y limitados:

- reservas de hoy;
- confirmadas restantes;
- completadas;
- ocupación aproximada solo si puede calcularse correctamente.

La pieza principal es «Próxima reserva» y luego una agenda cronológica. No inventar ingresos si no existen estados y reglas suficientes para una métrica confiable.

### Calendario

FullCalendar con vistas día, semana y lista. La vista inicial depende del ancho: día/lista en móvil, semana en escritorio.

Cada evento muestra hora, cliente abreviado y servicio. Color o marca secundaria identifica profesional, pero texto y filtros siguen disponibles.

Al seleccionar una reserva, abrir drawer en escritorio y pantalla/modal accesible en móvil con:

- estado;
- cliente y contacto;
- servicio y snapshots;
- profesional;
- horario;
- fuente y notas;
- acciones permitidas.

Confirmar acciones destructivas o irreversibles. «Cancelar reserva» requiere diálogo con fecha, hora y nombre; «Completar» puede ser directa con feedback y opción de cerrar.

### Reservas

Tabla adaptable con filtros por fecha, estado y profesional. En móvil se convierte en lista, no en tabla horizontal ilegible.

Columnas esenciales:

- fecha/hora;
- cliente;
- servicio;
- profesional;
- estado.

No incluir teléfono y email en la tabla principal; aparecen en detalle.

### Servicios y profesionales

Listas editables con estado activo/inactivo. Formularios en páginas o drawers, no en muchas celdas inline.

- Desactivar explica que impide reservas futuras y conserva histórico.
- Duración y precio muestran unidades.
- La asignación profesional–servicio usa checkboxes con nombres completos.

### Disponibilidad

Vista centrada en un profesional:

- selector de profesional;
- semana con uno o más intervalos por día;
- acción «Añadir intervalo»;
- validación inmediata de cruces y orden;
- sección separada «Bloqueos y ausencias» con rango, motivo y eliminación.

No usar un calendario mensual para editar reglas recurrentes: una lista semanal es más clara.

## 7. Componentes compartidos

Primitivas mínimas:

```text
Button
IconButton
TextField
TextArea
Select
Checkbox
RadioCard
DateStrip
SlotGrid
StatusBadge
InlineAlert
Dialog
Drawer
Skeleton
EmptyState
PageHeader
```

Cada componente debe tener estados `default`, `hover`, `focus-visible`, `disabled`, `loading` y `error` cuando corresponda. No crear una librería exhaustiva antes de que la aplicación requiera los componentes.

## 8. Estados y feedback

### Loading

- Skeletons que preservan la forma de contenido cuando la espera supera un instante.
- Spinner dentro de botones para mutaciones; mantener ancho y texto legible.
- Desactivar doble envío mientras una petición está en curso, además de idempotencia en servidor.

### Vacío

Todo estado vacío responde:

1. qué falta;
2. por qué puede ocurrir;
3. qué acción es posible.

### Error

- Error de campo: junto al control.
- Error recuperable de sección: alerta inline con reintento.
- Error de página: contexto, request ID y navegación segura.
- Error inesperado: nunca mostrar stack trace.
- Toast: solo para confirmaciones no críticas; no usarlo como único lugar para errores importantes.

### Estado de reserva

Etiquetas en español:

| Valor | Etiqueta | Tratamiento |
|---|---|---|
| `confirmed` | Confirmada | primario/informativo |
| `completed` | Completada | éxito |
| `cancelled` | Cancelada | neutro o peligro moderado |
| `no_show` | Inasistencia | advertencia |

## 9. Responsive

Puntos de verificación, no contratos rígidos:

- 320–479 px: una columna, acciones principales a ancho completo.
- 480–767 px: grillas de slots de 3–4 columnas según contenido.
- 768–1023 px: navegación administrativa compacta.
- 1024 px o más: resumen lateral público y sidebar administrativo.

Probar al menos 320, 375, 768, 1024 y 1440 px, además de zoom al 200 %. Evitar alturas fijas en formularios y calendarios.

## 10. Accesibilidad

- HTML semántico antes que roles personalizados.
- Una sola jerarquía lógica de encabezados por página.
- Labels persistentes; placeholders no sustituyen etiquetas.
- Foco visible y orden predecible.
- Wizard, selector de fecha, slots, drawer y diálogos operables con teclado.
- Diálogos atrapan foco, tienen título y devuelven foco al disparador.
- Cambios de paso y resultados asíncronos importantes se anuncian.
- Iconos decorativos usan `aria-hidden`; botones solo-icono tienen nombre accesible.
- Contraste AA y contenido comprensible sin color.
- Respetar `prefers-reduced-motion`.

## 11. Contenido y localización

- Interfaz inicial en español de Chile (`es-CL`).
- Fechas: «martes 11 de agosto», evitando formatos ambiguos como `11/08` cuando hay espacio.
- Hora: 24 horas (`15:15`).
- Moneda: `Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP' })` con presentación coherente.
- Tono de tú, cordial y directo.
- Usar «profesional» en texto genérico; el negocio puede personalizar esta etiqueta en una fase futura.
- No prometer «email enviado» hasta conocer el resultado; preferir «Enviaremos los detalles» o el estado real.

## 12. Criterios visuales de terminado

- No hay overflow horizontal a 320 px.
- No aparecen saltos importantes al cargar datos.
- Todos los flujos tienen loading, vacío, error y éxito.
- Toda acción muestra resultado perceptible.
- La selección actual permanece evidente al volver de paso.
- Fechas, zonas, duración y precios coinciden con la respuesta del backend.
- La interfaz se puede recorrer con teclado y conserva foco útil después de mutaciones.
- Datos demo son realistas y consistentes en todas las pantallas.

