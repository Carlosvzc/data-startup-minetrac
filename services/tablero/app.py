
from pathlib import Path
import os,io,json,sys,html
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pandas as pd
import streamlit as st
from core import metrics
from figures import views

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
st.set_page_config(page_title='MineTrac | Control operativo',page_icon='⛏',layout='wide',initial_sidebar_state='expanded')
st.markdown('<style>'+ (HERE/'styles.css').read_text(encoding='utf-8-sig')+'</style>',unsafe_allow_html=True)
mode=os.environ.get('MINETRAC_STORAGE','local')
@st.cache_data(ttl=60)
def load(mode,bucket,region):
    if mode=='s3':
        import boto3
        client=boto3.client('s3',region_name=region)
        def obj(key):return client.get_object(Bucket=bucket,Key=key)['Body'].read()
        return pd.read_csv(io.BytesIO(obj('clean/operacion.csv'))),json.loads(obj('clean/resultados.json')),'Amazon S3 · '+bucket+'/clean/operacion.csv'
    if mode!='local':raise ValueError('Modo de almacenamiento desconocido.')
    return pd.read_csv(ROOT/'data/clean/operacion.csv'),json.loads((ROOT/'data/clean/resultados.json').read_text(encoding='utf-8')),'Demostración local'
try:
    d,result,source=load(mode,os.environ.get('MINETRAC_BUCKET',''),os.environ.get('AWS_DEFAULT_REGION','us-east-1'))
except Exception:
    st.error('No pudimos cargar los datos. Revisa la conexión o solicita al responsable que verifique el acceso a la fuente.')
    if st.button('Volver a intentar'):
        st.cache_data.clear();st.rerun()
    st.stop()

