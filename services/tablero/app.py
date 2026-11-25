from pathlib import Path
import os, io, json, sys, html
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd
import streamlit as st
from core import resumen, recomendaciones, ciclo_cercano, rango_periodo, filtrar_periodo
from figures import views
import libreta as lb
import alertas as alr
import correo as mail
import reporte as rpt
import resumen_envio as envio

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
st.set_page_config(page_title='MineTrac | Control de mantenimiento', page_icon='⛏', layout='wide', initial_sidebar_state='expanded')
st.markdown('<style>' + (HERE / 'fonts.css').read_text(encoding='utf-8') + (HERE / 'styles.css').read_text(encoding='utf-8-sig') + '</style>', unsafe_allow_html=True)
mode = os.environ.get('MINETRAC_STORAGE', 'local')
# Alcance actual: solo camiones. Con MINETRAC_ALCANCE=flota se muestra también la libreta de los demás equipos.
SHOW_LIB = os.environ.get('MINETRAC_ALCANCE', 'camiones') == 'flota'


@st.cache_data(ttl=60)
def load(mode, bucket, region):
    if mode == 's3':
        import boto3
        client = boto3.client('s3', region_name=region)

        def obj(key):
            return client.get_object(Bucket=bucket, Key=key)['Body'].read()
        try:
            lib = pd.read_csv(io.BytesIO(obj('clean/libreta_eventos.csv')))
        except Exception:   # la libreta es opcional: si aún no se sube, el resto del tablero sigue funcionando
            lib = pd.DataFrame()
        return (pd.read_csv(io.BytesIO(obj('clean/mantenimiento.csv'))), pd.read_csv(io.BytesIO(obj('clean/inventario.csv'))),
                json.loads(obj('clean/resultados.json')), 'Amazon S3 · ' + bucket + '/clean/', lib)
    if mode != 'local':
        raise ValueError('Modo de almacenamiento desconocido.')
    base = ROOT / 'data/clean'
    lib = pd.read_csv(base / 'libreta_eventos.csv') if (base / 'libreta_eventos.csv').exists() else pd.DataFrame()
    return (pd.read_csv(base / 'mantenimiento.csv'), pd.read_csv(base / 'inventario.csv'),
            json.loads((base / 'resultados.json').read_text(encoding='utf-8')), 'Demostración local · data/clean/', lib)


