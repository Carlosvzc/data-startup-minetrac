from pathlib import Path
import os, io, json, sys, html
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd
import streamlit as st
from core import resumen, recomendaciones, ciclo_cercano, rango_periodo, filtrar_periodo
from figures import views

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
st.set_page_config(page_title='MineTrac | Control de mantenimiento', page_icon='⛏', layout='wide', initial_sidebar_state='expanded')
st.markdown('<style>' + (HERE / 'styles.css').read_text(encoding='utf-8-sig') + '</style>', unsafe_allow_html=True)
mode = os.environ.get('MINETRAC_STORAGE', 'local')


@st.cache_data(ttl=60)
def load(mode, bucket, region):
    if mode == 's3':
        import boto3
        client = boto3.client('s3', region_name=region)

        def obj(key):
            return client.get_object(Bucket=bucket, Key=key)['Body'].read()
        return (pd.read_csv(io.BytesIO(obj('clean/mantenimiento.csv'))), pd.read_csv(io.BytesIO(obj('clean/inventario.csv'))),
                json.loads(obj('clean/resultados.json')), 'Amazon S3 · ' + bucket + '/clean/')
    if mode != 'local':
        raise ValueError('Modo de almacenamiento desconocido.')
    base = ROOT / 'data/clean'
    return (pd.read_csv(base / 'mantenimiento.csv'), pd.read_csv(base / 'inventario.csv'),
            json.loads((base / 'resultados.json').read_text(encoding='utf-8')), 'Demostración local · data/clean/')


