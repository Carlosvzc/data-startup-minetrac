"""Envío por correo del resumen de MineTrac (reporte PDF + alertas).

Dos formas de enviar, según las variables de entorno:
  MINETRAC_CORREO=smtp  (por defecto)  MINETRAC_SMTP_HOST, MINETRAC_SMTP_PUERTO (587), MINETRAC_SMTP_USUARIO, MINETRAC_SMTP_CLAVE, MINETRAC_CORREO_DE
  MINETRAC_CORREO=ses                  Amazon SES con el rol de la instancia (MINETRAC_CORREO_DE debe estar verificado en SES)
Las claves nunca se escriben en el código ni en el repositorio. Si falta configuración, `configurado()` lo dice y no se envía nada.
"""
from __future__ import annotations
import html
import os
import re
import smtplib
import ssl
from email.message import EmailMessage

RE_CORREO = re.compile(r'^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$')


def separar_destinatarios(texto: str) -> list[str]:
    """Acepta correos separados por coma, punto y coma, espacio o salto de línea; descarta duplicados."""
    vistos, out = set(), []
    for c in re.split(r'[,;\s]+', texto or ''):
        c = c.strip().lower()
        if c and c not in vistos:
            vistos.add(c); out.append(c)
    return out


def validos(correos: list[str]) -> tuple[list[str], list[str]]:
    return [c for c in correos if RE_CORREO.match(c)], [c for c in correos if not RE_CORREO.match(c)]


def modo() -> str:
    return os.environ.get('MINETRAC_CORREO', 'smtp').lower()


def configurado() -> tuple[bool, str]:
    """(listo, mensaje). No revela valores, solo qué falta."""
    if not os.environ.get('MINETRAC_CORREO_DE'):
        return False, 'Falta MINETRAC_CORREO_DE (el correo remitente).'
    if modo() == 'ses':
        return True, 'Amazon SES'
    faltan = [v for v in ('MINETRAC_SMTP_HOST', 'MINETRAC_SMTP_USUARIO', 'MINETRAC_SMTP_CLAVE') if not os.environ.get(v)]
    return (False, 'Faltan variables: ' + ', '.join(faltan) + '.') if faltan else (True, 'SMTP ' + os.environ['MINETRAC_SMTP_HOST'])


