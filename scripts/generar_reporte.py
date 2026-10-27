"""Genera las gráficas de docs/ y el documento técnico docs/E1-dashboard.md con las cifras de data/clean.

Uso: python scripts/pipeline_e1.py && python scripts/generar_reporte.py
"""
from pathlib import Path
import sys, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/tablero'))
from figures import views                                                  # noqa: E402
from core import resumen, eventos, ciclo_cercano, recomendaciones          # noqa: E402

m = pd.read_csv(ROOT / 'data/clean/mantenimiento.csv')
r = json.loads((ROOT / 'data/clean/resultados.json').read_text(encoding='utf-8'))
ab, fb = r['auditoria_bitacora'], r['auditoria_bitacora']['formato']
charts, aux = views(m)
titulos = [t for t, _ in charts]
k = resumen(m)
ev = eventos(m).copy()
ev['fecha'] = pd.to_datetime(ev.fecha)
comp, por, mes, vida, spec, peaks = aux['componentes'], aux['por_camion'], aux['por_mes'], aux['vida'], aux['spectrum'], aux['peaks']
recs = recomendaciones(m, aux)
p7, p15 = ciclo_cercano(spec, 7), ciclo_cercano(spec, 15)
serie = aux['serie']

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
T, G, Y = '#147e88', '#c78b21', '#9bbdcc'
for i in range(6):
    fig, ax = plt.subplots(figsize=(10.8, 4.6), layout='constrained')
    if i == 0:
        z = comp.head(10).sort_values('costo_mxn')
        ax.barh(z.componente, z.costo_mxn / 1000, color=[G if x == comp.iloc[0].componente else Y for x in z.componente])
        ax.set_xlabel('Miles de MXN (solo intervenciones con monto)')
    elif i == 1:
        ax.barh(por.index, por['Con monto'], color=T, label='Con monto anotado')
        ax.barh(por.index, por['Sin monto'], left=por['Con monto'], color='#c8d9e1', label='Sin monto anotado')
        ax.set_xlabel('Intervenciones registradas'); ax.legend(frameon=False)
    elif i == 2:
        sin, con = ev[ev.costo_mxn_intervencion.isna()], ev[ev.costo_mxn_intervencion.notna()]
        ax.scatter(sin.fecha, sin.camion_id, s=14, color='#c8d9e1', label='Sin monto anotado')
        ax.scatter(con.fecha, con.camion_id, s=np.clip(con.costo_mxn_intervencion / 400, 14, 300), color=T, alpha=.7, label='Con monto (tamaño = costo)')
        ax.legend(frameon=False, loc='upper center', bbox_to_anchor=(.5, -.1), ncol=2); ax.invert_yaxis()
    elif i == 3:
        ax.bar(mes.index, mes.values, width=22, color=[T if x == mes.idxmax() else Y for x in mes.index]); ax.set_ylabel('Intervenciones por mes')
    elif i == 4:
        z = vida.sort_values('mean')
        ax.barh(z.componente, z['mean'], color=Y)
        for yy, (v, n) in enumerate(zip(z['mean'], z['count'])):
            ax.text(v + 4, yy, f'{v:.0f} d (n={int(n)})', va='center', fontsize=8)
        ax.set_xlabel('Días promedio entre cambios (intervalos mayores a 30 días)')
    else:
        sp = spec[spec.periodo_dias.between(2, 60)].sort_values('periodo_dias')
        ax.plot(sp.periodo_dias, sp.amplitud, color='#4d84b5')
        for pk in peaks[:2]:
            ax.axvline(pk['periodo_dias'], color=G, ls='--', lw=1)
            ax.annotate(f"{pk['periodo_dias']:.1f} días", xy=(pk['periodo_dias'], pk['amplitud']), xytext=(8, -4), textcoords='offset points')
        ax.axvline(15, color='#999', ls=':', lw=1); ax.annotate('15 días', xy=(15, 0), xytext=(4, 6), textcoords='offset points', color='#666')
        ax.set_xlabel('Duración del ciclo (días)'); ax.set_ylabel('Amplitud (intervenciones por día)')
    ax.set_title(titulos[i], loc='left', fontweight='bold', pad=14, fontsize=11)
    ax.grid(axis='x' if i in (0, 1, 4) else 'y', alpha=.15)
    fig.text(.99, .995, 'BITÁCORA REAL · Máquinas Centella', ha='right', va='top', fontsize=8, color='#6b7782')
    fig.savefig(ROOT / f'docs/grafica_{i + 1}.png', dpi=150); plt.close(fig)

