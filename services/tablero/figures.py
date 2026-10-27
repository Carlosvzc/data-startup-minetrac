import numpy as np
import pandas as pd
import plotly.graph_objects as go
from core import eventos, resumen, serie_diaria, spectral

TEAL = '#0b857a'
BLUE = '#4d84b5'
GRAY = '#c8d9e1'
GOLD = '#dba047'
SOFT = '#9bbdcc'
DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']


def _estilo(figs, altos):
    for i, f in enumerate(figs):
        if f is None:
            continue
        f.update_layout(template='plotly_white', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=8, r=30, t=30, b=15), height=altos[i],
                        font=dict(family='Segoe UI, Arial', size=12, color='#607687'),
                        hoverlabel=dict(bgcolor='white', font_color='#183342'),
                        legend=dict(orientation='h', x=0, y=1.17, font_size=11), bargap=.32)
        f.update_xaxes(showgrid=False, zeroline=False, linecolor='#dbe5ea', tickfont_size=11)
        f.update_yaxes(showgrid=False, zeroline=False, linecolor='#dbe5ea', tickfont_size=11)



def _fmt_fecha(x):
    return pd.Timestamp(x).strftime('%d/%m/%Y')


def views(m):
    """Seis visualizaciones de la bitácora real. Devuelve [(titulo, figura)], datos auxiliares."""
    ev = eventos(m).copy()
    ev['fecha'] = pd.to_datetime(ev.fecha)
    aux = {}
    # 1) Gasto por componente (solo intervenciones con monto)
    comp = m.groupby('componente', as_index=False).costo_mxn.sum().query('costo_mxn>0').sort_values('costo_mxn', ascending=False)
    aux['componentes'] = comp
    if len(comp):
        top = comp.iloc[0]
        t = comp.head(10).sort_values('costo_mxn')
        f0 = go.Figure(go.Bar(x=t.costo_mxn / 1000, y=t.componente, orientation='h',
                              marker_color=[GOLD if x == top.componente else SOFT for x in t.componente],
                              text=[f"${v / 1000:,.0f} mil" for v in t.costo_mxn], textposition='outside', cliponaxis=False,
                              hovertemplate='%{y}<br>Gasto registrado: $%{x:,.1f} mil MXN<extra></extra>'))
        f0.update_xaxes(title='Miles de MXN (solo intervenciones con monto)', range=[0, float(t.costo_mxn.max()) / 1000 * 1.3])
        f0.update_yaxes(automargin=True)
        t0 = f"{top.componente} concentra el {100 * top.costo_mxn / comp.costo_mxn.sum():.0f}% del gasto registrado"
    else:
        f0, t0 = None, 'Sin montos registrados en esta selección'
    # 2) Intervenciones por camión, con y sin monto
    por = ev.assign(monto=np.where(ev.costo_mxn_intervencion.notna(), 'Con monto', 'Sin monto')).groupby(['camion_id', 'monto']).size().unstack(fill_value=0)
    for c in ('Con monto', 'Sin monto'):
        if c not in por:
            por[c] = 0
    por['total'] = por['Con monto'] + por['Sin monto']
    por = por.sort_values('total')
    aux['por_camion'] = por
    f1 = go.Figure()
    f1.add_trace(go.Bar(y=por.index, x=por['Con monto'], orientation='h', name='Con monto anotado', marker_color=TEAL,
                        hovertemplate='%{y}<br>Con monto: %{x}<extra></extra>'))
    f1.add_trace(go.Bar(y=por.index, x=por['Sin monto'], orientation='h', name='Sin monto anotado', marker_color=GRAY,
                        hovertemplate='%{y}<br>Sin monto: %{x}<extra></extra>'))
    f1.update_layout(barmode='stack')
    f1.update_xaxes(title='Intervenciones registradas')
    f1.update_yaxes(type='category', automargin=True)
    lider = por.index[-1]
    t1 = f"{lider} suma {int(por.total.iloc[-1])} intervenciones, la bitácora más activa"
    # 3) Línea de tiempo
    sin, con = ev[ev.costo_mxn_intervencion.isna()], ev[ev.costo_mxn_intervencion.notna()]
    f2 = go.Figure()
    f2.add_trace(go.Scatter(x=sin.fecha, y=sin.camion_id, mode='markers', name='Sin monto registrado',
                            marker=dict(color=GRAY, size=7, line=dict(color='white', width=.5)), customdata=sin.componente,
                            hovertemplate='%{y} · %{x|%d/%m/%Y}<br>%{customdata}<extra></extra>'))
    f2.add_trace(go.Scatter(x=con.fecha, y=con.camion_id, mode='markers', name='Con monto (tamaño = costo)',
                            marker=dict(color=TEAL, opacity=.75, size=np.clip(np.sqrt(con.costo_mxn_intervencion.fillna(0)) / 6, 8, 40),
                                        line=dict(color='white', width=.5)),
                            customdata=np.stack([con.componente, con.costo_mxn_intervencion], axis=-1),
                            hovertemplate='%{y} · %{x|%d/%m/%Y}<br>%{customdata[0]}<br>$%{customdata[1]:,.0f} MXN<extra></extra>'))
    f2.update_yaxes(categoryorder='array', categoryarray=sorted(ev.camion_id.unique(), reverse=True), automargin=True)
    f2.update_xaxes(title=None, nticks=7)
    t2 = f"{len(sin)} de {len(ev)} intervenciones no tienen monto anotado"
    # 4) Intervenciones por mes
    mes = ev.assign(mes=ev.fecha.dt.to_period('M').dt.to_timestamp()).groupby('mes').size()
    mes = mes.reindex(pd.date_range(mes.index.min(), mes.index.max(), freq='MS'), fill_value=0)
    aux['por_mes'] = mes
    pico = mes.idxmax()
    f3 = go.Figure(go.Bar(x=mes.index, y=mes.values, marker_color=[TEAL if x == pico else SOFT for x in mes.index],
                          hovertemplate='%{x|%b %Y}<br>Intervenciones: %{y}<extra></extra>'))
    f3.update_yaxes(title='Intervenciones por mes')
    f3.update_xaxes(title=None, nticks=8)
    t3 = f"{pico.strftime('%m/%Y')} fue el mes con más intervenciones: {int(mes.max())}"
    # 5) Días entre cambios del mismo componente
    vida = (m.dropna(subset=['vida_util_dias']).drop_duplicates(['camion_id', 'componente', 'fecha'])
            .groupby('componente').vida_util_dias.agg(['mean', 'count']).reset_index().query('count>=3'))
    aux['vida'] = vida
    if len(vida):
        vida = vida.sort_values('mean')
        best = vida.iloc[-1]
        f4 = go.Figure(go.Bar(x=vida['mean'], y=vida.componente, orientation='h',
                              marker_color=[TEAL if x == best.componente else SOFT for x in vida.componente],
                              text=[f"{v:.0f} d (n={int(n)})" for v, n in zip(vida['mean'], vida['count'])], textposition='outside',
                              cliponaxis=False, hovertemplate='%{y}<br>Promedio entre trabajos: %{x:.0f} días<extra></extra>'))
        f4.update_xaxes(title='Días entre trabajos (solo intervalos >30 días)', range=[0, float(vida['mean'].max()) * 1.3])
        f4.update_yaxes(automargin=True)
        w = vida.iloc[0]
        t4 = f"{w.componente} registra intervalos entre trabajos de {w['mean']:.0f} días en promedio"
    else:
        f4, t4 = None, 'Faltan intervalos repetidos para comparar trabajos'
    # 6) FFT de las intervenciones diarias
    serie = serie_diaria(m, inicio='2024-04-01')
    aux['serie'] = serie
    spec, peaks, msg = None, [], ''
    try:
        spec, peaks = spectral(serie)
    except ValueError as e:
        msg = str(e)
    aux.update(spectrum=spec, peaks=peaks, fft_message=msg)
    f5 = None
    if spec is not None:
        sp = spec[spec.periodo_dias.between(2, 60)].sort_values('periodo_dias')
        f5 = go.Figure(go.Scatter(x=sp.periodo_dias, y=sp.amplitud, mode='lines', line=dict(color=BLUE, width=2), fill='tozeroy',
                                  fillcolor='rgba(77,132,181,.07)', hovertemplate='Periodo: %{x:.2f} días<br>Amplitud: %{y:.3f}<extra></extra>'))
        for pk in peaks[:2]:
            f5.add_vline(x=pk['periodo_dias'], line_dash='dot', line_color=TEAL)
            f5.add_annotation(x=pk['periodo_dias'], y=pk['amplitud'], text=f"<b>{pk['periodo_dias']:.1f} días</b>", showarrow=True,
                              arrowhead=0, ax=24, ay=-28, font=dict(color=TEAL, size=12))
        f5.update_xaxes(title='Duración del ciclo (días)', tickvals=[2, 7, 15, 30, 45, 60], range=[2, 60])
        f5.update_yaxes(title='Fuerza del ciclo (intervenciones por día)', rangemode='tozero')
    t5 = (f"El ciclo dominante de las intervenciones es de {peaks[0]['periodo_dias']:.1f} días" if peaks else 'Ciclos de las intervenciones')
    figs = [f0, f1, f2, f3, f4, f5]
    _estilo(figs, [360, max(320, len(por) * 40 + 80), 340, 320, 360, 320])
    for i in (3, 5):
        if figs[i] is not None:
            figs[i].update_yaxes(showgrid=True, gridcolor='#e9eff3')
    f2.update_xaxes(showgrid=True, gridcolor='#e9eff3')
    for i, f in enumerate(figs):
        if f is not None:
            f.update_layout(showlegend=i in (1, 2), legend=dict(orientation='h', x=0, y=1.15, font_size=11))
    return list(zip([t0, t1, t2, t3, t4, t5], figs)), aux