def cuerpo_html(titulo: str, lectura: str, k: dict, resumen_alertas: dict, alertas_top: list[dict], periodo: str) -> str:
    """Correo con el mismo lenguaje visual del tablero. Todo el texto que viene de datos se escapa."""
    e = html.escape
    tarjetas = ''.join(
        f'<td style="padding:14px 16px;border-top:3px solid #f5a300;background:#f4f8fb;border:1px solid #d9e3ec;border-top:3px solid #f5a300">'
        f'<div style="font:700 22px Arial,sans-serif;color:#0f2a44">{e(v)}</div><div style="font:11px Arial,sans-serif;color:#4f6478;margin-top:3px">{e(l)}</div></td>'
        for v, l in [(f"{k['intervenciones']:,}", 'Intervenciones'), ('$' + f"{k['gasto_mxn']:,.0f}", 'Gasto registrado (parcial)'),
                     (f"{resumen_alertas.get('Alta', 0)}", 'Alertas altas'), (f"{resumen_alertas.get('Media', 0)}", 'Alertas medias')])
    col = {'Alta': '#b3261e', 'Media': '#c77d00', 'Info': '#2a6f97'}
    filas = ''.join(
        f'<tr><td style="padding:8px 10px;border-bottom:1px solid #e6eef5;font:700 12px Arial;color:{col.get(a["severidad"], "#0f2a44")}">{e(a["severidad"])}</td>'
        f'<td style="padding:8px 10px;border-bottom:1px solid #e6eef5;font:700 12px Arial;color:#0f2a44">{e(a["camion_id"])}</td>'
        f'<td style="padding:8px 10px;border-bottom:1px solid #e6eef5;font:12px Arial;color:#2f3a43">{e(a["tipo"])}. {e(a["detalle"])}</td></tr>' for a in alertas_top)
    return (f'<div style="background:#e8eef4;padding:24px 0"><table align="center" width="620" cellpadding="0" cellspacing="0" style="background:#fff;border:1px solid #d9e3ec">'
            f'<tr><td style="background:#0f2a44;padding:22px 26px"><div style="font:700 11px Arial;color:#f5a300;letter-spacing:1.5px">MINETRAC · CONTROL DE MAQUINARIA</div>'
            f'<div style="font:700 22px Arial;color:#fff;margin-top:6px">{e(titulo)}</div><div style="font:12px Arial;color:#cfd5da;margin-top:4px">{e(periodo)}</div></td></tr>'
            f'<tr><td style="height:5px;background:#f5a300"></td></tr>'
            f'<tr><td style="padding:22px 26px"><p style="font:15px/1.5 Arial;color:#0f2a44;margin:0 0 16px">{e(lectura)}</p>'
            f'<table width="100%" cellspacing="6" cellpadding="0"><tr>{tarjetas}</tr></table>'
            f'<h3 style="font:700 15px Arial;color:#0f2a44;margin:20px 0 8px">Lo más urgente</h3>'
            f'<table width="100%" cellspacing="0" cellpadding="0">{filas or "<tr><td style=font:13px Arial>Sin alertas con los datos actuales.</td></tr>"}</table>'
            f'<p style="font:12px/1.5 Arial;color:#4f6478;margin:18px 0 0">El reporte completo va adjunto en PDF. Información real de la bitácora de camiones de Máquinas Centella; '
            f'los montos son parciales porque no todas las intervenciones tienen monto anotado.</p></td></tr></table></div>')


def construir_mensaje(destinatarios: list[str], asunto: str, html_cuerpo: str, texto_plano: str, pdf: bytes | None = None,
                      nombre_pdf: str = 'reporte_minetrac.pdf', remitente: str | None = None) -> EmailMessage:
    ok, malos = validos(destinatarios)
    if malos or not ok:
        raise ValueError('Correos no válidos: ' + ', '.join(malos) if malos else 'Falta al menos un destinatario.')
    if any(ch in asunto for ch in '\r\n'):
        raise ValueError('El asunto no puede tener saltos de línea.')
    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = remitente or os.environ.get('MINETRAC_CORREO_DE', '')
    msg['To'] = ', '.join(ok)
    msg.set_content(texto_plano)
    msg.add_alternative(html_cuerpo, subtype='html')
    if pdf:
        msg.add_attachment(pdf, maintype='application', subtype='pdf', filename=nombre_pdf)
    return msg


def enviar(msg: EmailMessage) -> str:
    """Envía el mensaje con la configuración del entorno. Devuelve el modo usado. Lanza excepción si algo falla."""
    listo, info = configurado()
    if not listo:
        raise RuntimeError('El envío de correo no está configurado. ' + info)
    if modo() == 'ses':
        import boto3
        boto3.client('ses', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')).send_raw_email(
            Source=msg['From'], Destinations=[a.strip() for a in msg['To'].split(',')], RawMessage={'Data': msg.as_bytes()})
        return 'ses'
    host, puerto = os.environ['MINETRAC_SMTP_HOST'], int(os.environ.get('MINETRAC_SMTP_PUERTO', '587'))
    ctx = ssl.create_default_context()
    if puerto == 465:
        with smtplib.SMTP_SSL(host, puerto, context=ctx, timeout=30) as s:
            s.login(os.environ['MINETRAC_SMTP_USUARIO'], os.environ['MINETRAC_SMTP_CLAVE']); s.send_message(msg)
    else:
        with smtplib.SMTP(host, puerto, timeout=30) as s:
            s.starttls(context=ctx); s.login(os.environ['MINETRAC_SMTP_USUARIO'], os.environ['MINETRAC_SMTP_CLAVE']); s.send_message(msg)
    return 'smtp'
