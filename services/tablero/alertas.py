"""Alertas de mantenimiento de los camiones, calculadas solo con la bitácora real.

Qué NO hacen: no usan horas trabajadas (la empresa aún no las captura), así que no hay alertas por horómetro.
Todas las reglas miran días calendario y repeticiones registradas, y se evalúan a una fecha de corte
(por defecto, la última fecha de la bitácora) para que un atraso de captura no se confunda con un camión descuidado.
"""
from __future__ import annotations
import pandas as pd

UMBRALES = {
    'dias_sin_servicio_media': 120,   # días desde el último servicio preventivo registrado
    'dias_sin_servicio_alta': 240,
    'ventana_repeticion': 30,         # misma pieza o sistema del mismo camión
    'ventana_reciente': 60,           # solo alertamos repeticiones que ocurrieron en los últimos N días
    'sistema_veces_90d': 3,           # mismo sistema 3 o más veces en 90 días
    'pico_actividad': 2.0,            # últimos 30 días ≥ 2× el promedio mensual del camión (y al menos 4)
    'dias_sin_registro': 90,          # camión sin ninguna anotación (posible captura atrasada)
}
ORDEN = {'Alta': 0, 'Media': 1, 'Info': 2}
COLUMNAS = ['severidad', 'camion_id', 'tipo', 'detalle', 'accion', 'fecha_ref']


def _eventos(m: pd.DataFrame) -> pd.DataFrame:
    ev = m.drop_duplicates(['camion_id', 'evento_id']).copy()
    if 'fecha_calidad' in ev:
        ev = ev[ev.fecha_calidad.ne('solo_anio')]
    ev['fecha'] = pd.to_datetime(ev.fecha)
    return ev.dropna(subset=['fecha'])


def fecha_corte(m: pd.DataFrame):
    ev = _eventos(m)
    return ev.fecha.max().normalize() if len(ev) else pd.Timestamp.today().normalize()


def _fila(sev, camion, tipo, detalle, accion, ref=None):
    return dict(severidad=sev, camion_id=camion, tipo=tipo, detalle=detalle, accion=accion,
                fecha_ref=None if ref is None else pd.Timestamp(ref).date().isoformat())


def calcular(m: pd.DataFrame, corte=None, umbrales: dict | None = None) -> pd.DataFrame:
    """Devuelve una tabla de alertas ordenada por severidad. `m` es mantenimiento.csv (una fila por intervención y sistema)."""
    u = {**UMBRALES, **(umbrales or {})}
    ev = _eventos(m)
    if ev.empty:
        return pd.DataFrame(columns=COLUMNAS)
    corte = pd.Timestamp(corte).normalize() if corte is not None else ev.fecha.max().normalize()
    ev = ev[ev.fecha <= corte]
    mm = m.copy(); mm['fecha'] = pd.to_datetime(mm.fecha, errors='coerce')
    out = []
    for cam in sorted(m.camion_id.unique()):
        e = ev[ev.camion_id == cam]
        # 1) servicio preventivo
        serv = mm[(mm.camion_id == cam) & (mm.sistema == 'Servicio preventivo') & mm.fecha.notna() & (mm.fecha <= corte)]
        if serv.empty:
            out.append(_fila('Media', cam, 'Servicio preventivo', 'No hay ningún servicio preventivo registrado en la bitácora.',
                             'Confirmar con el taller si se le han hecho servicios y capturarlos.'))
        else:
            ult = serv.fecha.max(); dias = (corte - ult).days
            if dias >= u['dias_sin_servicio_alta']:
                out.append(_fila('Alta', cam, 'Servicio preventivo', f'Último servicio hace {dias} días ({ult:%d/%m/%Y}).',
                                 'Programar servicio preventivo.', ult))
            elif dias >= u['dias_sin_servicio_media']:
                out.append(_fila('Media', cam, 'Servicio preventivo', f'Último servicio hace {dias} días ({ult:%d/%m/%Y}).',
                                 'Revisar si toca el siguiente servicio.', ult))
        if e.empty:
            continue
        # 2) repeticiones recientes (mismo componente en ≤30 días)
        rec = mm[(mm.camion_id == cam) & (mm.reincidencia_30d.astype(str).str.lower() == 'true') & (mm.fecha > corte - pd.Timedelta(days=u['ventana_reciente'])) & (mm.fecha <= corte)]
        for comp, g in rec.groupby('componente'):
            f = g.fecha.max()
            out.append(_fila('Alta', cam, 'Repetición reciente', f'«{comp}» volvió a registrarse en menos de {u["ventana_repeticion"]} días (último: {f:%d/%m/%Y}).',
                             'Pedir diagnóstico antes de repetir la compra; revisar garantía.', f))
        # 3) mismo sistema muchas veces en 90 días
        r90 = e[(e.fecha > corte - pd.Timedelta(days=90))]
        sis = mm[(mm.camion_id == cam) & mm.evento_id.isin(r90.evento_id)]
        for s, g in sis.groupby('sistema'):
            n = g.evento_id.nunique()
            if s != 'Servicio preventivo' and n >= u['sistema_veces_90d']:
                out.append(_fila('Media', cam, 'Sistema con muchas intervenciones', f'{s}: {n} intervenciones en los últimos 90 días.',
                                 'Revisar la causa de fondo del sistema.', g.fecha.max()))
        # 4) pico de actividad
        r30 = int((e.fecha > corte - pd.Timedelta(days=30)).sum())
        meses = max((e.fecha.max() - e.fecha.min()).days / 30.4, 1)
        prom = len(e) / meses
        if r30 >= 4 and r30 >= u['pico_actividad'] * prom:
            out.append(_fila('Media', cam, 'Pico de actividad', f'{r30} intervenciones en 30 días; su promedio es {prom:.1f} al mes.',
                             'Ver qué cambió: operación, operador o una falla de origen.', e.fecha.max()))
        # 5) sin registro reciente
        dias_reg = (corte - e.fecha.max()).days
        if dias_reg >= u['dias_sin_registro']:
            out.append(_fila('Info', cam, 'Sin registros recientes', f'Última anotación hace {dias_reg} días ({e.fecha.max():%d/%m/%Y}).',
                             'Confirmar si está parado o si falta capturar su bitácora.', e.fecha.max()))
    df = pd.DataFrame(out, columns=COLUMNAS)
    if df.empty:
        return df
    df['_o'] = df.severidad.map(ORDEN)
    return df.sort_values(['_o', 'camion_id', 'tipo']).drop(columns='_o').reset_index(drop=True)


def resumen_alertas(df: pd.DataFrame) -> dict:
    return {s: int((df.severidad == s).sum()) for s in ORDEN} if len(df) else {s: 0 for s in ORDEN}
