import html
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from app.integrations.email.service import BookingEmailData

WEEKDAYS_ES = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]

MONTHS_ES = [
    "",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def format_spanish_date(dt: datetime) -> str:
    weekday = WEEKDAYS_ES[dt.weekday()]
    day = dt.day
    month = MONTHS_ES[dt.month]
    year = dt.year
    return f"{weekday}, {day} de {month} de {year}"


def render_booking_confirmation_subject(booking: "BookingEmailData") -> str:
    return f"Confirmación de reserva en {booking.business_name}"


def render_booking_confirmation_text(booking: "BookingEmailData") -> str:
    tz = ZoneInfo(booking.business_timezone)
    local_start = booking.starts_at.astimezone(tz)
    local_end = booking.ends_at.astimezone(tz)

    date_str = format_spanish_date(local_start)
    start_time = local_start.strftime("%H:%M")
    end_time = local_end.strftime("%H:%M")
    time_str = f"{start_time} a {end_time} (Hora local {booking.business_timezone})"

    lines = [
        f"Hola {booking.customer_name},",
        "",
        f"Tu reserva en {booking.business_name} ha sido confirmada.",
        "",
        "Detalles de la cita:",
        f"- Servicio: {booking.service_name}",
        f"- Profesional: {booking.provider_name}",
        f"- Fecha: {date_str}",
        f"- Horario: {time_str}",
        f"- Duración: {booking.duration_minutes} minutos",
        f"- Código de reserva: {booking.public_reference}",
    ]

    if booking.business_address:
        lines.append(f"- Dirección: {booking.business_address}")
    if booking.business_phone:
        lines.append(f"- Teléfono de contacto: {booking.business_phone}")

    lines.extend(
        [
            "",
            f"Gracias por confiar en {booking.business_name}.",
        ]
    )

    return "\n".join(lines)


def render_booking_confirmation_html(booking: "BookingEmailData") -> str:
    tz = ZoneInfo(booking.business_timezone)
    local_start = booking.starts_at.astimezone(tz)
    local_end = booking.ends_at.astimezone(tz)

    date_str = format_spanish_date(local_start)
    start_time = local_start.strftime("%H:%M")
    end_time = local_end.strftime("%H:%M")
    time_str = f"{start_time} a {end_time} (Hora local {booking.business_timezone})"

    esc_business = html.escape(booking.business_name)
    esc_customer = html.escape(booking.customer_name)
    esc_service = html.escape(booking.service_name)
    esc_provider = html.escape(booking.provider_name)
    esc_ref = html.escape(booking.public_reference)

    address_row = ""
    if booking.business_address:
        esc_address = html.escape(booking.business_address)
        address_row = (
            "<tr>\n"
            '  <td style="padding: 8px 0; color: #64748b; font-size: 14px; width: 140px;">Dirección:</td>\n'
            f'  <td style="padding: 8px 0; color: #1e293b; font-size: 14px; font-weight: 500;">{esc_address}</td>\n'
            "</tr>\n"
        )

    phone_row = ""
    if booking.business_phone:
        esc_phone = html.escape(booking.business_phone)
        phone_row = (
            "<tr>\n"
            '  <td style="padding: 8px 0; color: #64748b; font-size: 14px; width: 140px;">Teléfono:</td>\n'
            f'  <td style="padding: 8px 0; color: #1e293b; font-size: 14px; font-weight: 500;">{esc_phone}</td>\n'
            "</tr>\n"
        )

    body_style = (
        "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; "
        "background-color: #f8fafc; margin: 0; padding: 24px 12px;"
    )
    table_style = (
        "max-width: 580px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e2e8f0; "
        "border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05);"
    )
    box_style = (
        "background-color: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 24px;"
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Confirmación de Reserva</title>
</head>
<body style="{body_style}">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="{table_style}">
    <tr>
      <td style="background-color: #0f172a; padding: 24px; text-align: center;">
        <h1 style="color: #ffffff; font-size: 20px; font-weight: 700; margin: 0;">{esc_business}</h1>
      </td>
    </tr>
    <tr>
      <td style="padding: 32px 24px;">
        <h2 style="color: #0f172a; font-size: 18px; font-weight: 600; margin: 0 0 12px 0;">
          ¡Tu reserva está confirmada!
        </h2>
        <p style="color: #475569; font-size: 15px; line-height: 1.5; margin: 0 0 24px 0;">
          Hola <strong>{esc_customer}</strong>, tu cita ha sido reservada con éxito.
        </p>

        <div style="{box_style}">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="padding: 8px 0; color: #64748b; font-size: 14px; width: 140px;">Servicio:</td>
              <td style="padding: 8px 0; color: #1e293b; font-size: 14px; font-weight: 600;">{esc_service}</td>
            </tr>
            <tr>
              <td style="padding: 8px 0; color: #64748b; font-size: 14px;">Profesional:</td>
              <td style="padding: 8px 0; color: #1e293b; font-size: 14px; font-weight: 600;">{esc_provider}</td>
            </tr>
            <tr>
              <td style="padding: 8px 0; color: #64748b; font-size: 14px;">Fecha:</td>
              <td style="padding: 8px 0; color: #1e293b; font-weight: 600; text-transform: capitalize;">
                {date_str}
              </td>
            </tr>
            <tr>
              <td style="padding: 8px 0; color: #64748b; font-size: 14px;">Horario:</td>
              <td style="padding: 8px 0; color: #1e293b; font-size: 14px; font-weight: 600;">{time_str}</td>
            </tr>
            <tr>
              <td style="padding: 8px 0; color: #64748b; font-size: 14px;">Duración:</td>
              <td style="padding: 8px 0; color: #1e293b; font-size: 14px; font-weight: 500;">
                {booking.duration_minutes} minutos
              </td>
            </tr>
            <tr>
              <td style="padding: 8px 0; color: #64748b; font-size: 14px;">Código:</td>
              <td style="padding: 8px 0; color: #0284c7; font-size: 14px; font-weight: 700; font-family: monospace;">
                {esc_ref}
              </td>
            </tr>
            {address_row}{phone_row}
          </table>
        </div>

        <p style="color: #64748b; font-size: 13px; line-height: 1.5; margin: 0;">
          Si necesitas realizar cambios o tienes alguna consulta, por favor contáctanos directamente.
        </p>
      </td>
    </tr>
    <tr>
      <td style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 16px 24px; text-align: center;">
        <p style="color: #94a3b8; font-size: 12px; margin: 0;">{esc_business} — Sistema de Reservas</p>
      </td>
    </tr>
  </table>
</body>
</html>
"""