try:
    mant, inv, result, source, libreta = load(mode, os.environ.get('MINETRAC_BUCKET', ''), os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
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
    st.markdown('<div class="mt-brand"><span>⛏</span>MineTrac</div><div class="mt-sidebar-sub">CONTROL DE MAQUINARIA</div>', unsafe_allow_html=True)
    st.subheader('Filtros')
    st.caption('Elige qué quieres ver. Todo el tablero se actualiza al instante.')
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

_corte = alr.fecha_corte(mant)
_alertas = alr.calcular(mant, _corte)
_ra = alr.resumen_alertas(_alertas)
st.markdown('<div class="mt-hero"><div class="mt-hero-main"><div class="mt-eyebrow">MINETRAC · MÁQUINAS CENTELLA</div><h1>Mantenimiento de la flota</h1>'
            '<p>Qué se repara, cuánto cuesta y qué conviene atender primero.</p></div>'
            '<div class="mt-hero-side"><div class="mt-hero-chip"><b>' + str(_ra['Alta']) + '</b><span>alertas altas</span></div>'
            '<div class="mt-hero-chip"><b>' + str(_ra['Media']) + '</b><span>alertas medias</span></div>'
            '<div class="mt-hero-chip soft"><b>' + safe(date_label(_corte)) + '</b><span>datos hasta</span></div></div></div>', unsafe_allow_html=True)
st.markdown('<div class="mt-aviso"><b>Datos reales de Máquinas Centella.</b> Bitácora de reparaciones de los 7 camiones. '
            'Por ahora el alcance son los camiones; el resto de la flota se agrega después. <b>Las horas trabajadas, toneladas, tarifas e ingresos</b> la empresa los lleva a mano y aún no están capturados; no los simulamos ni los estimamos.</div>', unsafe_allow_html=True)
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
charts, aux = views(mm)


def lectura(k, aux):
    partes = [f"En este periodo hay <b>{k['intervenciones']:,} intervenciones</b> en {mm.camion_id.nunique()} camiones y <b>{money(k['gasto_mxn'])}</b> con monto anotado."]
    comp = aux['componentes']
    if len(comp):
        partes.append(f"El gasto se concentra en <b>{safe(comp.iloc[0].componente)}</b> ({100 * comp.iloc[0].costo_mxn / comp.costo_mxn.sum():.0f}% del total registrado).")
    por = aux['por_camion']
    if len(por):
        partes.append(f"El camión con más intervenciones es <b>{safe(por.index[-1])}</b> ({int(por.iloc[-1].total)}).")
    return ' '.join(partes)


st.markdown('<div class="mt-lectura">' + lectura(k, aux) + '</div>', unsafe_allow_html=True)
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
st.markdown('<div class="mt-context"><span>' + safe(date_label(period[0])) + ' a ' + safe(date_label(period[1])) + '</span><span>'
            + str(mm.camion_id.nunique()) + ' camiones</span><span>' + safe(system) + '</span><span>'
            + f"{k['con_monto']:,}" + ' de ' + f"{k['intervenciones']:,}" + ' con monto anotado</span></div>', unsafe_allow_html=True)

_nombres = ['Vista general', 'Alertas y reportes', 'Mantenimiento y refacciones', 'Ciclos', 'Flota y operación'] + (['Libreta de taller'] if SHOW_LIB else []) + ['Predicción', 'Calidad de datos', 'Explorar datos']
_tabs = st.tabs(_nombres)
overview, alerts_tab, maintenance, cycles, fleet = _tabs[:5]
taller = _tabs[5] if SHOW_LIB else None
pred, quality, detail = _tabs[-3:]

with overview:
    st.subheader('Qué cuesta y dónde se concentra')
    l, r = st.columns([1.2, 1], gap='medium')
    with l:
        chart(charts[0][0], charts[0][1], 'Gasto por componente, solo con intervenciones que tienen monto. Si una intervención toca varios sistemas, el monto se reparte en partes iguales.', 'c0')
    with r:
        chart(charts[1][0], charts[1][1], 'Intervenciones por camión; en gris, las que no tienen monto anotado.', 'c1')
    st.subheader('Tres recomendaciones para revisar')
    st.caption('Calculamos estas recomendaciones con la selección actual. Solo usamos los montos anotados.')
    for n, (col, (tag, title, text)) in enumerate(zip(st.columns(3), recomendaciones(mm, aux)), 1):
        with col:
            etiqueta = safe(tag.split('/')[-1].strip().capitalize())
            st.markdown(f'<div class="mt-action"><div class="mt-num">{n}</div><div><div class="mt-action-tag">{etiqueta}</div><h4>{safe(title)}</h4><p>{safe(text)}</p></div></div>', unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def pdf_seleccion(mm_, periodo, filtros):
    """Reporte de la selección actual; se guarda en caché para que descargar no regenere el PDF en cada clic."""
    import e2 as _e2
    r2_ = _e2.cargar(mode, os.environ.get('MINETRAC_BUCKET', ''), os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'), ROOT)
    hist = pred_ = None
    if r2_ is not None:
        hist = pd.Series(r2_['serie']['valores'], index=pd.to_datetime(r2_['serie']['fechas'])); pred_ = _e2.pronostico(r2_, 4)
    return rpt.generar_pdf(mm_, _alertas, periodo, filtros, _corte, hist, pred_, lectura(resumen(mm_), views(mm_)[1]))


with alerts_tab:
    st.subheader('Qué atender primero')
    st.caption(f'Alertas calculadas con la bitácora de los camiones, a la fecha de corte {date_label(_corte)} (último dato registrado). '
               'Usan días y repeticiones; todavía no hay horas trabajadas para alertar por horómetro.')
    ca = st.columns(3)
    for col, (sev, nota) in zip(ca, [('Alta', 'Atender pronto'), ('Media', 'Revisar esta semana'), ('Info', 'Confirmar datos')]):
        with col:
            st.markdown(f'<div class="mt-sev mt-sev-{sev.lower()}"><b>{_ra[sev]}</b><span>{sev}</span><i>{nota}</i></div>', unsafe_allow_html=True)
    fa, fb = st.columns([1, 2])
    sev_sel = fa.multiselect('Nivel', ['Alta', 'Media', 'Info'], default=['Alta', 'Media'], key='alert_sev')
    cam_sel = fb.multiselect('Camiones', sorted(mant.camion_id.unique()), default=[], key='alert_trucks', placeholder='Los 7 camiones')
    vista = _alertas[_alertas.severidad.isin(sev_sel)]
    if cam_sel:
        vista = vista[vista.camion_id.isin(cam_sel)]
    if vista.empty:
        st.info('No hay alertas con esta selección.')
    cols_a = st.columns(2, gap='medium')
    for n_a, (_, a) in enumerate(vista.iterrows()):
        with cols_a[n_a % 2]:
            st.markdown(f'<div class="mt-alert mt-alert-{a.severidad.lower()}"><div class="mt-alert-top"><span class="mt-pill">{safe(a.severidad)}</span><b>{safe(a.camion_id)}</b>'
                        f'<em>{safe(a.tipo)}</em></div><p>{safe(a.detalle)}</p><small>Qué hacer: {safe(a.accion)}</small></div>', unsafe_allow_html=True)
    st.markdown('<div class="mt-notice"><b>Cómo leerlas.</b> Si una alerta de servicio parece exagerada, puede faltar capturar ese servicio en la bitácora: '
                'confírmalo con el taller antes de actuar. Los umbrales (120 y 240 días sin servicio, 3 intervenciones del mismo sistema en 90 días) son un punto de partida que la empresa puede ajustar.</div>', unsafe_allow_html=True)

    st.subheader('Reporte en PDF')
    st.caption('Incluye los indicadores, las gráficas y las alertas de la selección que tienes en los filtros, más la predicción de las próximas semanas.')
    filtros_txt = f"{mm.camion_id.nunique()} camiones · {system}"
    periodo_txt = f'{period[0]:%d/%m/%Y} a {period[1]:%d/%m/%Y}'
    st.download_button('Descargar reporte PDF', pdf_seleccion(mm, periodo_txt, filtros_txt), f'reporte_minetrac_{_corte:%Y%m%d}.pdf', 'application/pdf', type='primary', key='dl_pdf')

    st.subheader('Enviar por correo')
    st.caption('Manda el resumen de toda la flota (alertas y PDF adjunto) a quien lo necesite. El envío es siempre manual: solo se manda cuando confirmas.')
    listo, info = mail.configurado()
    if not listo:
        st.markdown('<div class="mt-notice"><b>El correo todavía no está configurado en este servidor.</b> ' + safe(info) +
                    ' Se configura con variables de entorno (ver README). Mientras tanto puedes descargar el PDF y adjuntarlo tú.</div>', unsafe_allow_html=True)
    destino = st.text_input('Correos de destino', key='mail_to', placeholder='nombre@empresa.com, otro@empresa.com', help='Separa varios con coma.')
    confirmo = st.checkbox('Confirmo que quiero enviar este resumen a esas personas.', key='mail_ok')
    if st.button('Enviar resumen', disabled=not listo, key='mail_btn'):
        dest = mail.separar_destinatarios(destino)
        ok_, malos = mail.validos(dest)
        permitidos = [d.strip().lower() for d in os.environ.get('MINETRAC_DOMINIOS_PERMITIDOS', '').split(',') if d.strip()]
        if not ok_ or malos:
            st.error('Revisa los correos: ' + (', '.join(malos) if malos else 'escribe al menos uno.'))
        elif len(ok_) > 5:
            st.error('Máximo 5 destinatarios por envío.')
        elif permitidos and any(c.split('@')[1] not in permitidos for c in ok_):
            st.error('Solo se puede enviar a los dominios autorizados: ' + ', '.join(permitidos) + '.')
        elif not confirmo:
            st.warning('Marca la casilla de confirmación para enviar.')
        elif st.session_state.get('mail_n', 0) >= 5:
            st.error('Alcanzaste el límite de 5 envíos en esta sesión.')
        else:
            try:
                with st.spinner('Preparando y enviando…'):
                    asunto, html_c, texto, pdf_b, _ = envio.paquete(mant, ROOT)
                    mail.enviar(mail.construir_mensaje(ok_, asunto, html_c, texto, pdf_b, f'reporte_minetrac_{_corte:%Y%m%d}.pdf'))
                st.session_state['mail_n'] = st.session_state.get('mail_n', 0) + 1
                st.success(f'Enviado a {len(ok_)} destinatario(s).')
            except Exception:
                st.error('No pudimos enviar el correo. Revisa la configuración del servidor de correo e inténtalo de nuevo.')


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
    st.subheader('Camiones del catálogo')
    st.caption('Los 7 camiones de Máquinas Centella según el catálogo entregado (pendiente de validación por la empresa). El catálogo completo trae 21 equipos; el resto de la flota se agrega después.')
    inv_v = inv if SHOW_LIB else inv[inv.categoria.str.lower().str.contains('cami')]
    c = inv_v.groupby('categoria').size().reset_index(name='Equipos').rename(columns={'categoria': 'Tipo'})
    st.dataframe(c, hide_index=True, width='stretch')
    cols = ['equipo_id', 'categoria', 'modelo'] + (['estado'] if 'estado' in inv_v.columns else [])
    st.dataframe(inv_v[cols].rename(columns={'equipo_id': 'Equipo', 'categoria': 'Tipo', 'modelo': 'Modelo', 'estado': 'Estado'}), hide_index=True, width='stretch')
    st.markdown('<div class="mt-notice"><b>Operación y balance financiero: queda para una etapa posterior.</b> La empresa lleva a mano las horas trabajadas, las toneladas y las tarifas, '
                'y todavía no las tiene capturadas. Cuando existan (horas trabajadas por turno, toneladas, tarifas, horómetro), podremos agregar los ingresos, el margen operativo neto por equipo y el indicador de tarifas para contratos.</div>', unsafe_allow_html=True)

if SHOW_LIB:
    with taller:
        st.subheader('Libreta de taller: equipos que no son camiones')
        st.caption('Transcribimos 35 fotos de la libreta manuscrita de la empresa (abril de 2024 a octubre de 2026). Es información real, sin validar todavía: '
                   'las fechas y los montos salen de letra a mano y los marcamos cuando son dudosos. Esta pestaña no usa el filtro de camiones.')
        if libreta.empty:
            st.info('Todavía no hay datos de la libreta en esta fuente. Súbelos a clean/libreta_eventos.csv para verlos aquí.')
        else:
            eq_sel = st.multiselect('Equipos de la libreta', sorted(libreta.equipo_id.unique()), default=[], key='lib_equipos',
                                    placeholder='Los 14 equipos', help='Déjalo vacío para incluir todos.')
            lib = lb.filtrar(libreta, eq_sel)
            kl = lb.kpis(lib)
            cl = st.columns(4)
            lspecs = [('Anotaciones', f"{kl['anotaciones']:,}", f"{kl['equipos']} equipos · {kl['servicios']} servicios preventivos"),
                      ('Servicios con intervalo', f"{kl['con_intervalo']:,}", 'Servicios de 250, 500, 750 o 1,000 horas'),
                      ('Gasto con monto único', money(kl['gasto_mxn']), f"MXN · {kl['con_monto']} anotaciones con una sola cifra (parcial)"),
                      ('Repeticiones / 100 anot.', f"{kl['rep_100']:.1f}", 'Mismo equipo y sistema en hasta 30 días, sin servicios')]
            for col, (label, value, note) in zip(cl, lspecs):
                with col:
                    st.metric(label, value)
                    st.markdown('<div class="mt-kpi-note">' + note + '</div>', unsafe_allow_html=True)
            lf = lb.graficas(lib)
            l, r = st.columns(2, gap='medium')
            with l:
                chart('Qué equipos concentran más anotaciones', lf[0], 'Anotaciones por equipo; en negro, los servicios preventivos.', 'l0')
            with r:
                chart('Qué sistemas fallan más', lf[1], 'Anotaciones por sistema, sin servicios preventivos. Clasificamos por palabras clave; hay anotaciones sin clasificar.', 'l1')
            l, r = st.columns(2, gap='medium')
            with l:
                chart('Cuánto se anota cada mes', lf[2], 'Anotaciones con fecha desde abril de 2024.', 'l2')
            with r:
                chart('Qué servicios preventivos se registran', lf[3], 'Servicios que indican su intervalo en horas de operación.', 'l3')
            piezas = lib[lib.canibalizacion]
            if len(piezas):
                with st.expander(f'Piezas o controles pasados de un equipo a otro ({len(piezas)} anotaciones)'):
                    st.caption('Detectamos anotaciones que mencionan otro equipo al mover una pieza. Es una lectura automática: puede incluir falsos positivos.')
                    st.dataframe(piezas[['equipo_id', 'fecha', 'equipos_mencionados']].rename(columns={'equipo_id': 'Equipo', 'fecha': 'Fecha', 'equipos_mencionados': 'Equipos mencionados'}), hide_index=True, width='stretch')
            st.markdown('<div class="mt-notice"><b>Límites de la libreta:</b> casi nunca anota la fecha en que el equipo dejó de trabajar ni cuándo regresó, '
                        'así que no sirve todavía para medir horas fuera de servicio. Solo una anotación trae lectura de horómetro. Las anotaciones con varias cifras '
                        '(cotizaciones o desgloses) no entran al gasto para no sumar alternativas. T1 y T2 aparecen en la libreta pero no en el catálogo de 21 equipos.</div>', unsafe_allow_html=True)
            st.download_button('Descargar libreta estructurada (CSV)', lib.to_csv(index=False).encode('utf-8-sig'), 'minetrac_libreta.csv', 'text/csv')

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

with pred:
    import e2
    st.subheader('Cuántas fallas esperar en las próximas semanas')
    st.caption('Serie semanal de intervenciones de los 7 camiones (abril de 2024 a octubre de 2026). Modelo: regresión lineal calculada a mano con NumPy '
               '(tendencia e intervenciones de la semana anterior). Es una referencia para planear el taller, no una promesa. Esta pestaña usa toda la bitácora y no los filtros de arriba.')
    r2 = e2.cargar(mode, os.environ.get('MINETRAC_BUCKET', ''), os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'), ROOT)
    if r2 is None:
        st.info('Todavía no hay resultados del análisis en esta fuente. Ejecuta scripts/pipeline_e2.py para generarlos.')
    else:
        c1, c2 = st.columns(2)
        horizonte = c1.slider('Semanas a predecir', 1, 12, 8, key='horizonte')
        suav = c2.select_slider('Suavizado de la serie (semanas)', options=[1, 4, 8, 13], value=4, key='suavizado')
        fig, p = e2.fig_serie(r2, suav, horizonte)
        g = r2['regresion']
        k = st.columns(4)
        k[0].metric('Intervenciones esperadas', f"{p.prediccion.sum():.0f}")
        k[1].metric('Promedio por semana', f"{p.prediccion.mean():.1f}")
        k[2].metric('R² del modelo', f"{g['r2']:.2f}")
        k[3].metric('Error típico (RMSE)', f"{g['rmse']:.1f}")
        chart('Historia y predicción', fig, 'Barras: lo registrado cada semana. Línea dorada: lo que predice el modelo; la banda marca el rango razonable.', 'e2a')
        a, b = st.columns(2, gap='medium')
        with a:
            chart('Tendencia y estacionalidad', e2.fig_descomposicion(r2), 'Descomposición aditiva con ciclo de 52 semanas. Con 2.5 ciclos de historia, la estacionalidad es indicativa; la tendencia es lo confiable.', 'e2b')
        with b:
            st.markdown('##### Qué dice el análisis')
            ad, dd = r2['adf_serie'], r2['adf_diferencia']
            acf_v = r2['acf_pacf']['acf']; banda = r2['acf_pacf']['banda']
            fuera = [str(i) for i in range(1, 5) if abs(acf_v[i]) > banda]
            est = (f"La serie original es estacionaria al 5 % (ADF p = {ad['p_valor']:.3f}), aunque con una tendencia suave que la regresión incluye" if ad['estacionaria']
                   else f"La serie original no es estacionaria (ADF p = {ad['p_valor']:.2f})")
            st.markdown(f"- **Estacionariedad.** {est}; con una diferencia lo es con holgura (p < 0.001).\n"
                        f"- **Memoria.** Los rezagos {', '.join(fuera) if fuera else 'ninguno de los primeros 4'} superan la banda de 95 % (±{banda:.2f}): la actividad de una semana se parece a la de semanas anteriores, sin ser un patrón fuerte.\n"
                        f"- **Residuos.** Durbin-Watson = {g['durbin_watson']:.2f} (cerca de 2: sin autocorrelación) y media ≈ 0. Shapiro-Wilk p = {g['shapiro_p']:.5f}: los residuos no son del todo normales porque los datos son conteos.\n"
                        f"- **Comprobación.** Los coeficientes a mano coinciden con scikit-learn hasta {r2['comparacion_sklearn']['max_dif_abs']:.0e}.")
            st.dataframe(e2.tabla_coef(r2).style.format({'Coeficiente β': '{:.4f}', 'Error estándar': '{:.4f}', 't': '{:.2f}', 'p': '{:.3f}'}), hide_index=True, width='stretch')
        a, b = st.columns(2, gap='medium')
        with a:
            chart('Autocorrelación (ACF) de la serie', e2.fig_acf(r2, 'acf_pacf', 'acf'), 'Barras fuera de la banda dorada son correlaciones significativas.', 'e2c')
        with b:
            chart('Autocorrelación parcial (PACF)', e2.fig_acf(r2, 'acf_pacf', 'pacf'), 'Ayuda a ver cuántos rezagos aportan información propia.', 'e2d')
        chart('Diagnóstico de residuos', e2.fig_residuos(r2), 'Centrados en cero, con una cola a la derecha (semanas con muchas intervenciones juntas) y las líneas diagonales propias de los conteos enteros. Confirma que el modelo es solo una referencia.', 'e2e')
        st.markdown(f'<div class="mt-notice"><b>Alcance.</b> La serie viene de la bitácora de los 7 camiones ({r2["serie"]["total"]} intervenciones con fecha, de abril de 2024 a octubre de 2026). '
                    f'Con {g["n"]} semanas el modelo explica poco (R² = {g["r2"]:.2f}) y sirve como referencia de ritmo, no como pronóstico de fallas individuales. Algunas fechas están inferidas por el orden de la hoja (ver Calidad de datos).</div>', unsafe_allow_html=True)
        st.download_button('Descargar predicción en CSV', p.to_csv(index=False).encode('utf-8-sig'), 'prediccion_semanal.csv', 'text/csv')

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
st.caption('MineTrac · Data Startup · Importes en MXN · Información real de Máquinas Centella (camiones); operación pendiente')