def safe(v):return html.escape(str(v))
def date_label(v):
    months=['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
    x=pd.Timestamp(v)
    return f'{x.day:02d} {months[x.month-1]} {x.year}'
def money(v):
    return '$'+(f'{v/1e6:,.2f} M' if abs(v)>=1e6 else f'{v:,.0f}')
def reset_filters():
    for key in ['category','equipment','location','billing','period']:
        st.session_state.pop(key,None)
def chart(title,fig,caption,key):
    with st.container(border=True):
        st.subheader(title)
        st.caption(caption)
        st.plotly_chart(fig,width='stretch',key=key,config={'displayModeBar':False,'responsive':True})

with st.sidebar:
    st.markdown('<div class="mt-brand"><span>M</span>MineTrac</div><div class="mt-sidebar-sub">CONTROL DE MAQUINARIA</div>',unsafe_allow_html=True)
    st.subheader('Tu selección')
    begin,end=pd.Timestamp(d.fecha.min()).date(),pd.Timestamp(d.fecha.max()).date()
    period=st.date_input('Periodo de análisis',value=(begin,end),min_value=begin,max_value=end,key='period',format='DD/MM/YYYY')
    category=st.selectbox('Tipo de maquinaria',['Toda la maquinaria']+sorted(d.categoria.unique()),key='category')
    options=sorted(d.loc[d.categoria.eq(category) if category!='Toda la maquinaria' else pd.Series(True,index=d.index),'equipo_id'].unique())
    if 'equipment' in st.session_state:
        st.session_state['equipment']=[x for x in st.session_state['equipment'] if x in options]
    equipment=st.multiselect('Equipos específicos',options,default=[],key='equipment',placeholder='Toda la flota',help='Déjalo vacío para incluir todos los equipos del tipo elegido.')
    with st.expander('Ubicación y modalidad'):
        location=st.selectbox('Ubicación',['Todas las ubicaciones']+sorted(d.ubicacion.unique()),key='location')
        billing=st.selectbox('Modalidad de cobro',['Todas las modalidades']+sorted(d.modalidad_cobro.unique()),key='billing',format_func=lambda x:{'hora':'Por hora','tonelada':'Por tonelada'}.get(x,x))
    st.button('Restablecer filtros',on_click=reset_filters,width='stretch')
    st.divider()
    st.caption('FUENTE DE INFORMACIÓN')
    st.markdown('<span class="mt-badge">'+('Datos conectados a AWS' if mode=='s3' else 'Demostración local')+'</span>',unsafe_allow_html=True)
    if st.button('Recargar datos',width='stretch'):
        st.cache_data.clear();st.rerun()
    st.caption('MineTrac · Evidencia 1')
    st.caption('Todos los importes se muestran en MXN.')

st.markdown('<div class="mt-eyebrow">OPERACIÓN / PANEL EMPRESARIAL</div><div class="mt-hero"><h1>Resumen de operación</h1><p>Entiende cuánto genera tu flota, qué cuesta mantenerla y dónde enfocar la revisión.</p></div>',unsafe_allow_html=True)
st.markdown('<div class="mt-simulation"><b>ESCENARIO SIMULADO · E1</b> &nbsp; Horas, costos e ingresos sintéticos. Catálogo provisional de 21 equipos.</div>',unsafe_allow_html=True)
if len(period)!=2:
    st.info('Elige la fecha de inicio y la fecha de fin para consultar el periodo.')
    st.stop()
mask=d.fecha.between(str(period[0]),str(period[1]))
if category!='Toda la maquinaria':mask &= d.categoria.eq(category)
if equipment:mask &= d.equipo_id.isin(equipment)
if location!='Todas las ubicaciones':mask &= d.ubicacion.eq(location)
if billing!='Todas las modalidades':mask &= d.modalidad_cobro.eq(billing)
selection=d.loc[mask].copy()
if selection.empty:
    st.info('No hay registros para esta combinación. Cambia el periodo o restablece los filtros.')
    st.stop()
k=metrics(selection)
cards=st.columns(4)
metric_specs=[
 ('Ingresos del periodo',money(k['ingresos_mxn']),'MXN acumulados','Suma de ingresos. Cada registro cobra por hora o por tonelada, según su modalidad.'),
 ('Margen directo',f"{k['margen_directo_pct']:.2f}%" if k['margen_directo_pct'] is not None else 'Sin base','Después de operación y mantenimiento','Porcentaje de ingresos que queda al restar costos operativos y mantenimiento. No es utilidad neta contable.'),
 ('Mantenimiento por hora','$'+f"{k['mantenimiento_mxn_h']:.2f}" if k['mantenimiento_mxn_h'] is not None else 'Sin base','MXN por hora trabajada','Costo total de mantenimiento dividido entre las horas trabajadas de la selección.'),
 ('Disponibilidad',f"{k['disponibilidad_pct']:.2f}%" if k['disponibilidad_pct'] is not None else 'Sin base','Tiempo programado sin paro','Horas programadas menos horas de paro, divididas entre horas programadas. No equivale a utilización.')
]
for col,(label,value,note,help_text) in zip(cards,metric_specs):
    with col:
        st.metric(label,value,help=help_text)
        st.markdown('<div class="mt-kpi-note">'+note+'</div>',unsafe_allow_html=True)
st.markdown('<div class="mt-context">'+safe(date_label(period[0]))+' — '+safe(date_label(period[1]))+' &nbsp; · &nbsp; '+str(selection.equipo_id.nunique())+' equipos &nbsp; · &nbsp; '+f'{len(selection):,}'+' registros &nbsp; · &nbsp; Filtros aplicados a todos los indicadores y gráficas</div>',unsafe_allow_html=True)
charts,agg=views(selection)
eq=agg['equipment']
costly=eq.loc[eq.mant_h.idxmax()] if eq.mant_h.notna().any() else None
lowest=eq.loc[eq.margen_pct.idxmin()] if eq.margen_pct.notna().any() else None
overview,equipments,cycles,quality,detail=st.tabs(['Vista general','Equipos y costos','Ciclos de operación','Calidad de datos','Explorar datos'])

with overview:
    st.subheader('Cómo se generan los ingresos')
    left,right=st.columns([1.55,1],gap='medium')
    with left:
        chart(charts[0][0],charts[0][1],'La línea más intensa muestra el promedio de 7 días para facilitar la lectura de la tendencia.','chart0')
    with right:
        chart(charts[1][0],charts[1][1],'Participación por tipo de maquinaria en el periodo elegido.','chart1')
    st.subheader('Tres decisiones para revisar')
    st.caption('Acciones sugeridas para este escenario simulado. Contrástalas con registros reales antes de aplicarlas a la empresa.')
    p=agg['peaks']
    cycle_text=f"{p[0]['periodo_dias']:.0f} y {p[1]['periodo_dias']:.0f} días" if len(p)>1 else 'un periodo más amplio'
    actions=[
      ('01 / MANTENIMIENTO',f'Revisar el equipo {safe(costly.equipo_id)}' if costly is not None else 'Revisar captura de mantenimiento',
       f"Registra el mayor costo: <span class='mt-number'>$"+f"{costly.mant_h:.2f} MXN/h</span>. Conciliar órdenes de trabajo antes de decidir reemplazos." if costly is not None else 'Se requieren horas trabajadas para comparar el costo por hora.'),
      ('02 / CAPACIDAD','Preparar personal e insumos',f"Revisar la programación en ciclos de <span class='mt-number'>{cycle_text}</span>. Los patrones de la simulación deben validarse con partes reales."),
      ('03 / CONTRATOS',f'Revisar la tarifa de {safe(lowest.equipo_id)}' if lowest is not None else 'Revisar ingresos y costos',
       f"Presenta el menor margen directo: <span class='mt-number'>{lowest.margen_pct:.1f}%</span>. Comparar trabajos y contratos equivalentes antes de renegociar." if lowest is not None else 'Se necesitan ingresos distintos de cero para calcular el margen.')
    ]
    for col,(tag,title,text) in zip(st.columns(3),actions):
        with col:
            st.markdown(f'<div class="mt-action"><div class="mt-action-tag">{tag}</div><h4>{title}</h4><p>{text}</p></div>',unsafe_allow_html=True)

with equipments:
    st.subheader('Compara equipos con la misma selección')
    st.caption('Las barras horizontales permiten leer cada equipo sin girar las etiquetas. El color destaca el valor más alto, sin clasificarlo automáticamente como bueno o malo.')
    l,r=st.columns(2,gap='medium')
    with l:chart(charts[2][0],charts[2][1],'Margen después de costos directos y mantenimiento; no incluye impuestos, depreciación ni financiamiento.','chart2')
    with r:chart(charts[3][0],charts[3][1],'Razón de costos totales entre horas totales; un valor alto requiere revisión, no demuestra una falla.','chart3')
    with st.expander('Ver cifras exactas por equipo'):
        display=eq[['equipo_id','ingreso_mxn','margen_pct','horas','mantenimiento','mant_h']].rename(columns={'equipo_id':'Equipo','ingreso_mxn':'Ingresos (MXN)','margen_pct':'Margen directo (%)','horas':'Horas trabajadas','mantenimiento':'Mantenimiento (MXN)','mant_h':'Mantenimiento (MXN/h)'})
        st.dataframe(display,hide_index=True,width='stretch',column_config={c:st.column_config.NumberColumn(format='%.2f') for c in display.columns if c!='Equipo'})

with cycles:
    st.subheader('Cuándo se repite la actividad')
    st.caption('Compara los días de la semana y consulta cada cuántos días aparece un patrón en las horas trabajadas.')
    l,r=st.columns([1,1.15],gap='medium')
    with l:chart(charts[4][0],charts[4][1],'Promedio de horas diarias; evita comparar totales de días que aparecen un número diferente de veces.','chart4')
    with r:
        if charts[5][1] is None:
            with st.container(border=True):
                st.subheader('FFT · amplía el periodo')
                st.info('Selecciona al menos 30 días completos y consecutivos para calcular los ciclos. Las otras cinco gráficas siguen disponibles.')
        else:
            chart(charts[5][0],charts[5][1],'El eje está expresado en días: un pico más alto indica un patrón más marcado.','chart5')
    st.markdown('<div class="mt-notice"><b>Cómo leerlo:</b> un ciclo de 7 días indica repetición semanal; uno de 15 días, repetición cada quince días. No indica que una máquina falle con esa frecuencia.</div>',unsafe_allow_html=True)
    with st.expander('Método FFT y alcance de la simulación'):
        st.write('Se agregan las horas por día, se verifica un calendario sin huecos, se retira la tendencia lineal y se aplica ventana Hann antes de la transformada rápida de Fourier. Frecuencia de muestreo: una observación por día.')
        if agg['peaks']:
            st.dataframe(pd.DataFrame(agg['peaks'][:2]).rename(columns={'periodo_dias':'Periodo (días)','amplitud_h':'Amplitud (h)','frecuencia_ciclos_dia':'Frecuencia (ciclos/día)'}),hide_index=True)
        st.write('Los ciclos de 7 y 15 días fueron introducidos por diseño. Recuperarlos verifica el procedimiento; no descubre estacionalidad real ni diagnostica vibraciones mecánicas.')

with quality:
    a=result['auditoria']
    st.subheader('Datos revisados antes del análisis')
    st.caption('Esta auditoría corresponde a la base completa del escenario, independientemente de los filtros de consulta.')
    st.markdown(f'<div class="mt-flow"><div><strong>{a["filas_raw"]:,}</strong><span>registros recibidos</span></div><div><strong>{sum(a[x] for x in ["nulos","duplicados","negativos","atipicos","formato"]):,}</strong><span>incidencias corregidas</span></div><div><strong>{a["filas_clean"]:,}</strong><span>registros depurados</span></div><div><strong>0</strong><span>errores residuales en los cinco controles</span></div></div>',unsafe_allow_html=True)
    fixes=['Interpolación por equipo y fecha','Eliminación de copias idénticas','Conversión a faltante e interpolación','Límite físico del turno e interpolación','ID en mayúsculas, sin espacios']
    audit=pd.DataFrame({'Error':['Nulos','Duplicados','Negativos','Atípicos','Formato'],'Detectados':[a[x] for x in ['nulos','duplicados','negativos','atipicos','formato']],'Corrección aplicada':fixes,'Residuales':[0]*5})
    st.dataframe(audit,hide_index=True,width='stretch')
    with st.expander('Procedencia y reglas de limpieza'):
        st.write('El catálogo procede del Excel provisional de la empresa. Los 8,820 registros operativos son sintéticos, con semilla 42; no son datos reales de horas, costos o ingresos. Los errores de práctica se sembraron deliberadamente.')
        st.write('Las horas nulas, negativas o fuera del turno se interpolan dentro del mismo equipo y se acotan por horas programadas menos paro. En los extremos se usa el valor válido más cercano. Ingresos y costos variables se reconstruyen únicamente en este escenario simulado. La limpieza no consulta la base anterior a la corrupción.')
    with st.expander('Cómo se calculan los cuatro indicadores'):
        st.write('Ingresos: suma de horas × tarifa o toneladas × tarifa, según modalidad. Un registro utiliza una sola modalidad.')
        st.write('Margen directo (%) = 100 × (ingresos − operación directa − mantenimiento) / ingresos.')
        st.write('Mantenimiento (MXN/h) = suma de mantenimiento / suma de horas trabajadas.')
        st.write('Disponibilidad (%) = 100 × (horas programadas − horas de paro) / horas programadas. No equivale a utilización.')
    with st.expander('Conexión y trazabilidad'):
        st.caption(source)
        st.write('En modo AWS, el tablero lee la fuente privada con credenciales temporales del rol de instancia. Si la fuente falla, informa el error y no la reemplaza por una copia local.')
    st.download_button('Descargar auditoría del escenario',json.dumps(result,ensure_ascii=False,indent=2),'auditoria_minetrac.json','application/json')

with detail:
    st.subheader('Registros de tu selección')
    st.caption(f'{len(selection):,} filas. Usa la búsqueda de la tabla o descarga el detalle para revisarlo.')
    display=selection[['fecha','equipo_id','categoria','ubicacion','horas_trabajadas_h','ingreso_mxn','costo_operativo_mxn','costo_mantenimiento_mxn','margen_directo_mxn']].rename(columns={'fecha':'Fecha','equipo_id':'Equipo','categoria':'Tipo','ubicacion':'Ubicación','horas_trabajadas_h':'Horas','ingreso_mxn':'Ingresos (MXN)','costo_operativo_mxn':'Operación (MXN)','costo_mantenimiento_mxn':'Mantenimiento (MXN)','margen_directo_mxn':'Margen directo (MXN)'})
    st.dataframe(display,hide_index=True,width='stretch',column_config={c:st.column_config.NumberColumn(format='%.2f') for c in display.columns if '(MXN)' in c or c=='Horas'})
    st.download_button('Descargar selección en CSV',selection.to_csv(index=False).encode('utf-8-sig'),'minetrac_seleccion.csv','text/csv',type='primary')
st.caption('MineTrac · E1 Data Startup · Importes en MXN · Resultados del escenario simulado')

