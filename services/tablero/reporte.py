"""Reporte PDF del tablero de MineTrac: indicadores, gráficas, alertas y predicción de la selección actual.

Usa reportlab y matplotlib (sin navegador ni servicios externos), así que corre igual en el tablero, en un script programado
o dentro de una Lambda. Solo muestra información real de la bitácora de camiones; lo que falta se dice como falta.
"""
from __future__ import annotations
import io
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import BaseDocTemplate, Frame, Image, KeepTogether, PageTemplate, Paragraph, Spacer, Table, TableStyle
from core import eventos, resumen

INK, STEEL, GOLD, BLUE, LINE, SOFT = '#1f2328', '#5b6770', '#f2b600', '#3e5c76', '#dde1e5', '#9aa6b0'
SEV = {'Alta': '#b3261e', 'Media': '#c77d00', 'Info': '#3e5c76'}
MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


def _money(v):
    return '$' + (f'{v / 1e6:,.2f} M' if abs(v) >= 1e6 else f'{v:,.0f}')


def _estilos():
    base = dict(fontName='Helvetica', textColor=colors.HexColor(INK), alignment=TA_LEFT)
    return {
        'h1': ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=23, leading=26, textColor=colors.white),
        'sub': ParagraphStyle('sub', fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor('#cfd5da')),
        'h2': ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=colors.HexColor(INK), spaceBefore=14, spaceAfter=6, keepWithNext=1),
        'p': ParagraphStyle('p', fontSize=9.6, leading=14, spaceAfter=4, **base),
        'peq': ParagraphStyle('peq', fontSize=8, leading=11, textColor=colors.HexColor(STEEL), fontName='Helvetica'),
        'cel': ParagraphStyle('cel', fontSize=8.2, leading=10.5, **base),
        'celb': ParagraphStyle('celb', fontSize=8.2, leading=10.5, fontName='Helvetica-Bold', textColor=colors.HexColor(INK)),
        'kv': ParagraphStyle('kv', fontName='Helvetica-Bold', fontSize=18, leading=20, textColor=colors.HexColor(INK)),
        'kl': ParagraphStyle('kl', fontName='Helvetica', fontSize=7.6, leading=10, textColor=colors.HexColor(STEEL)),
    }


def _png(fig, ancho_cm):
    b = io.BytesIO(); fig.savefig(b, format='png', dpi=200, bbox_inches='tight', facecolor='white'); plt.close(fig); b.seek(0)
    ancho = ancho_cm * cm
    from PIL import Image as PI
    w, h = PI.open(b).size; b.seek(0)
    return Image(b, width=ancho, height=ancho * h / w)


def _limpiar(ax):
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color('#c9cfd4')
    ax.tick_params(colors='#434c54', labelsize=8)
    ax.set_axisbelow(True)


def g_componentes(mm):
    c = mm.groupby('componente').costo_mxn.sum().loc[lambda s: s > 0].sort_values(ascending=False).head(8)
    if c.empty:
        return None
    c = c.iloc[::-1]
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    ax.barh(c.index, c.values / 1000, color=[GOLD if i == len(c) - 1 else SOFT for i in range(len(c))], height=.62)
    for y, v in enumerate(c.values):
        ax.text(v / 1000 + c.max() / 1000 * .015, y, f'${v / 1000:,.0f} mil', va='center', fontsize=7.6, color=INK)
    ax.set_xlim(0, c.max() / 1000 * 1.22); ax.set_xlabel('Miles de MXN (solo intervenciones con monto)', fontsize=8, color=STEEL); _limpiar(ax)
    return fig


def g_camiones(mm):
    ev = eventos(mm)
    t = ev.assign(c=np.where(ev.costo_mxn_intervencion.notna(), 'Con monto', 'Sin monto')).groupby(['camion_id', 'c']).size().unstack(fill_value=0)
    for c in ('Con monto', 'Sin monto'):
        if c not in t:
            t[c] = 0
    fig, ax = plt.subplots(figsize=(6.4, 2.4))
    ax.bar(t.index, t['Con monto'], color=INK, width=.6, label='Con monto')
    ax.bar(t.index, t['Sin monto'], bottom=t['Con monto'], color='#d3d8dc', width=.6, label='Sin monto')
    ax.legend(frameon=False, fontsize=8, loc='upper left', ncol=2); ax.set_ylabel('Intervenciones', fontsize=8, color=STEEL); _limpiar(ax)
    return fig


