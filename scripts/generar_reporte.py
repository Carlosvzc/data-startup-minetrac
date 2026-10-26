
from pathlib import Path
import sys,json,html
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services/tablero'))
from figures import views
from core import metrics
d=pd.read_csv(ROOT/'data/clean/operacion.csv');r=json.loads((ROOT/'data/clean/resultados.json').read_text(encoding='utf-8'))
_,a=views(d);eq=a['equipment'];cat=a['category'];wk=a['weekday']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
for i in range(6):
 fig,ax=plt.subplots(figsize=(10.8,4.2),layout='constrained')
 if i==0:ax.plot(pd.to_datetime(a['daily'].fecha),a['daily'].ingreso_mxn,color='#147e88',lw=1);ax.set_ylabel('Ingresos (MXN)')
 elif i==1:ax.bar(cat.categoria,cat.ingreso_mxn,color='#147e88');ax.set_ylabel('Ingresos (MXN)')
 elif i in [2,3]:
  field='margen_pct' if i==2 else 'mant_h';z=eq.sort_values(field,ascending=i==2)
  ax.bar(z.equipo_id,z[field],color='#147e88');ax.set_ylabel('Margen directo (%)' if i==2 else 'Mantenimiento (MXN/h)')
 elif i==4:ax.bar(wk.dia,wk.horas,color='#147e88');ax.set_ylabel('Horas diarias medias')
 else:
  spec=a['spectrum'];spec=spec[spec.periodo_dias.between(2,60)]
  ax.plot(spec.frecuencia_ciclos_dia,spec.amplitud_h,color='#147e88')
  for peak in a['peaks'][:2]:
   ax.axvline(peak['frecuencia_ciclos_dia'],color='#c78b21',ls='--',lw=1)
   ax.annotate(f"{peak['periodo_dias']:.0f} días",xy=(peak['frecuencia_ciclos_dia'],peak['amplitud_h']),xytext=(8,-10),textcoords='offset points')
  ax.set_xlabel('Frecuencia (ciclos/día)');ax.set_ylabel('Amplitud (horas)')
 ax.set_title(a['titles'][i],loc='left',fontweight='bold',pad=16,fontsize=11)
 ax.grid(axis='y',alpha=.15);ax.tick_params(axis='x',labelsize=8)
 fig.text(.99,.01,'SIMULADO · semilla 42',ha='right',fontsize=8,color='#6b7782')
 fig.savefig(ROOT/f'docs/grafica_{i+1}.png',dpi=170);plt.close(fig)
