"""Pestaña de análisis y predicción del E2 (lee data/clean/e2_resultados.json, generado por scripts/pipeline_e2.py)."""
from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

INK, GOLD, BLUE, SOFT, GRAY = '#2b3138', '#f2b600', '#3e5c76', '#9aa6b0', '#d3d8dc'


def _base(fig, h=340):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      font=dict(family='Barlow, sans-serif', size=13, color=INK), legend=dict(orientation='h', y=1.12, x=0))
    fig.update_xaxes(showgrid=False); fig.update_yaxes(gridcolor='#eceff1', zeroline=False)
    return fig


def pronostico(res: dict, semanas: int) -> pd.DataFrame:
    """Predicción recursiva con la regresión a mano: y_t = b0 + b1·t + b2·y_(t-1). Banda aproximada ±1.96·RMSE."""
    b = res['regresion']['beta']; rmse = res['regresion']['rmse']
    serie = res['serie']; y = serie['valores'][-1]; t = serie['semanas'] - 1
    ult = pd.Timestamp(serie['fechas'][-1]); filas = []
    for h in range(1, semanas + 1):
        t += 1; y = max(0.0, b[0] + b[1] * t + b[2] * y)
        filas.append({'semana': ult + pd.Timedelta(weeks=h), 'prediccion': y,
                      'bajo': max(0.0, y - 1.96 * rmse), 'alto': y + 1.96 * rmse})
    return pd.DataFrame(filas)


def fig_serie(res, suavizado, semanas):
    s = res['serie']; f = pd.to_datetime(s['fechas']); v = pd.Series(s['valores'], index=f)
    fig = go.Figure()
    fig.add_bar(x=f, y=v, name='Anotaciones por semana', marker_color=GRAY)
    if suavizado > 1:
        fig.add_scatter(x=f, y=v.rolling(suavizado, min_periods=1).mean(), name=f'Promedio móvil {suavizado} sem.', line=dict(color=INK, width=2.5))
    p = pronostico(res, semanas)
    fig.add_scatter(x=p.semana, y=p.alto, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip')
    fig.add_scatter(x=p.semana, y=p.bajo, mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(242,182,0,.25)', name='Banda ±1.96·RMSE', hoverinfo='skip')
    fig.add_scatter(x=p.semana, y=p.prediccion, name='Predicción', line=dict(color=GOLD, width=3), mode='lines+markers')
    return _base(fig, 380), p


def fig_descomposicion(res):
    d = res['descomposicion']; f = pd.to_datetime(res['serie']['fechas'])
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=.06, subplot_titles=('Tendencia', 'Estacionalidad (52 semanas, indicativa)', 'Residuo'))
    for i, (k, c) in enumerate([('tendencia', GOLD), ('estacional', BLUE), ('residuo', SOFT)], 1):
        fig.add_scatter(x=f, y=d[k], line=dict(color=c, width=2), showlegend=False, row=i, col=1)
    return _base(fig, 520)


def fig_acf(res, clave, nombre):
    a = res[clave][nombre]; b = res[clave]['banda']
    fig = go.Figure(go.Bar(x=list(range(len(a))), y=a, marker_color=INK))
    fig.add_hrect(y0=-b, y1=b, fillcolor=GOLD, opacity=.25, line_width=0)
    fig.update_xaxes(title='Rezago (semanas)')
    return _base(fig, 260)


def fig_residuos(res):
    g = res['regresion']
    fig = make_subplots(rows=1, cols=2, subplot_titles=('Residuos vs. valor ajustado', 'Distribución de residuos'))
    fig.add_scatter(x=g['ajustado'], y=g['residuos'], mode='markers', marker=dict(color=INK, size=6), showlegend=False, row=1, col=1)
    fig.add_hline(y=0, line_color=GOLD, row=1, col=1)
    fig.add_histogram(x=g['residuos'], marker_color=BLUE, nbinsx=18, showlegend=False, row=1, col=2)
    return _base(fig, 300)


def tabla_coef(res) -> pd.DataFrame:
    g = res['regresion']
    return pd.DataFrame({'Variable': g['variables'], 'Coeficiente β': g['beta'], 'Error estándar': g['error_estandar'], 't': g['t'], 'p': g['p_valor']})


def cargar(mode, bucket, region, root):
    import json
    try:
        if mode == 's3':
            import boto3
            return json.loads(boto3.client('s3', region_name=region).get_object(Bucket=bucket, Key='clean/e2_resultados.json')['Body'].read())
        p = root / 'data/clean/e2_resultados.json'
        return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None
    except Exception:
        return None