def g_mensual(mm):
    ev = eventos(mm)
    if 'fecha_calidad' in ev:
        ev = ev[ev.fecha_calidad.ne('solo_anio')]
    ev = ev.assign(f=pd.to_datetime(ev.fecha)).dropna(subset=['f'])
    if ev.empty:
        return None
    s = ev.groupby(ev.f.dt.to_period('M')).size()
    s = s.reindex(pd.period_range(s.index.min(), s.index.max(), freq='M'), fill_value=0)
    fig, ax = plt.subplots(figsize=(6.4, 2.3))
    ax.fill_between(range(len(s)), s.values, color=GOLD, alpha=.25); ax.plot(range(len(s)), s.values, color=INK, lw=1.8)
    paso = max(1, len(s) // 8)
    ax.set_xticks(range(0, len(s), paso)); ax.set_xticklabels([f'{MESES[p.month - 1]} {str(p.year)[2:]}' for p in s.index[::paso]])
    ax.set_ylabel('Intervenciones', fontsize=8, color=STEEL); ax.grid(axis='y', color='#eceff1'); _limpiar(ax)
    return fig


def g_prediccion(hist, pred):
    fig, ax = plt.subplots(figsize=(6.4, 2.3))
    h = hist.tail(26)
    ax.bar(h.index, h.values, color='#d3d8dc', width=5)
    ax.fill_between(pred.semana, pred.bajo, pred.alto, color=GOLD, alpha=.25, lw=0)
    ax.plot(pred.semana, pred.prediccion, color=GOLD, lw=2.4, marker='o', ms=3.5)
    ax.set_ylabel('Intervenciones por semana', fontsize=8, color=STEEL); _limpiar(ax)
    fig.autofmt_xdate(rotation=0, ha='center'); ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d/%m'))
    return fig


def _tarjetas(k, est):
    vals = [(f"{k['intervenciones']:,}", 'INTERVENCIONES'), (_money(k['gasto_mxn']), 'GASTO REGISTRADO (PARCIAL)'),
            (('$' + f"{k['promedio_mxn']:,.0f}") if k['promedio_mxn'] is not None else 'Sin base', 'COSTO PROMEDIO CON MONTO'),
            (f"{k['pct_reincidencia']:.1f}", 'REPETICIONES / 100 INTERV.')]
    celdas = [[Paragraph(v, est['kv']), ] for v, _ in vals]
    t = Table([[Paragraph(v, est['kv']) for v, _ in vals], [Paragraph(l, est['kl']) for _, l in vals]], colWidths=[4.3 * cm] * 4)
    t.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), .6, colors.HexColor(LINE)), ('LINEAFTER', (0, 0), (-2, -1), .6, colors.HexColor(LINE)),
                           ('LINETOP', (0, 0), (-1, 0), 3, colors.HexColor(GOLD)), ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
                           ('LEFTPADDING', (0, 0), (-1, -1), 10), ('TOPPADDING', (0, 0), (-1, 0), 9), ('BOTTOMPADDING', (0, 0), (-1, 0), 1),
                           ('TOPPADDING', (0, 1), (-1, 1), 0), ('BOTTOMPADDING', (0, 1), (-1, 1), 8)]))
    return t