topmaint=eq.loc[eq.mant_h.idxmax()];lowmargin=eq.loc[eq.margen_pct.idxmin()]
k=r['kpis'];aud=r['auditoria']
lines=[
'# E1. Dashboard empresarial de MineTrac',
'## Contexto y procedencia',
'MineTrac centraliza operación, ingresos y mantenimiento de maquinaria para apoyar programación y revisión de contratos. La E1 corresponde a la entrega del 26 de octubre de 2026 del proyecto Data Startup del TecNM Campus Colima.',
'El inventario de 21 ID procede de EQUIPOS MAQ.CENTELLA.xlsx (Hoja2): 11 cargadores, 7 camiones, 2 minicargadores y 1 retroexcavadora. El usuario informó que es provisional. Se conserva intacto y trazable en data/raw/. No se verificó propiedad, fabricante ni condición de los equipos. LORESA se conserva literalmente.',
'La guía permite emplear datos sintéticos cuando la empresa no entrega información real. Con autorización del usuario, se construyó un escenario de operación de 420 días (2025-08-01 a 2026-09-24), semilla 42 y 21 equipos. Son 8,820 observaciones equipo-día limpias. Todas las horas, tarifas, costos, ingresos, paros y estacionalidades son simulados. No se atribuyen resultados financieros a la empresa. Los audios no se usaron como evidencia cuantitativa.',
'## Pregunta de negocio',
'¿Qué equipos requieren revisión del costo de mantenimiento, cómo se distribuyen los ingresos y cuándo conviene preparar capacidad operativa? Pregunta analítica: comparar margen directo y mantenimiento por hora y detectar periodicidades de actividad. La señal analizada es la suma diaria de horas trabajadas de la flota.',
'## Diseño de los datos simulados',
'Se programa un turno de 12 horas por equipo y día. Horas trabajadas: 6.3 + 1.15 cos(2πt/7) + 0.72 cos(2πt/15) + 0.0008t + ruido normal (σ=0.20) + ajuste por equipo, acotadas entre cero y horas programadas menos paro. Los paros se muestrean de un conjunto de valores entre 0 y 2 horas. No se modelan intervalos superpuestos.',
'Los camiones cobran por tonelada. Los otros equipos cobran por hora. La tarifa base es 55 MXN/t para camiones, 1,250 MXN/h para cargadores, 750 MXN/h para minicargadores y 950 MXN/h para retroexcavadora, con ajuste sintético de hasta 7.5%. La productividad de camiones es de 20 a 26 t/h. Esos valores son supuestos didácticos, no cotizaciones.',
'Los costos variables dependen de las horas y categoría. Los costos fijos diarios se añaden una sola vez. El mantenimiento es un costo sintético diario ocasional generado con probabilidad 0.035 e importe entre 1,000 y 8,000 MXN. No representa órdenes reales ni permite comparar durabilidad OEM contra genéricos. Esa función pertenece a la evolución del producto.',
'## Limpieza reproducible y auditoría',
'Se sembraron cinco errores deliberadamente en el escenario; no se afirma que provinieran del Excel. La fuente raw se conserva y clean_data no consulta la base previa a la corrupción. Se normaliza el ID, se detectan duplicados por equipo y fecha y solo se descartan observaciones idénticas. Los conflictos de contenido se rechazan.',
'Reporte cuantitativo: 40 nulos en horas; 30 filas duplicadas; 15 horas negativas; 10 atípicos de 99 horas; 25 ID con minúsculas y espacios. Filas raw: 8,850. Filas clean: 8,820. Residuales después de la limpieza: cero en cada uno de los cinco controles.',
'Los negativos y atípicos se convierten a faltantes, sin cambiar el signo como una supuesta corrección universal. Se imputan junto con los nulos por interpolación cronológica dentro del mismo equipo. En extremos se usa el valor válido más cercano. Se aplica el límite físico de programadas menos paro y se etiqueta cada corrección. En un sistema real se pediría validación documental antes de tratar una imputación como observación.',
'Por ser una simulación, se reconstruyen toneladas, ingresos y costos variables a partir de las horas depuradas. No se modifican costos de mantenimiento al corregir horas. El CSV de correcciones conserva el valor original, motivo y valor final. El error absoluto medio de las horas reconstruidas contra la verdad sintética, usado solo para evaluar el ejercicio y nunca para limpiar, es '+f"{r['error_imputacion_mae_h']:.6f} horas por fila.",
'## Cuatro KPIs visibles',
f"1. Ingresos del periodo: $ {k['ingresos_mxn']:,.2f} MXN. Fórmula: suma de ingresos; por fila se calcula horas × tarifa o toneladas × tarifa, según modalidad.",
f"2. Margen directo: {k['margen_directo_pct']:.2f}%. Fórmula: 100 × (Σ ingresos − Σ costos operativos − Σ mantenimiento) / Σ ingresos. El numerador es $ {k['margen_directo_mxn']:,.2f} MXN. No es utilidad neta: no incluye depreciación, impuestos ni financiamiento.",
f"3. Mantenimiento por hora: $ {k['mantenimiento_mxn_h']:.2f} MXN/h. Fórmula: Σ mantenimiento ($ {k['mantenimiento_mxn']:,.2f}) / Σ horas ({k['horas_trabajadas']:,.4f}). Se usa razón de sumas y se evita promediar razones individuales.",
f"4. Disponibilidad física: {k['disponibilidad_pct']:.2f}%. Fórmula: 100 × (Σ horas programadas − Σ horas de paro) / Σ horas programadas. No equivale a utilización y no se deduce del total de horas trabajadas.",
'Los cuatro resultados pertenecen al escenario simulado completo. Cada filtro del tablero los recalcula. Si una selección no tiene datos se muestra un mensaje y no un KPI cero inventado.',
'## Seis visualizaciones con hallazgos']
for i,title in enumerate(a['titles']):
 lines+=['### '+str(i+1)+'. '+title,'![Gráfica '+str(i+1)+'](grafica_'+str(i+1)+'.png)']
 interpretations=[
 'La serie permite observar la variación y el crecimiento suave incorporados al escenario; no es un pronóstico.',
 'La participación depende de número de equipos, tarifas y actividad simulada; no implica superioridad tecnológica.',
 'La comparación permite priorizar revisión de contratos y costos directos. Un mayor margen no demuestra mayor utilidad neta.',
 'La razón considera mantenimiento y horas de cada equipo. Un costo alto no prueba una falla ni justifica por sí solo sustituir la máquina.',
 'El efecto por día depende de la fecha inicial y del ciclo semanal generado. Se debe contrastar con un calendario real antes de operar.',
 'Los dos picos principales recuperan los periodos introducidos por diseño. El resto de picos tiene amplitud mucho menor y no se interpreta como un ciclo de negocio establecido.']
 lines.append(interpretations[i])
