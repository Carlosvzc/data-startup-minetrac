
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core import spectral
COLOR='#19b9ad'
def views(d):
    daily=d.groupby('fecha',as_index=False).agg(ingreso_mxn=('ingreso_mxn','sum'),horas=('horas_trabajadas_h','sum'))
    category=d.groupby('categoria',as_index=False).ingreso_mxn.sum().sort_values('ingreso_mxn',ascending=False)
    eq=d.groupby('equipo_id',as_index=False).agg(ingreso_mxn=('ingreso_mxn','sum'),margen=('margen_directo_mxn','sum'),horas=('horas_trabajadas_h','sum'),mantenimiento=('costo_mantenimiento_mxn','sum'))
    eq['margen_pct']=100*eq.margen/eq.ingreso_mxn
    eq['mant_h']=eq.mantenimiento/eq.horas
    weekday=daily.copy();weekday['weekday']=pd.to_datetime(weekday.fecha).dt.dayofweek
    wk=weekday.groupby('weekday',as_index=False).horas.mean()
    names=['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
    wk['dia']=wk.weekday.map(dict(enumerate(names)))
    high=wk.loc[wk.horas.idxmax()];low=wk.loc[wk.horas.idxmin()]
    spec,peaks=spectral(d)
    top=category.iloc[0];margin=eq.loc[eq.margen_pct.idxmax()];maint=eq.loc[eq.mant_h.idxmax()]
    titles=[
        f"Ingresos acumulados de la selección: $"+f"{d.ingreso_mxn.sum():,.0f} MXN",
        f"{top.categoria} aporta {100*top.ingreso_mxn/category.ingreso_mxn.sum():.1f}% de los ingresos",
        f"{margin.equipo_id} registra el mayor margen directo: {margin.margen_pct:.1f}%",
        f"{maint.equipo_id} tiene el mayor mantenimiento por hora: $"+f"{maint.mant_h:.2f}",
        f"{high.dia} promedia {100*(high.horas/low.horas-1):.1f}% más horas que {low.dia.lower()}",
        f"FFT: ciclos dominantes de {peaks[0]['periodo_dias']:.1f} y {peaks[1]['periodo_dias']:.1f} días" if len(peaks)>1 else "FFT de horas diarias"
    ]
    figs=[
        px.line(daily,x='fecha',y='ingreso_mxn',labels={'fecha':'Fecha','ingreso_mxn':'Ingresos (MXN)'}),
        px.bar(category,x='categoria',y='ingreso_mxn',labels={'categoria':'Categoría','ingreso_mxn':'Ingresos (MXN)'}),
        px.bar(eq.sort_values('margen_pct'),x='equipo_id',y='margen_pct',labels={'equipo_id':'Equipo','margen_pct':'Margen directo (%)'}),
        px.bar(eq.sort_values('mant_h',ascending=False),x='equipo_id',y='mant_h',labels={'equipo_id':'Equipo','mant_h':'Mantenimiento (MXN/h)'}),
        px.bar(wk,x='dia',y='horas',labels={'dia':'Día de semana','horas':'Horas diarias medias de la flota'}),
        px.line(spec[spec.periodo_dias.between(2,60)].sort_values('frecuencia_ciclos_dia'),x='frecuencia_ciclos_dia',y='amplitud_h',labels={'frecuencia_ciclos_dia':'Frecuencia (ciclos/día)','amplitud_h':'Amplitud (horas)'})
    ]
    for f in figs:
        f.update_layout(template='plotly_dark',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',margin=dict(l=20,r=20,t=15,b=20),height=310,font=dict(family='Arial',size=12),showlegend=False)
        f.update_traces(marker_color=COLOR) if f.data[0].type=='bar' else f.update_traces(line_color=COLOR)
    for peak in peaks[:2]:
        figs[-1].add_vline(x=peak['frecuencia_ciclos_dia'],line_dash='dot',line_color='#f5b84b')
    return list(zip(titles,figs)),{'daily':daily,'category':category,'equipment':eq,'weekday':wk,'spectrum':spec,'peaks':peaks,'titles':titles}

