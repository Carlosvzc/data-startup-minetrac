
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core import spectral

TEAL='#0b857a'
BLUE='#4d84b5'
GRAY='#c8d9e1'
GOLD='#dba047'
def views(d):
    daily=d.groupby('fecha',as_index=False).agg(ingreso_mxn=('ingreso_mxn','sum'),horas=('horas_trabajadas_h','sum'))
    category=d.groupby('categoria',as_index=False).ingreso_mxn.sum().sort_values('ingreso_mxn',ascending=False)
    eq=d.groupby('equipo_id',as_index=False).agg(ingreso_mxn=('ingreso_mxn','sum'),margen=('margen_directo_mxn','sum'),horas=('horas_trabajadas_h','sum'),mantenimiento=('costo_mantenimiento_mxn','sum'))
    eq['margen_pct']=np.where(eq.ingreso_mxn.ne(0),100*eq.margen/eq.ingreso_mxn,np.nan)
    eq['mant_h']=np.where(eq.horas.ne(0),eq.mantenimiento/eq.horas,np.nan)
    weekday=daily.copy()
    weekday['weekday']=pd.to_datetime(weekday.fecha).dt.dayofweek
    wk=weekday.groupby('weekday',as_index=False).horas.mean()
    wk['dia']=wk.weekday.map(dict(enumerate(['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'])))
    full_names=['lunes','martes','miércoles','jueves','viernes','sábado','domingo']
    high=wk.loc[wk.horas.idxmax()];low=wk.loc[wk.horas.idxmin()]
    spec=None;peaks=[];fft_message=''
    try:
        spec,peaks=spectral(d)
    except ValueError as error:
        fft_message=str(error)
    top=category.iloc[0]
    margin=eq.loc[eq.margen_pct.idxmax()] if eq.margen_pct.notna().any() else eq.iloc[0]
    maint=eq.loc[eq.mant_h.idxmax()] if eq.mant_h.notna().any() else eq.iloc[0]
    share=100*top.ingreso_mxn/category.ingreso_mxn.sum() if category.ingreso_mxn.sum() else 0
    weekly_change=100*(high.horas/low.horas-1) if low.horas else 0
    # Keep six titles / data structures available for the E1 report builder.
    titles=[
        f"Los ingresos diarios alcanzan hasta $"+f"{daily.ingreso_mxn.max():,.0f} MXN",
        f"{top.categoria} concentra el {share:.1f}% de los ingresos",
        f"{margin.equipo_id} lidera el margen directo con {margin.margen_pct:.1f}%",
        f"{maint.equipo_id} requiere revisar su mantenimiento: $"+f"{maint.mant_h:.2f}/h",
        f"El {full_names[int(high.weekday)]} registra {weekly_change:.1f}% más actividad que el {full_names[int(low.weekday)]}",
        f"La actividad se repite cada {peaks[0]['periodo_dias']:.0f} y {peaks[1]['periodo_dias']:.0f} días" if len(peaks)>1 else 'Ciclos de la actividad diaria'
    ]
    f0=go.Figure()
    f0.add_trace(go.Scatter(x=daily.fecha,y=daily.ingreso_mxn/1000,mode='lines',line=dict(color='#9ccbc6',width=1),name='Ingreso diario',hovertemplate='%{x}<br>Ingreso diario: $%{y:,.1f} mil MXN<extra></extra>'))
    smooth=daily.ingreso_mxn.rolling(7,min_periods=7).mean()/1000
    f0.add_trace(go.Scatter(x=daily.fecha,y=smooth,mode='lines',line=dict(color=TEAL,width=2.8),name='Promedio de 7 días',hovertemplate='%{x}<br>Promedio de 7 días: $%{y:,.1f} mil MXN<extra></extra>'))
    f0.update_yaxes(title='Miles de MXN',tickprefix='$')
    f0.update_xaxes(title=None,nticks=6)
    cat_plot=category.sort_values('ingreso_mxn')
    f1=go.Figure(go.Bar(x=cat_plot.ingreso_mxn/1e6,y=cat_plot.categoria,orientation='h',marker_color=[TEAL if x==top.categoria else '#8eb8c9' for x in cat_plot.categoria],text=[f"$"+f"{v/1e6:.2f} M" for v in cat_plot.ingreso_mxn],textposition='outside',cliponaxis=False,hovertemplate='%{y}<br>$%{x:,.2f} millones MXN<extra></extra>'))
    f1.update_xaxes(title='Millones de MXN',range=[0,max(cat_plot.ingreso_mxn)/1e6*1.28])
    f1.update_yaxes(title=None)
    m=eq.sort_values('margen_pct')
    f2=go.Figure(go.Bar(x=m.margen_pct,y=m.equipo_id,orientation='h',marker_color=[TEAL if x==margin.equipo_id else '#9bbdcc' for x in m.equipo_id],text=[f"{v:.1f}%" for v in m.margen_pct],textposition='outside',cliponaxis=False,hovertemplate='Equipo %{y}<br>Margen directo: %{x:.1f}%<extra></extra>'))
    f2.update_xaxes(title='Margen directo (%)',range=[min(0,float(m.margen_pct.min())*1.2),max(1,float(m.margen_pct.max())*1.2)])
    f2.update_yaxes(title=None,type='category',automargin=True)
    c=eq.sort_values('mant_h')
    f3=go.Figure(go.Bar(x=c.mant_h,y=c.equipo_id,orientation='h',marker_color=[GOLD if x==maint.equipo_id else '#9bbdcc' for x in c.equipo_id],text=[f"$"+f"{v:.2f}" for v in c.mant_h],textposition='outside',cliponaxis=False,hovertemplate='Equipo %{y}<br>Mantenimiento: $%{x:.2f} MXN/h<extra></extra>'))
    f3.update_xaxes(title='MXN por hora trabajada',range=[0,max(1,float(c.mant_h.max())*1.3)])
    f3.update_yaxes(title=None,type='category',automargin=True)
    f4=go.Figure(go.Bar(x=wk.dia,y=wk.horas,marker_color=[TEAL if x==high.weekday else '#9bbdcc' for x in wk.weekday],text=[f"{v:.0f} h" for v in wk.horas],textposition='outside',cliponaxis=False,hovertemplate='%{x}<br>Promedio diario: %{y:.1f} horas<extra></extra>'))
    f4.update_xaxes(title=None)
    f4.update_yaxes(title='Horas diarias de la selección',range=[0,max(wk.horas)*1.22])
    f5=None
    if spec is not None:
        sp=spec[spec.periodo_dias.between(2,60)].sort_values('periodo_dias')
        f5=go.Figure(go.Scatter(x=sp.periodo_dias,y=sp.amplitud_h,mode='lines',line=dict(color=BLUE,width=2),fill='tozeroy',fillcolor='rgba(77,132,181,.07)',hovertemplate='Periodo: %{x:.2f} días<br>Amplitud: %{y:.2f} h<extra></extra>'))
        for peak in peaks[:2]:
            f5.add_vline(x=peak['periodo_dias'],line_dash='dot',line_color=TEAL)
            f5.add_annotation(x=peak['periodo_dias'],y=peak['amplitud_h'],text=f"<b>{peak['periodo_dias']:.1f} días</b>",showarrow=True,arrowhead=0,ax=24,ay=-28,font=dict(color=TEAL,size=12))
        f5.update_xaxes(title='Duración del ciclo (días)',tickvals=[2,7,15,30,45,60],range=[2,60])
        f5.update_yaxes(title='Fuerza del ciclo · amplitud (h)',rangemode='tozero')
    figs=[f0,f1,f2,f3,f4,f5]
    for i,f in enumerate(figs):
        if f is None:continue
        f.update_layout(template='plotly_white',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',margin=dict(l=8,r=30,t=30,b=15),height=max(360,len(eq)*24+60) if i in [2,3] else 320,font=dict(family='Segoe UI, Arial',size=12,color='#607687'),showlegend=i==0,hoverlabel=dict(bgcolor='white',font_color='#183342'),legend=dict(orientation='h',x=0,y=1.17,font_size=11),bargap=.32)
        f.update_xaxes(showgrid=False,zeroline=False,linecolor='#dbe5ea',tickfont_size=11)
        f.update_yaxes(showgrid=i in [0,4,5],gridcolor='#e9eff3',zeroline=False,linecolor='#dbe5ea',tickfont_size=11)
    return list(zip(titles,figs)),{'daily':daily,'category':category,'equipment':eq,'weekday':wk,'spectrum':spec,'peaks':peaks,'titles':titles,'fft_message':fft_message,'share':share}

