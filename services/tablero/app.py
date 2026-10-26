
from pathlib import Path
import os,io,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pandas as pd
import streamlit as st
from core import metrics
from figures import views
ROOT=Path(__file__).resolve().parents[2]
st.set_page_config(page_title='MineTrac | E1',page_icon='⛏',layout='wide')
st.markdown('<style>.block-container{padding-top:1.8rem} [data-testid="stMetric"]{background:#132833;border:1px solid #244652;padding:18px;border-radius:10px} h1{color:#42dac7}</style>',unsafe_allow_html=True)
st.title('MineTrac')
st.caption('SALUD OPERATIVA · E1 DATA STARTUP')
st.warning('ESCENARIO SIMULADO · Los 21 ID proceden del inventario provisional. Horas, costos, ingresos y ciclos son sintéticos (semilla 42). No representan resultados reales de la empresa.')
mode=os.environ.get('MINETRAC_STORAGE','local')
@st.cache_data(ttl=60)
def load(mode,bucket,region):
    if mode=='s3':
        import boto3
        client=boto3.client('s3',region_name=region)
        def obj(key):
            return client.get_object(Bucket=bucket,Key=key)['Body'].read()
        d=pd.read_csv(io.BytesIO(obj('clean/operacion.csv')))
        result=json.loads(obj('clean/resultados.json'))
        return d,result,'Amazon S3 · '+bucket+'/clean/operacion.csv'
    if mode!='local':raise ValueError('Modo de almacenamiento desconocido.')
    return pd.read_csv(ROOT/'data/clean/operacion.csv'),json.loads((ROOT/'data/clean/resultados.json').read_text(encoding='utf-8')),'Demostración local · sin conexión AWS'
try:
    d,result,source=load(mode,os.environ.get('MINETRAC_BUCKET',''),os.environ.get('AWS_DEFAULT_REGION','us-east-1'))
except Exception:
    st.error('No se pudo leer la fuente configurada. Verifica la sesión AWS, permisos y nombre del bucket. No se sustituyeron los datos cloud por archivos locales.')
    st.stop()
st.sidebar.header('Filtros')
st.sidebar.caption(source)
categories=st.sidebar.multiselect('Categorías',sorted(d.categoria.unique()),default=sorted(d.categoria.unique()))
options=sorted(d.loc[d.categoria.isin(categories),'equipo_id'].unique())
equipment=st.sidebar.multiselect('Equipos',options,default=options)
locations=st.sidebar.multiselect('Ubicación',sorted(d.ubicacion.unique()),default=sorted(d.ubicacion.unique()))
billing=st.sidebar.multiselect('Cobro',sorted(d.modalidad_cobro.unique()),default=sorted(d.modalidad_cobro.unique()))
begin,end=pd.to_datetime(d.fecha.min()).date(),pd.to_datetime(d.fecha.max()).date()
period=st.sidebar.date_input('Periodo',value=(begin,end),min_value=begin,max_value=end)
if st.sidebar.button('Actualizar fuente'):
    st.cache_data.clear();st.rerun()
if len(period)!=2:st.info('Selecciona inicio y fin.');st.stop()
selection=d[d.categoria.isin(categories)&d.equipo_id.isin(equipment)&d.ubicacion.isin(locations)&d.modalidad_cobro.isin(billing)&d.fecha.between(str(period[0]),str(period[1]))]
if selection.empty:st.info('No hay registros con estos filtros.');st.stop()
k=metrics(selection)
cards=st.columns(4)
cards[0].metric('Ingresos',f"$"+f"{k['ingresos_mxn']/1e6:.2f} M")
cards[1].metric('Margen directo',f"{k['margen_directo_pct']:.2f}%")
cards[2].metric('Mantenimiento / hora',f"$"+f"{k['mantenimiento_mxn_h']:.2f}")
cards[3].metric('Disponibilidad',f"{k['disponibilidad_pct']:.2f}%")
st.caption(f"{len(selection):,} registros · {selection.equipo_id.nunique()} equipos · {period[0]} a {period[1]} · Moneda MXN. Margen después de operación directa y mantenimiento; no es utilidad neta.")
tab,quality,detail=st.tabs(['Historia del negocio','Limpieza y método','Datos y descargas'])
with tab:
    if selection.fecha.nunique()<30:
        st.info('Para mostrar las seis gráficas y la FFT selecciona al menos 30 días consecutivos.')
    else:
        charts,agg=views(selection)
        for i in range(0,6,2):
            cols=st.columns(2)
            for j in range(2):
                title,fig=charts[i+j]
                with cols[j]:
                    st.subheader(title)
                    st.plotly_chart(fig,width='stretch',key='chart'+str(i+j))
        st.caption('FFT sobre horas diarias, frecuencia de muestreo 1/día, tendencia lineal retirada y ventana Hann. Los ciclos de 7 y 15 días fueron introducidos por diseño; recuperarlos valida el procedimiento, no descubre estacionalidad real.')
        eq=agg['equipment'];costly=eq.loc[eq.mant_h.idxmax()]
        st.subheader('Tres acciones para el escenario')
        st.write(f"1. Programar la revisión preventiva de {costly.equipo_id}: tiene el mayor costo de mantenimiento por hora de esta selección ($"+f"{costly.mant_h:.2f}). Validar órdenes de trabajo antes de decidir reemplazos.")
        st.write('2. Preparar disponibilidad de personal e insumos para los ciclos de 7 y 15 días. Contrastar el patrón con partes reales antes de cambiar la programación de la empresa.')
        lowest=eq.loc[eq.margen_pct.idxmin()]
        st.write(f"3. Revisar tarifa y estructura de costos de {lowest.equipo_id}, con margen directo de {lowest.margen_pct:.1f}%. Comparar contratos equivalentes antes de renegociar.")
with quality:
    st.subheader('Cinco errores detectados y corregidos')
    a=result['auditoria']
    st.dataframe(pd.DataFrame({'Tipo':['Nulos','Duplicados','Negativos','Atípicos','Formato'],'Detectados':[a[x] for x in ['nulos','duplicados','negativos','atipicos','formato']],'Residuales':[0]*5}),hide_index=True)
    st.write('Nulos y horas inválidas: interpolación cronológica por equipo, acotada por horas programadas menos paro. Duplicados idénticos: una observación por equipo y día. Formato: ID en mayúsculas sin espacios.')
    st.write('Ingresos, toneladas y costos variables se recalculan por las horas corregidas únicamente en este escenario simulado. La limpieza no consulta la base previa a la corrupción.')
    st.write('Disponibilidad = 100 × (programadas − paro) / programadas. Costo de mantenimiento por hora = suma de mantenimiento / suma de horas. Margen = 100 × (ingresos − operación directa − mantenimiento) / ingresos.')
    st.write('El calendario sintético programa 12 horas por equipo y día. No se infiere disponibilidad a partir de horas trabajadas. No se suman dos modalidades de cobro sobre la misma fila.')
with detail:
    st.dataframe(selection,hide_index=True)
    st.download_button('Descargar selección limpia',selection.to_csv(index=False).encode('utf-8-sig'),'minetrac_clean.csv','text/csv')
    st.download_button('Descargar resultados y auditoría',json.dumps(result,ensure_ascii=False,indent=2),'resultados.json','application/json')