def _tabla_alertas(al, est, max_filas=14):
    if al is None or al.empty:
        return [Paragraph('No hay alertas con los datos actuales.', est['p'])]
    filas = [[Paragraph('<b>Nivel</b>', est['cel']), Paragraph('<b>Camión</b>', est['cel']), Paragraph('<b>Alerta</b>', est['cel']), Paragraph('<b>Qué hacer</b>', est['cel'])]]
    for _, r in al.head(max_filas).iterrows():
        col = SEV[r.severidad]
        filas.append([Paragraph(f'<font color="{col}"><b>{r.severidad}</b></font>', est['cel']), Paragraph(r.camion_id, est['celb']),
                      Paragraph(f'<b>{r.tipo}.</b> {r.detalle}', est['cel']), Paragraph(r.accion, est['cel'])])
    t = Table(filas, colWidths=[1.5 * cm, 1.6 * cm, 8.2 * cm, 5.7 * cm], repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eceff1')), ('LINEBELOW', (0, 0), (-1, -1), .4, colors.HexColor(LINE)),
                           ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
    out = [t]
    if len(al) > max_filas:
        out.append(Paragraph(f'Se muestran las {max_filas} más importantes de {len(al)}. El resto está en el tablero.', est['peq']))
    return out


def generar_pdf(mm, alertas=None, periodo='', filtros='', corte=None, historial=None, prediccion=None, lectura=None) -> bytes:
    """mm: filas de mantenimiento ya filtradas. historial: Serie semanal (índice fecha). prediccion: DataFrame semana/prediccion/bajo/alto."""
    est = _estilos(); k = resumen(mm)
    buf = io.BytesIO()
    W, H = letter
    hoy = datetime.now(); fecha_txt = f'{hoy.day} de {["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"][hoy.month - 1]} de {hoy.year}'
    def pagina(c, d):
        c.saveState()
        if d.page == 1:
            c.setFillColor(colors.HexColor(INK)); c.rect(0, H - 4.1 * cm, W, 4.1 * cm, stroke=0, fill=1)
            c.setFillColor(colors.HexColor(GOLD)); c.rect(0, H - 4.1 * cm, W, .22 * cm, stroke=0, fill=1)
            c.setFont('Helvetica-Bold', 9); c.setFillColor(colors.HexColor(GOLD)); c.drawString(2 * cm, H - 1.35 * cm, 'MINETRAC  ·  CONTROL DE MAQUINARIA')
            c.setFillColor(colors.white); c.setFont('Helvetica-Bold', 23); c.drawString(2 * cm, H - 2.45 * cm, 'Reporte de mantenimiento de la flota')
            c.setFillColor(colors.HexColor('#cfd5da')); c.setFont('Helvetica', 9.5)
            c.drawString(2 * cm, H - 3.15 * cm, f'{periodo}  ·  {filtros}')
            c.drawString(2 * cm, H - 3.7 * cm, f'Generado el {fecha_txt}' + (f'  ·  datos hasta el {pd.Timestamp(corte):%d/%m/%Y}' if corte is not None else ''))
        else:
            c.setFillColor(colors.HexColor(GOLD)); c.rect(0, H - .5 * cm, W, .5 * cm, stroke=0, fill=1)
        c.setStrokeColor(colors.HexColor(LINE)); c.line(2 * cm, 1.5 * cm, W - 2 * cm, 1.5 * cm)
        c.setFont('Helvetica', 7.6); c.setFillColor(colors.HexColor(STEEL))
        c.drawString(2 * cm, 1.05 * cm, 'MineTrac · Máquinas Centella · Información real de la bitácora de camiones. Importes en MXN.')
        c.drawRightString(W - 2 * cm, 1.05 * cm, f'Página {d.page}')
        c.restoreState()
    doc = BaseDocTemplate(buf, pagesize=letter, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.6 * cm, bottomMargin=2 * cm,
                          title='Reporte de mantenimiento · MineTrac', author='MineTrac')
    primera = Frame(2 * cm, 2 * cm, W - 4 * cm, H - 2 * cm - 4.7 * cm, id='f1', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    resto = Frame(2 * cm, 2 * cm, W - 4 * cm, H - 2 * cm - 1.4 * cm, id='f2', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id='uno', frames=[primera], onPage=pagina, autoNextPageTemplate='resto'), PageTemplate(id='resto', frames=[resto], onPage=pagina)])
    story = [Spacer(1, 0)]
    story.append(_tarjetas(k, est)); story.append(Spacer(1, 6))
    if lectura:
        story.append(Paragraph(lectura, est['p']))
    story.append(Paragraph('Qué cuesta y dónde se concentra', est['h2']))
    f1 = g_componentes(mm)
    story.append(_png(f1, 16.5) if f1 else Paragraph('Esta selección no tiene montos anotados.', est['p']))
    story.append(Paragraph('Gasto por componente, solo intervenciones con monto. Si una intervención toca varios sistemas, el monto se reparte en partes iguales.', est['peq']))
    story.append(Paragraph('Intervenciones por camión', est['h2'])); story.append(_png(g_camiones(mm), 16.5))
    f3 = g_mensual(mm)
    if f3:
        story.append(Paragraph('Actividad mes a mes', est['h2'])); story.append(_png(f3, 16.5))
        story.append(Paragraph('Solo intervenciones con día conocido.', est['peq']))
    story.append(Paragraph('Alertas de mantenimiento', est['h2']))
    if alertas is not None and len(alertas):
        c = alertas.severidad.value_counts()
        story.append(Paragraph(f'{int(c.get("Alta", 0))} altas · {int(c.get("Media", 0))} medias · {int(c.get("Info", 0))} informativas. '
                               'Se calculan con la bitácora (días calendario y repeticiones); aún no hay horas trabajadas para alertar por horómetro.', est['p']))
    story.extend(_tabla_alertas(alertas, est))
    if historial is not None and prediccion is not None and len(prediccion):
        story.append(Paragraph('Qué esperar en las próximas semanas', est['h2']))
        story.append(_png(g_prediccion(historial, prediccion), 16.5))
        story.append(Paragraph(f'Se esperan unas {prediccion.prediccion.sum():.0f} intervenciones en {len(prediccion)} semanas (alrededor de {prediccion.prediccion.mean():.1f} por semana). '
                               'Es una referencia de ritmo del taller, no un pronóstico de fallas individuales. Usa toda la bitácora de camiones, sin los filtros.', est['peq']))
    story.append(Paragraph('Qué falta para decidir mejor', est['h2']))
    story.append(Paragraph(f"Solo {k['pct_con_monto']:.0f}% de las intervenciones tiene monto anotado. Faltan tipo de pieza (original o genérica), proveedor y horómetro al cambio. "
                           'Con esos datos se podrá calcular el costo por hora útil de cada refacción.', est['p']))
    doc.build(story)
    return buf.getvalue()