try:
    mant, inv, result, source = load(mode, os.environ.get('MINETRAC_BUCKET', ''), os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
except Exception:
    st.error('No pudimos cargar los datos. Revisa la conexión o solicita al responsable que verifique el acceso a la fuente.')
    if st.button('Volver a intentar'):
        st.cache_data.clear()
        st.rerun()
    st.stop()


def safe(v):
    return html.escape(str(v))


def money(v):
    return '$' + (f'{v / 1e6:,.2f} M' if abs(v) >= 1e6 else f'{v:,.0f}')


def date_label(v):
    months = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
    x = pd.Timestamp(v)
    return f'{x.day:02d} {months[x.month - 1]} {x.year}'


def reset_filters():
    for key in ['period', 'trucks', 'system', 'include_undated']:
        st.session_state.pop(key, None)


def chart(title, fig, caption, key):
    with st.container(border=True):
        st.subheader(title)
        st.caption(caption)
        if fig is None:
            st.info('No hay datos suficientes en esta selección para esta gráfica.')
        else:
            st.plotly_chart(fig, width='stretch', key=key, config={'displayModeBar': False, 'responsive': True})


with st.sidebar:
    st.markdown('<div class="mt-brand"><span>M</span>MineTrac</div><div class="mt-sidebar-sub">CONTROL DE MAQUINARIA</div>', unsafe_allow_html=True)
    st.subheader('Tu selección')
    begin, end = rango_periodo(mant)
    period = st.date_input('Periodo de análisis', value=(begin, end), min_value=begin, max_value=end, key='period', format='DD/MM/YYYY')
    trucks = st.multiselect('Camiones', sorted(mant.camion_id.unique()), default=[], key='trucks', placeholder='Los 7 camiones',
                            help='Déjalo vacío para incluir todos los camiones.')
    system = st.selectbox('Sistema', ['Todos los sistemas'] + sorted(mant.sistema.unique()), key='system')
    include_undated = st.checkbox('Incluir intervenciones sin día conocido', value=True, key='include_undated', help='Las contamos por camión y sistema. No las colocamos en una fecha ni las usamos para ampliar el periodo.')
    st.button('Restablecer filtros', on_click=reset_filters, width='stretch')
    st.divider()
    st.caption('FUENTE DE INFORMACIÓN')
    st.markdown('<span class="mt-badge">' + ('Datos conectados a AWS' if mode == 's3' else 'Demostración local') + '</span>', unsafe_allow_html=True)
    if st.button('Recargar datos', width='stretch'):
        st.cache_data.clear()
        st.rerun()
    st.caption('MineTrac · Evidencia 1')
    st.caption('Todos los importes se muestran en MXN.')

st.markdown('<div class="mt-eyebrow">MANTENIMIENTO / PANEL EMPRESARIAL</div><div class="mt-hero"><h1>Resumen de mantenimiento</h1>'
            '<p>Revisamos qué se repara, cuánto cuesta y qué conviene atender primero.</p></div>', unsafe_allow_html=True)
st.markdown('<div class="mt-aviso"><b>DATOS REALES · E1</b> &nbsp; Catálogo de 21 equipos y bitácora de reparaciones de los 7 camiones de Máquinas Centella. '
            '<b>Pendiente de entrega por la empresa:</b> horas trabajadas, toneladas, tarifas e ingresos. No simulamos ni estimamos esos datos.</div>', unsafe_allow_html=True)
if len(period) != 2:
    st.info('Elige la fecha de inicio y la fecha de fin para consultar el periodo.')
    st.stop()
mm = filtrar_periodo(mant, period[0], period[1], include_undated)
if trucks:
    mm = mm[mm.camion_id.isin(trucks)]
if system != 'Todos los sistemas':
    mm = mm[mm.sistema.eq(system)]
if mm.empty:
    st.info('No hay intervenciones para esta combinación. Cambia el periodo o restablece los filtros.')
    st.stop()

k = resumen(mm)
cards = st.columns(4)
specs = [
    ('Intervenciones', f"{k['intervenciones']:,}", 'Reparaciones y servicios registrados', 'Cada intervención cuenta una vez, aunque toque varios sistemas.'),
    ('Gasto registrado', money(k['gasto_mxn']), 'MXN con monto anotado (parcial)', 'Sumamos los montos anotados. Los faltantes quedan vacíos; el gasto sigue siendo parcial.'),
    ('Costo promedio', '$' + f"{k['promedio_mxn']:,.0f}" if k['promedio_mxn'] is not None else 'Sin base', 'Por intervención con monto', 'Gasto registrado dividido entre las intervenciones que tienen monto.'),
    ('Repeticiones / 100 interv.', f"{k['pct_reincidencia']:.1f}", 'Mismo componente en hasta 30 días', 'Razón: repeticiones por componente y fecha divididas entre intervenciones. No es porcentaje de intervenciones fallidas ni mide fallas confirmadas.'),
]
for col, (label, value, note, help_text) in zip(cards, specs):
    with col:
        st.metric(label, value, help=help_text)
        st.markdown('<div class="mt-kpi-note">' + note + '</div>', unsafe_allow_html=True)
st.markdown('<div class="mt-context">' + safe(date_label(period[0])) + ' - ' + safe(date_label(period[1])) + ' &nbsp; · &nbsp; '
            + str(mm.camion_id.nunique()) + ' camiones &nbsp; · &nbsp; ' + f"{k['con_monto']:,}" + ' intervenciones con monto de ' + f"{k['intervenciones']:,}"
            + ' &nbsp; · &nbsp; Filtramos por periodo, camión y sistema; las intervenciones sin día se incluyen aparte</div>', unsafe_allow_html=True)
st.caption('Conservamos 15 fechas heredadas y 3 con año corregido. El registro que solo indica 2022 sigue en los totales si dejamos marcada la opción de incluirlo. No lo usamos para ampliar el periodo ni lo dibujamos en las gráficas de fechas.')
charts, aux = views(mm)
overview, maintenance, cycles, fleet, quality, detail = st.tabs(
    ['Vista general', 'Mantenimiento y refacciones', 'Ciclos', 'Flota y operación', 'Calidad de datos', 'Explorar datos'])

with overview:
    st.subheader('Qué cuesta y dónde se concentra')
    l, r = st.columns([1.2, 1], gap='medium')
    with l:
        chart(charts[0][0], charts[0][1], 'Gasto por componente, solo con intervenciones que tienen monto. Si una intervención toca varios sistemas, el monto se reparte en partes iguales.', 'c0')
    with r:
        chart(charts[1][0], charts[1][1], 'Intervenciones por camión; en gris, las que no tienen monto anotado.', 'c1')
    st.subheader('Tres recomendaciones para revisar')
    st.caption('Calculamos estas recomendaciones con la selección actual. Solo usamos los montos anotados.')
    for col, (tag, title, text) in zip(st.columns(3), recomendaciones(mm, aux)):
        with col:
            st.markdown(f'<div class="mt-action"><div class="mt-action-tag">{safe(tag)}</div><h4>{safe(title)}</h4><p>{safe(text)}</p></div>', unsafe_allow_html=True)

with maintenance:
    st.subheader('Qué se ha reparado y cuándo')
    st.caption('Revisamos la bitácora de los 7 camiones. Sumamos los montos anotados y dejamos vacíos los que faltan.')
    l, r = st.columns(2, gap='medium')
    with l:
        chart(charts[2][0], charts[2][1], 'Ubicamos solo las intervenciones con día conocido. El tamaño del punto indica su monto cuando está registrado.', 'c2')
    with r:
        chart(charts[3][0], charts[3][1], 'Contamos las intervenciones con día conocido de cada mes.', 'c3')
    chart(charts[4][0], charts[4][1], 'Días entre trabajos registrados del mismo componente. Solo intervalos mayores de 30 días y componentes con al menos tres intervalos; Nos falta confirmar los reemplazos y medir las horas para hablar de vida útil.', 'c4')
    st.markdown('<div class="mt-notice"><b>Pendiente de capturar:</b> tipo de pieza (original o genérica), proveedor real y lectura del horómetro al cambio. '
                'Con esos tres datos el tablero calculará el costo por hora útil de cada opción, como pide el cliente.</div>', unsafe_allow_html=True)
    if len(aux['componentes']):
        with st.expander('Gasto por componente (cifras exactas)'):
            comp = aux['componentes'].rename(columns={'componente': 'Componente', 'costo_mxn': 'Gasto registrado (MXN)'})
            st.dataframe(comp, hide_index=True, width='stretch', column_config={'Gasto registrado (MXN)': st.column_config.NumberColumn(format='%.0f')})

with cycles:
    st.subheader('Cuándo se repite la actividad')
    st.caption('Análisis de Fourier (FFT) sobre las intervenciones registradas por día, desde el 1 de abril de 2024.')
    if charts[5][1] is None:
        with st.container(border=True):
            st.subheader('FFT · amplía el periodo')
            st.info('Selecciona al menos 30 días completos y consecutivos para calcular los ciclos. Las otras gráficas siguen disponibles.')
    else:
        chart(charts[5][0], charts[5][1], 'El eje está expresado en días: un pico más alto indica un patrón más marcado.', 'c5')
        p7, p15 = ciclo_cercano(aux['spectrum'], 7), ciclo_cercano(aux['spectrum'], 15)
        if p7 and p15:
            st.markdown(f'<div class="mt-notice"><b>Ciclo de 7 días:</b> su fuerza es {p7["veces_mediana"]:.1f} veces la mediana del espectro. '
                        f'<b>Ciclo de 15 días:</b> {p15["veces_mediana"]:.1f} veces la mediana, es decir, '
                        + ('no supera el umbral descriptivo de 2.5 veces la mediana (no es prueba estadística).' if p15['veces_mediana'] < 2.5 else 'supera el umbral descriptivo de 2.5 veces la mediana (no es prueba estadística).') + '</div>', unsafe_allow_html=True)
    with st.expander('Método FFT y límites'):
        st.write('Contamos las intervenciones registradas por día (con ceros en los días sin registro), retiramos la tendencia lineal y aplicamos una ventana Hann antes de la transformada rápida de Fourier.')
        st.write('Revisamos cuándo se registraron o atendieron las reparaciones. No tenemos una fecha de falla para cada intervención. Con 257 intervenciones en unos 900 días, la señal es débil; sirve para ver el ritmo semanal del taller, no para predecir fallas.')
        if aux['peaks']:
            st.dataframe(pd.DataFrame(aux['peaks'][:3]).rename(columns={'periodo_dias': 'Periodo (días)', 'amplitud': 'Amplitud', 'frecuencia_ciclos_dia': 'Frecuencia (ciclos/día)'}), hide_index=True)

with fleet:
    st.subheader('Catálogo de equipos')
    st.caption('21 equipos de Máquinas Centella según el catálogo entregado (pendiente de validación por la empresa).')
    c = inv.groupby('categoria').size().reset_index(name='Equipos').rename(columns={'categoria': 'Tipo'})
    st.dataframe(c, hide_index=True, width='stretch')
    st.dataframe(inv[['equipo_id', 'categoria', 'modelo']].rename(columns={'equipo_id': 'Equipo', 'categoria': 'Tipo', 'modelo': 'Modelo'}), hide_index=True, width='stretch')
    st.markdown('<div class="mt-notice"><b>Operación y balance financiero: pendiente.</b> Máquinas Centella nos informó por carta del 25 de octubre de 2026 que está '
                'recopilando, revisando y consolidando la información en un archivo de Excel con sus departamentos. Cuando llegue (horas trabajadas por turno, toneladas, tarifas, '
                'horómetro), podremos agregar los ingresos, el margen operativo neto por equipo y el indicador de tarifas para contratos. La carta se entregó por separado en Classroom.</div>', unsafe_allow_html=True)

with quality:
    b = result['auditoria_bitacora']
    f = b['formato']
    st.subheader('Datos revisados antes del análisis')
    st.caption('Revisamos la bitácora completa para esta auditoría. Los filtros no cambian sus conteos.')
    st.markdown(f'<div class="mt-flow"><div><strong>{b["intervenciones_leidas"]:,}</strong><span>intervenciones leídas</span></div><div><strong>{b["registros_clean"]:,}</strong><span>registros por sistema</span></div><div><strong>{b["formato_total"] + b["nulos_fecha_imputados"]:,}</strong><span>fechas y formatos corregidos</span></div><div><strong>{b["nulos_costo"]:,}</strong><span>sin monto (los dejamos vacíos)</span></div></div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame({
        'Error': ['Nulos', 'Duplicados', 'Negativos', 'Atípicos', 'Formato'],
        'Detectados': [b['nulos_costo'] + b['nulos_fecha_imputados'], b['duplicados'], b['negativos'], b['atipicos'], b['formato_total']],
        'Tratamiento': [f"{b['nulos_costo']} intervenciones sin monto se conservan sin monto; {b['nulos_fecha_imputados']} filas sin fecha heredan la de la fila anterior",
                        'Control de duplicación dentro de la misma fila de origen: ninguno. No descarta registros duplicados en filas distintas.', 'Ningún monto negativo',
                        f"1 monto sobre ${b['limite_atipico_mxn']:,.0f} (ajuste completo de motor) se conserva como monto anotado; pendiente de validar con comprobante",
                        f"{f['fechas_texto_interpretadas']} fechas escritas a mano interpretadas, {f['fechas_anio_corregido'] + f['fechas_solo_anio']} años corregidos o aproximados, {f['costo_extraido_de_texto']} montos tomados del texto, {f['texto_en_columna_costo']} texto en la columna de costo y {f['costo_en_columna_servicio']} monto en la columna de servicio"],
        'Residuales': [b['nulos_costo'], 0, 0, b['atipicos'], 0]}), hide_index=True, width='stretch')
    with st.expander('Procedencia, privacidad y reglas de limpieza'):
        st.write('El catálogo y la bitácora proceden de los Excel de Máquinas Centella. No hay datos simulados en este tablero.')
        st.write('Revisamos las fechas según el orden de cada hoja. Repartimos el monto entre los sistemas de cada intervención y clasificamos las piezas con palabras clave. Nos falta validar con la empresa el componente y la condición que interpretamos del texto.')
        st.write('Privacidad: no se muestra texto libre ni nombres. En este procesamiento no se identificaron proveedores: la columna conserva sin_dato; no completamos códigos ni identidades.')
        st.write('Fechas derivadas, pendientes de validar: 15 intervenciones heredaron fecha, 3 cambiaron de año por orden de la hoja y 1 solo tenía el año 2022. Conservamos 01/01 en el CSV como referencia técnica del año 2022. Contamos esa intervención, pero la excluimos del periodo y de las gráficas de fechas. La columna Calidad de fecha permite distinguirlas. La FFT excluye fechas anteriores a abril de 2024; depende de una captura completa, que aún no está confirmada.')
        st.write('El reparto igual del monto entre sistemas es una asignación analítica, no un desglose facturado. Días entre trabajos no equivale a vida útil de una pieza ni confirma que se reemplazó. Un monto atípico se conserva por estar anotado: no se verificó con factura.')
    with st.expander('Cómo se calculan los cuatro indicadores'):
        st.write('Intervenciones: eventos distintos de la bitácora. Gasto registrado: suma de montos anotados. Costo promedio: gasto registrado ÷ intervenciones con monto.')
        st.write('Repeticiones por 100 intervenciones = 100 × repeticiones por camión, componente y fecha en hasta 30 días ÷ intervenciones. Es una razón entre unidades distintas, no el porcentaje de reparaciones fallidas.')
    with st.expander('Conexión y trazabilidad'):
        st.caption(source)
        st.write('En modo AWS, el tablero lee la fuente privada con credenciales temporales del rol de instancia. Si la fuente falla, informa el error y no la reemplaza por una copia local.')
    st.download_button('Descargar auditoría', json.dumps(b, ensure_ascii=False, indent=2), 'auditoria_minetrac.json', 'application/json')