top = comp.iloc[0]
share = 100 * top.costo_mxn / comp.costo_mxn.sum()
top2 = comp.head(2)
share2 = 100 * top2.costo_mxn.sum() / comp.costo_mxn.sum()
sin_monto = 100 - k['pct_con_monto']
L = []
A = lambda t: L.append(t.replace('**', ''))
A('# E1. Dashboard empresarial de MineTrac')
A('## Contexto y procedencia')
A('MineTrac apoya a Máquinas Centella S.A. de C.V. a controlar costos, mantenimiento y operación de su maquinaria pesada. Esta es la entrega E1 (26 de octubre de 2026) del Proyecto Integrador Data Startup del TecNM campus Colima.')
A(f'Datos reales que nos entregó la empresa: (1) el catálogo de 21 equipos (11 cargadores, 2 minicargadores, 1 retroexcavadora y 7 camiones) y (2) la bitácora de reparaciones de los 7 camiones, una hoja por camión, con {ab["intervenciones"]} intervenciones y ${k["gasto_mxn"]:,.0f} MXN de gasto anotado. También recibimos un documento de contexto con tres módulos: refacciones e insumos, operación y registro de trabajo, y balance financiero por equipo.')
A('Este informe y el tablero usan únicamente esa información. No se generan registros simulados ni se imputan montos faltantes. Las fechas corregidas, las clasificaciones y el reparto de costos son transformaciones analíticas, identificadas y pendientes de validación. Las horas trabajadas, las toneladas, las tarifas y los ingresos todavía no existen en formato digital: la empresa los lleva en papel y, según su carta del 25 de octubre de 2026, está recopilando, revisando y consolidando la información con sus departamentos en un archivo de Excel. Por eso el balance financiero por equipo y el indicador de tarifas quedan pendientes y se incorporarán cuando llegue ese archivo.')
A('## Pregunta de negocio')
A('Pregunta de negocio: ¿qué refacciones pesan más en el gasto de mantenimiento, qué camiones se reparan más y cuánto se repite un mismo trabajo? Pregunta analítica: medir el gasto y la repetición de cambios por componente y por camión, y detectar periodicidades en las intervenciones. La señal para la FFT es el conteo diario de intervenciones registradas.')
A('## Datos y procedimiento')
A(f'Cada fila del Excel es una intervención. Un módulo de limpieza (services/worker/etl_bitacora.py) la convierte en una tabla ordenada con una fila por intervención y sistema: {ab["registros_clean"]} registros. Las fechas se corrigen con el orden cronológico de cada hoja, los montos se reparten en partes iguales entre los sistemas de una misma intervención, las piezas se clasifican con palabras clave del texto y se omiten nombres de proveedores; este procesamiento no detectó proveedores y conserva sin_dato. El texto libre y los nombres no salen del módulo hacia el tablero ni al repositorio. La clasificación de componente y la condición de la pieza (nueva o reparada) son una interpretación del texto y deben validarse con la empresa.')
A(f'Solo {k["pct_con_monto"]:.0f}% de las intervenciones ({k["con_monto"]} de {k["intervenciones"]}) trae monto, por lo que el gasto del tablero es una suma parcial y no el gasto total. Los montos que faltan no se inventan.')
A('## Limpieza reproducible y auditoría')
A(f'La bitácora ya traía errores de captura. Se revisaron los cinco tipos que pide la guía. Nulos: {ab["nulos_costo"]} intervenciones sin monto (se dejan sin monto) y {ab["nulos_fecha_imputados"]} filas sin fecha (heredan la de la fila anterior). Duplicados: {ab["duplicados"]}. Negativos: {ab["negativos"]}. Atípicos: {ab["atipicos"]} (un ajuste completo de motor de $149,000 MXN en el camión C7, por encima del límite de ${ab["limite_atipico_mxn"]:,.0f}; se conserva por estar anotado, pendiente de validar con comprobante). Formato: {ab["formato_total"]} problemas, entre ellos {fb["fechas_texto_interpretadas"]} fechas escritas a mano, {fb["fechas_anio_corregido"]} años equivocados (incluida una fecha de 2029), {fb["fechas_solo_anio"]} fecha con solo el año, {fb["costo_extraido_de_texto"]} montos escritos dentro del texto, {fb["texto_en_columna_costo"]} texto en la columna de costo y {fb["costo_en_columna_servicio"]} monto en la columna de servicio. Filas recibidas: {ab["registros_raw"]}. Filas limpias: {ab["registros_clean"]}. Residuales: los {ab["nulos_costo"]} montos que nadie anotó y el atípico verificado.')
A('## Cuatro KPIs visibles')
A(f'1. Intervenciones: {k["intervenciones"]}. Eventos distintos de la bitácora; cada intervención cuenta una vez aunque toque varios sistemas.')
A(f'2. Gasto registrado: ${k["gasto_mxn"]:,.0f} MXN. Suma de los montos anotados; es una suma parcial, pendiente de conciliar con comprobantes.')
A(f'3. Costo promedio: ${k["promedio_mxn"]:,.0f} MXN por intervención con monto.')
A(f'4. Repeticiones por 100 intervenciones: {k["pct_reincidencia"]:.1f} ({k["reincidencias"]} trabajos sobre el mismo componente del mismo camión en hasta 30 días). Es una razón por componente y fecha, no el porcentaje de intervenciones fallidas.')
A('Los valores corresponden a toda la bitácora; cada filtro del tablero (periodo, camión y sistema) los recalcula. Si una selección no tiene datos se muestra un aviso y no un indicador en cero.')
A('## Seis visualizaciones con hallazgos')
interp = [
    f'Gasto registrado por componente. {top2.componente.iloc[0]} y {top2.componente.iloc[1]} suman {share2:.0f}% del gasto anotado. Un componente con poco gasto puede ser solo uno cuyo monto no se anotó.',
    f'Intervenciones por camión. En gris están las que no tienen monto: {sin_monto:.0f}% del total. Más intervenciones no significa un camión peor; también depende de cuánto trabaja.',
    f'Cada punto es una intervención. Los puntos grises no tienen monto, lo que muestra qué tan incompleta es la captura de costos.',
    'Intervenciones por mes en toda la flota. Sirve para ver cargas de trabajo del taller, no para predecir fallas.',
    'Con las fechas de cambios repetidos se estima cada cuánto se vuelve a trabajar un componente. Es una aproximación: falta el horómetro al momento del cambio para medir horas de servicio.',
    f'Análisis de Fourier de las intervenciones diarias. El ciclo de 7 días tiene una fuerza {p7["veces_mediana"]:.1f} veces la mediana del espectro, mientras que el de 15 días tiene {p15["veces_mediana"]:.1f}.',
]
for i, t in enumerate(titulos):
    A('### ' + str(i + 1) + '. ' + t)
    A(f'![Gráfica {i + 1}](grafica_{i + 1}.png)')
    A(interp[i])