lines+=['## FFT e interpretación en días',
'Se agregan horas por fecha y se comprueban días consecutivos. Frecuencia de muestreo: una observación por día. N=420. Resolución de frecuencia: 1/420 = 0.00238095 ciclos/día. Nyquist: 0.5 ciclos/día, equivalente a un periodo mínimo de 2 días. Se retira tendencia lineal con ajuste NumPy y se aplica ventana Hann. La amplitud unilateral se normaliza por la suma de la ventana. Se buscan máximos locales para no contar dos bins vecinos de un mismo pico.',
f"Primer pico: f={a['peaks'][0]['frecuencia_ciclos_dia']:.8f} ciclos/día; T=1/f={a['peaks'][0]['periodo_dias']:.2f} días; amplitud={a['peaks'][0]['amplitud_h']:.3f} horas. Segundo: f={a['peaks'][1]['frecuencia_ciclos_dia']:.8f}; T={a['peaks'][1]['periodo_dias']:.2f} días; amplitud={a['peaks'][1]['amplitud_h']:.3f} horas.",
'Los 420 días contienen un número entero de ciclos de 7 y 15 días, lo que facilita verificar el método. Con registros reales, la duración, el muestreo irregular y el ruido modificarían la resolución y los picos. La FFT muestra periodicidad, no causalidad. Esta señal de horas no permite diagnosticar vibraciones mecánicas ni predecir fallas.',
'## Tres recomendaciones gerenciales para el escenario',
f"1. Programar una revisión preventiva y de comprobantes para {topmaint.equipo_id}, que presenta el mayor mantenimiento por hora ($ {topmaint.mant_h:.2f} MXN/h). Responsable propuesto: mantenimiento. Revisar antes del siguiente ciclo semanal; éxito: costos conciliados por orden y reducción verificada contra un periodo comparable, sin inventar una meta de ahorro.",
'2. Preparar personal e insumos considerando los ciclos de 7 y 15 días del escenario. Responsable propuesto: operaciones. Revisar calendario semanal y abastecimiento quincenal; éxito: menor tiempo de paro sin reducir disponibilidad. No modificar turnos de la empresa hasta contrastar el patrón con partes reales.',
f"3. Revisar tarifa, productividad y costos de {lowmargin.equipo_id}, que tiene el menor margen directo de la simulación ({lowmargin.margen_pct:.2f}%). Responsable propuesto: administración. Comparar modalidad y trabajo equivalentes; éxito: decisión documentada de mantener o renegociar basada en ingresos y costos conciliados. No se recomienda cancelar un contrato real a partir de esta simulación.",
'## Implementación del dashboard',
'Streamlit presenta la etiqueta de simulación, cuatro tarjetas, filtros de fecha, categoría, equipo, ubicación y modalidad, seis visualizaciones interactivas, auditoría y descarga CSV. Los filtros recalculan los indicadores. El espectro requiere al menos 30 días consecutivos en la selección. La función no completa huecos automáticamente. Los datos de demostración local y los datos leídos desde S3 usan el mismo esquema y cálculos.',
'El modo s3 lee clean/operacion.csv y clean/resultados.json mediante boto3, usando credenciales temporales del entorno AWS. No hay contraseñas, claves persistentes ni enlaces firmados guardados en el repositorio. Si falla la nube se informa del error y no se sustituye silenciosamente por un archivo local.',
'## Nube y presupuesto',
'Arquitectura E1: generador y limpieza → bucket S3 privado con raw/ y clean/ → Streamlit en EC2. Se verificó la identidad IAM individual admin-25460343. CloudShell se utilizó para preparar el despliegue, no para alojar el tablero. La instancia usa IMDSv2 y un rol con s3:GetObject limitado a dos archivos clean y el ZIP de despliegue. El bucket mantiene los cuatro bloqueos de acceso público. La demostración pública HTTP no recoge credenciales ni datos personales. No es un entorno de producción para datos reales confidenciales.',
'La cuenta dispone de un presupuesto existente de 1 USD, una notificación de gasto real superior a 0.01 USD y suscripción por correo. Los créditos del plan gratuito se verificaron en consola. Una alerta avisa y no detiene gasto. Con autorización del usuario se desplegó una instancia EC2 t3.micro con disco cifrado de 8 GB. El servidor, el disco y la IPv4 pueden consumir créditos. No se crearon RDS ni NAT Gateway. Tras evaluar la E1, revisar el consumo y detener o retirar la demostración.',
'## Verificación',
'Pruebas ejecutadas: reconciliación de los cinco errores y conteos; reglas físicas de horas; identidades contables; KPI de un caso pequeño calculado a mano; FFT con periodos conocidos; prueba de Streamlit con cuatro KPIs, seis gráficas y filtros, incluida selección vacía. Resultado: 4 pruebas aprobadas. Las capturas de la interfaz y la evidencia de nube se guardan en docs/.',
'## Defensa individual',
'¿Por qué no se presenta esto como información real? Porque los datos operativos fueron generados con semilla 42 y los ciclos se introdujeron por diseño. El inventario es la única fuente empresarial recibida.',
'¿Por qué el costo por hora usa razón de sumas? Para ponderar cada observación por su actividad y no dar el mismo peso a equipos con pocas y muchas horas.',
'¿Qué significa 0.142857 ciclos/día? Un ciclo cada 1/0.142857 = 7 días. No significa que una máquina falle cada semana.',
'¿Por qué raw y clean? raw permite reproducir y auditar la transformación; clean contiene el esquema listo para indicadores. No se sobrescribe la fuente.',
'¿La alerta evita gastos? No. Es una notificación. Se debe controlar uso, créditos y cierre de sesiones.',
'## Referencias',
'Guía oficial PROYECTO_INTEGRADOR_DATA_STARTUP_ALUMNOS (2).pdf: E1 en página 4; rúbrica en página 6; estructura de repositorio y autorización de datos sintéticos en páginas 8 y 9.',
'AWS S3: https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html',
'AWS CloudShell: https://docs.aws.amazon.com/cloudshell/latest/userguide/welcome.html',
'Streamlit: https://docs.streamlit.io/develop/api-reference',
'NumPy FFT: https://numpy.org/doc/stable/reference/routines.fft.html']
(ROOT/'docs/E1-dashboard.md').write_text('\n\n'.join(lines),encoding='utf-8')
(ROOT/'docs/resumen_resultados.json').write_text(json.dumps({'titulos':a['titles'],'equipo_mayor_mant_h':topmaint.to_dict(),'equipo_menor_margen':lowmargin.to_dict()},ensure_ascii=False,indent=2),encoding='utf-8')
print('Seis figuras y documento técnico creados.')

