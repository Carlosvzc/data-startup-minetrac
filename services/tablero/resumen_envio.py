"""Arma todo lo que lleva el correo (alertas, PDF y cuerpo) a partir de los datos. Lo usan el tablero y el script programado."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import alertas as al
import correo
import reporte
from core import resumen

ROOT = Path(__file__).resolve().parents[2]


def _prediccion(raiz: Path = ROOT, semanas: int = 4):
    p = raiz / 'data/clean/e2_resultados.json'
    if not p.exists():
        return None, None
    import e2
    r2 = json.loads(p.read_text(encoding='utf-8'))
    return pd.Series(r2['serie']['valores'], index=pd.to_datetime(r2['serie']['fechas'])), e2.pronostico(r2, semanas)


def paquete(mant: pd.DataFrame, raiz: Path = ROOT, periodo: str | None = None, filtros: str = '7 camiones · todos los sistemas'):
    """Devuelve (asunto, html, texto, pdf, alertas_df) para la bitácora completa de camiones."""
    corte = al.fecha_corte(mant)
    alertas = al.calcular(mant, corte)
    k = resumen(mant); ra = al.resumen_alertas(alertas)
    ev = mant[mant.get('fecha_calidad', pd.Series('ok', index=mant.index)).ne('solo_anio')]
    periodo = periodo or f"{pd.to_datetime(ev.fecha).min():%d/%m/%Y} a {pd.to_datetime(ev.fecha).max():%d/%m/%Y}"
    lectura = (f"Hay {ra['Alta']} alertas altas y {ra['Media']} medias en los camiones. "
               f"La bitácora suma {k['intervenciones']:,} intervenciones y ${k['gasto_mxn']:,.0f} MXN con monto anotado (parcial).")
    hist, pred = _prediccion(raiz)
    pdf = reporte.generar_pdf(mant, alertas, periodo, filtros, corte, hist, pred, lectura)
    top = alertas.head(6).to_dict('records') if len(alertas) else []
    html_c = correo.cuerpo_html('Resumen de mantenimiento de la flota', lectura, k, ra, top, periodo + ' · datos hasta ' + f'{corte:%d/%m/%Y}')
    texto = lectura + '\n\n' + '\n'.join(f"[{a['severidad']}] {a['camion_id']}: {a['tipo']}. {a['detalle']}" for a in top) + '\n\nReporte completo en el PDF adjunto.'
    return f"MineTrac · Resumen de mantenimiento ({corte:%d/%m/%Y})", html_c, texto, pdf, alertas