A('## FFT e interpretación en días')
A(f'Se cuentan las intervenciones por día desde el {r["serie"]["inicio"]} hasta el {r["serie"]["fin"]} ({r["serie"]["dias"]} días, con ceros en los días sin registro), se resta la tendencia lineal y se aplica una ventana de Hann antes de la FFT. Frecuencia de muestreo: una observación por día. Primer pico: f={peaks[0]["frecuencia_ciclos_dia"]:.6f} ciclos/día, T=1/f={peaks[0]["periodo_dias"]:.2f} días. Un ciclo de 7 días significa que el registro de intervenciones se repite cada semana (por ejemplo, días de la semana en que el taller recibe o entrega camiones). No significa que un camión falle con esa frecuencia.')
A(f'El ciclo de 15 días (quincena) no supera el umbral descriptivo: su fuerza es {p15["veces_mediana"]:.1f} veces la mediana del espectro, es decir, no supera el umbral descriptivo de 2.5 veces la mediana, sin prueba formal de significancia. Lo reportamos tal cual: con {k["intervenciones"]} intervenciones en unos 900 días la señal es débil, y 15 fechas de la bitácora se completaron con la de la fila anterior, lo que puede suavizar o crear patrones. Cuando lleguen las horas trabajadas por día se repetirá el análisis sobre esa señal, que es la que sí permite hablar de ciclos de operación.')
A('## Tres recomendaciones gerenciales')
for n, (_, titulo, texto) in enumerate(recs, 1):
    A(f'{n}. {titulo}. {texto}')