with detail:
    st.subheader('Intervenciones de camiones en tu selección')
    st.caption(f'{len(mm):,} filas (una por intervención y sistema). Sin texto libre; proveedores anonimizados.')
    cols = ['fecha', 'fecha_calidad', 'camion_id', 'sistema', 'componente', 'condicion_pieza', 'proveedor_codigo', 'costo_mxn', 'costo_origen', 'vida_util_dias', 'reincidencia_30d']
    dm = mm[cols].rename(columns={'fecha': 'Fecha analítica', 'fecha_calidad': 'Calidad de fecha', 'camion_id': 'Camión', 'sistema': 'Sistema', 'componente': 'Componente', 'condicion_pieza': 'Condición',
                                  'proveedor_codigo': 'Proveedor', 'costo_mxn': 'Monto (MXN)', 'costo_origen': 'Origen del monto', 'vida_util_dias': 'Días desde cambio anterior (>30)',
                                  'reincidencia_30d': 'Repite en 30 días'})
    dm.loc[mm.fecha_calidad.eq('solo_anio').to_numpy(), 'Fecha analítica'] = '2022 (día pendiente)'
    st.dataframe(dm, hide_index=True, width='stretch', column_config={'Monto (MXN)': st.column_config.NumberColumn(format='%.0f')})
    st.download_button('Descargar mantenimiento en CSV', mm.to_csv(index=False).encode('utf-8-sig'), 'minetrac_mantenimiento.csv', 'text/csv', type='primary')
st.caption('MineTrac · E1 Data Startup · Importes en MXN · Información real de Máquinas Centella; operación pendiente')
