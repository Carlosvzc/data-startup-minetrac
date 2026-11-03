"""Gráficas y tablas de la libreta de taller (equipos que no son camiones)."""
import pandas as pd
import plotly.graph_objects as go
from figures import _estilo, TEAL, GOLD, SOFT, GRAY, BLUE


def filtrar(lib, equipos):
    return lib[lib.equipo_id.isin(equipos)] if equipos else lib


def graficas(lib):
    """Devuelve cuatro figuras: por equipo, por sistema, por mes y servicios por intervalo (cualquiera puede ser None)."""
    if lib.empty:
        return [None] * 4
    por = lib.assign(tipo=lib.es_servicio.map({True: 'Servicio preventivo', False: 'Reparación, falla o compra'})).groupby(['equipo_id', 'tipo']).size().unstack(fill_value=0)
    for c in ('Servicio preventivo', 'Reparación, falla o compra'):
        if c not in por:
            por[c] = 0
    por = por.assign(t=por.sum(axis=1)).sort_values('t')
    f0 = go.Figure([go.Bar(y=por.index, x=por['Reparación, falla o compra'], name='Reparación, falla o compra', orientation='h', marker_color=SOFT),
                    go.Bar(y=por.index, x=por['Servicio preventivo'], name='Servicio preventivo', orientation='h', marker_color=TEAL)])
    f0.update_layout(barmode='stack')
    f0.update_xaxes(title='Anotaciones en la libreta')
    s = lib[~lib.es_servicio].groupby('sistema').agg(n=('evento_id', 'size'), gasto=('monto_mxn', 'sum')).sort_values('n')
    f1 = None
    if len(s):
        top = s.n.idxmax()
        f1 = go.Figure(go.Bar(y=s.index, x=s.n, orientation='h', marker_color=[GOLD if i == top else SOFT for i in s.index],
                              text=s.n, textposition='outside', cliponaxis=False,
                              customdata=s.gasto, hovertemplate='%{y}<br>%{x} anotaciones<br>Monto único anotado: $%{customdata:,.0f} MXN<extra></extra>'))
        f1.update_xaxes(title='Anotaciones (sin servicios preventivos)', range=[0, float(s.n.max()) * 1.2])
        f1.update_yaxes(automargin=True)
    d = lib.dropna(subset=['fecha']).assign(mes=lambda x: pd.to_datetime(x.fecha).dt.to_period('M').dt.to_timestamp())
    d = d[d.mes >= '2024-04-01']
    f2 = None
    if len(d):
        mm = d.groupby('mes').size()
        f2 = go.Figure(go.Scatter(x=mm.index, y=mm.values, mode='lines+markers', line=dict(color=TEAL, width=2.5), marker=dict(size=6),
                                  hovertemplate='%{x|%b %Y}<br>%{y} anotaciones<extra></extra>'))
        f2.update_yaxes(title='Anotaciones por mes')
    sv = lib.dropna(subset=['intervalo_servicio_h'])
    f3 = None
    if len(sv):
        c = sv.intervalo_servicio_h.astype(int).value_counts().sort_index()
        f3 = go.Figure(go.Bar(x=[f'{i:,} h' for i in c.index], y=c.values, marker_color=BLUE, text=c.values, textposition='outside', cliponaxis=False))
        f3.update_yaxes(title='Servicios anotados', range=[0, float(c.max()) * 1.2])
    figs = [f0, f1, f2, f3]
    _estilo(figs, [max(300, 26 * len(por) + 90), 340, 300, 300])
    return figs


def kpis(lib):
    no_serv = lib[~lib.es_servicio]
    rep = 0
    for _, g in no_serv.dropna(subset=['fecha']).groupby(['equipo_id', 'sistema']):
        rep += int(pd.to_datetime(g.fecha).sort_values().diff().dt.days.between(0, 30).sum())
    return {'anotaciones': int(len(lib)), 'equipos': int(lib.equipo_id.nunique()),
            'servicios': int(lib.es_servicio.sum()), 'con_intervalo': int(lib.intervalo_servicio_h.notna().sum()),
            'gasto_mxn': float(lib.monto_mxn.sum()), 'con_monto': int(lib.monto_mxn.notna().sum()),
            'repeticiones': rep, 'rep_100': 100 * rep / max(len(no_serv), 1)}