A('## Implementación del dashboard')
A('Streamlit muestra una franja que indica qué datos son reales y qué está pendiente, cuatro tarjetas (la cuarta es una razón por 100 intervenciones), filtros de periodo, camión y sistema, seis gráficas interactivas, seis pestañas (Vista general, Mantenimiento y refacciones, Ciclos, Flota y operación, Calidad de datos y Explorar datos) y descargas en CSV. La pestaña Flota y operación muestra el catálogo de 21 equipos y explica que la operación está pendiente de entrega por la empresa.')
A('El modo s3 lee clean/mantenimiento.csv, clean/inventario.csv y clean/resultados.json con boto3 y credenciales temporales de la instancia. No hay contraseñas ni claves en el repositorio. Si la lectura falla, el tablero lo informa y no la sustituye con una copia local.')
A('## Nube y presupuesto')
A('Arquitectura verificada el 26 de octubre de 2026: pipeline de limpieza -> bucket S3 privado minetrac-reales-251869518832-20261026 en us-east-1, con raw/ (dos Excel originales) y clean/ (cuatro archivos depurados) -> Streamlit en EC2 t3.micro. URL: http://54.204.60.100:8501/ . Stack: minetrac-e1-reales. Usuario de despliegue: admin-25460343; rol de instancia minetrac-e1-reales-ReadRole-XxCmmx32Dnlz, con lectura de tres tablas clean y del ZIP de aplicación; ListBucket limitado por prefijo. El rol no lee raw/. Bloqueo público de S3 activado y cifrado AES256; disco cifrado e IMDSv2. Puerto 8501 para el tablero, sin SSH público. No se guardan claves. Si S3 falla no se usan copias locales. Evidencias: evidencias/s3_raw_clean_real.png, evidencias/dashboard_real_aws.png, evidencias/iam_y_seguridad_real.png. Presupuesto objetivo $0; se conserva la alerta mensual de $1 USD con umbral real $0.01 USD. EC2, disco e IPv4 pueden consumir créditos o generar cargos; la alerta no detiene el consumo. La URL HTTP es para la entrega académica autorizada; no captura credenciales ni datos adicionales.')
A('![Evidencia de almacenamiento](evidencias/s3_raw_clean_real.png)')
A('![Dashboard real conectado a AWS](evidencias/dashboard_real_aws.png)')
A('## Verificación')
A('Pruebas automáticas (pytest): indicadores de un caso pequeño hecho a mano; calendario diario completo; FFT con periodos conocidos y rechazo de series cortas o con huecos; lectura de fechas escritas a mano; corrección de años equivocados; montos en texto; reparto de costos entre sistemas (el total se conserva); conteos de la bitácora real (257 intervenciones, 75 con monto, $928,832); seis gráficas y tres recomendaciones.')
A('## Defensa individual')
A('¿Qué proviene de la empresa? El catálogo y la bitácora. Los indicadores son cálculos; las fechas inferidas y la clasificación de piezas requieren validación. ¿Qué falta? Horas, toneladas, tarifas e ingresos; la empresa los está consolidando en un Excel.')
A(f'¿Por qué no se inventan los montos que faltan? Porque {sin_monto:.0f}% de las intervenciones no trae monto y rellenarlo cambiaría las conclusiones. Se reporta cuánto falta.')
A('¿Qué significa 0.142857 ciclos/día? Un ciclo cada 7 días. No significa que una máquina falle cada semana.')
A('¿Por qué el ciclo de 15 días no aparece? Porque en la bitácora real no supera ese umbral descriptivo. La guía lo pide como ejemplo de lo que se debe buscar, y reportamos el resultado honesto.')
A('¿Por qué raw y clean? raw conserva los originales para auditar; clean tiene el esquema listo para los indicadores.')
A('## Pendientes con el cliente')
A('Excel consolidado de la empresa (horas trabajadas por turno, toneladas, tarifas y horómetro); tipo de pieza (original o genérica) y proveedor en cada compra; lectura del horómetro al cambiar una pieza; fecha de falla y de regreso a operación de cada paro (para medir las horas fuera de servicio que pidió la empresa en la entrevista); montos de las intervenciones sin costo; y validar la clasificación de componentes. Con esos datos el tablero podrá calcular el costo por hora útil de cada refacción y el balance financiero por equipo, que son los módulos 1 y 3 del documento de contexto.')
A('## Límites de interpretación y entrega parcial')
A('La entrega se presenta con la información disponible, conforme a lo acordado con los profesores según lo informado por el equipo. La carta del 25 de octubre acredita que la empresa consolida datos; no certifica cifras ni la aprobación académica. Se adjunta sin modificar.')
A('La bitácora limpia contiene una fecha 2022-01-01 creada como referencia al disponer solo del año 2022; ese día no fue observado. Hay 15 intervenciones con fecha heredada, 3 con año corregido y 4 con texto interpretado. fecha_calidad permite distinguirlas. Los totales monetarios no dependen de estas fechas, pero los filtros, intervalos y FFT sí. No se calculan ingresos, margen, disponibilidad ni costo por hora sin sus datos.')
A('El control de duplicados del módulo identifica repeticiones dentro de una misma fila de origen; no permite afirmar que no haya intervenciones duplicadas entre filas distintas. Los 182 montos faltantes permanecen nulos. El monto atípico de $149,000 está anotado, pero no se verificó con factura. Los intervalos mayores de 30 días excluyen las repeticiones cortas y no representan vida útil. La ausencia de registro diario se representa con cero intervenciones registradas, no prueba ausencia de fallas ni captura completa.')
A('## Referencias')
A('Guía oficial PROYECTO_INTEGRADOR_DATA_STARTUP_ALUMNOS: E1 y rúbrica. Documento de contexto Maquina Centella Contexto. Carta de Máquinas Centella del 25 de octubre de 2026.')
A('Documentación técnica: AWS S3 (https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html); Streamlit (https://docs.streamlit.io/develop/api-reference); NumPy FFT (https://numpy.org/doc/stable/reference/routines.fft.html).')
(ROOT / 'docs/E1-dashboard.md').write_text('\n\n'.join(L), encoding='utf-8')
(ROOT / 'docs/resumen_resultados.json').write_text(json.dumps({'titulos': titulos, 'kpis': k}, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
print('Seis figuras y documento técnico creados.')
