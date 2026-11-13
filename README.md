# MineTrac · data-startup-minetrac

Proyecto Integrador DATA STARTUP · Cómputo en la Nube (IAD-2408) y Analítica de Datos (IAD-2403)
Tecnológico Nacional de México campus Colima · Ingeniería en Inteligencia Artificial

**Qué es:** con MineTrac revisamos el mantenimiento de los camiones de la empresa. Mostramos qué componentes concentran el gasto registrado y qué camiones tienen más intervenciones. El alcance actual son los 7 camiones (por indicación de la empresa, autorizada por los profesores); el diseño permite sumar después el resto de la flota. Aún no tenemos horas, toneladas ni tarifas para calcular ingresos y balances por equipo.
**Cliente:** Máquinas Centella S.A. de C.V.
**Nube:** Amazon Web Services (AWS, capa gratuita)
**URL pública:** http://98.93.132.212:8501/ (tablero) y http://98.93.132.212:8000/docs (API de ingesta). La dirección no es fija: cambia si se detiene la instancia, y la actualizamos aquí.

## Equipo
- Carlos Alejandro Vizcaino Anguiano · Cloud Lead
- Diego Reyes Natilla · Data Lead

## Entregables
| Entrega | Documento |
|---|---|
| E0 Propuesta | [docs/E0-propuesta.md](docs/E0-propuesta.md) · [PDF](docs/E0-propuesta.pdf) |
| E1 Dashboard | [docs/E1-dashboard.md](docs/E1-dashboard.md) · [Informe PDF](docs/E1-informe.pdf) · [Matriz de evidencia](docs/matriz_E1.md) |
| E2 Cimientos en la nube | [docs/E2-arquitectura.md](docs/E2-arquitectura.md) · [Informe PDF](docs/E2-informe.pdf) · `docker compose up --build` · `python scripts/pipeline_e2.py` |
| Analítica de Datos · Avance 1 | [notebooks/Avance1_EDA_MineTrac.ipynb](notebooks/Avance1_EDA_MineTrac.ipynb) |
| E3 a E5 | entregas posteriores |

## Datos
| Dato | Estado | Archivo |
|---|---|---|
| Catálogo de 21 equipos (11 cargadores, 2 minicargadores, 1 retroexcavadora, 7 camiones); el alcance actual son los 7 camiones | Real | `EQUIPOS MAQ CENTELLA.xlsx` |
| Bitácora de reparaciones de los 7 camiones (257 intervenciones, $928,832 MXN anotados) | Real | `CAMIONES 12M3 Y 14M3.xlsx` |
| Horas trabajadas, toneladas, tarifas, ingresos y horómetro | **Fuera del alcance por ahora**: la empresa los lleva a mano y no los tiene capturados | - |

No simulamos datos ni completamos montos faltantes. Documentamos las fechas inferidas y el reparto de costos. Cuando la empresa tenga esos registros capturados se agregan el balance por equipo y el indicador de tarifas, y también el resto de la flota.

**Privacidad.** Los Excel originales y los datos completos no se suben a GitHub (`data/raw/` y `data/clean/` están en `.gitignore`). La tabla limpia no trae texto libre y los proveedores permanecen como sin_dato si no se cuenta con una identificación validada. En `data/sample/` hay muestras de 60 filas.

En su carta del 25 de octubre de 2026 la empresa indicó que reuniría el resto de la información; después comunicó que no tiene tiempo de entregarla y pidió centrarnos en los camiones. La carta se entregó por separado en Classroom y no forma parte del repositorio.

## Reproducir (Python 3.11 o posterior)
Desde la raíz del repositorio, con los dos Excel en `data/raw/` o indicando su ruta:

    python -m pip install -r requirements-dev.txt
    python scripts/pipeline_e1.py --equipos "EQUIPOS MAQ CENTELLA.xlsx" --camiones "CAMIONES 12M3 Y 14M3.xlsx"
    python scripts/generar_reporte.py      # gráficas y docs/E1-dashboard.md con las cifras
    python scripts/exportar_informe.py     # docs/E1-informe.pdf
    python -m pytest tests -q
    python -m streamlit run services/tablero/app.py

`pipeline_e1.py` limpia la bitácora, calcula indicadores y FFT, y escribe `data/raw/`, `data/clean/`, `data/sample/` y `docs/auditoria.csv`. Para ver también el resto de la flota (libreta de taller y predicción semanal, fuera del alcance actual) se arranca el tablero con `MINETRAC_ALCANCE=flota`.

## Ejecutar con Docker

Primero ejecutamos scripts/pipeline_e1.py con los dos Excel originales. Así generamos data/clean/, que no está en Git. Después ejecutamos docker compose up --build. Montamos esa carpeta en /app/data/clean como volumen de solo lectura. La imagen se construye sin copiar los datos completos. Comprobamos la configuración con docker compose config.

## E1 · Dashboard empresarial
- **Limpieza (cinco errores) de la bitácora real:** 182 intervenciones sin monto (no se inventan) y 15 filas sin fecha, 0 duplicados, 0 negativos, 1 atípico anotado, pendiente de comprobante ($149,000, ajuste de motor) y 16 problemas de formato (fechas escritas a mano, años equivocados, montos dentro del texto).
- **4 KPIs:** intervenciones, gasto registrado, costo promedio por intervención con monto y repeticiones por 100 intervenciones (hasta 30 días).
- **6 visualizaciones** con título de hallazgo, **FFT** de las intervenciones diarias (el ciclo de 7 días destaca; el de 15 no) y **3 recomendaciones** calculadas con los filtros.
- **Módulo 1 del documento de contexto (refacciones e insumos):** gasto por componente, línea de tiempo, días entre cambios y trabajos repetidos.
- **Pendiente con la empresa:** tipo de pieza (original o genérica), proveedor y horómetro al cambio; y la captura de horas, toneladas y tarifas (módulos 2 y 3).

### Nube y presupuesto

Desplegamos MineTrac en AWS y verificamos la conexión el 26 de octubre de 2026. Usamos el bucket privado minetrac-reales-251869518832-20261026, en us-east-1. En raw/ guardamos los dos Excel originales y en clean/ los archivos depurados . El tablero corre en una instancia EC2 t3.micro y lee las tablas desde S3. URL en esa fecha: http://54.204.60.100:8501/ ; hoy es http://98.93.132.212:8501/ porque la dirección cambió al reiniciar la instancia. El stack se llama minetrac-e1-reales.

Trabajamos con el usuario admin-25460343. El rol minetrac-e1-reales-ReadRole-XxCmmx32Dnlz permite leer las tres tablas clean y el ZIP de la aplicación; limitamos ListBucket por prefijo. El rol no lee raw/. Conservamos el bloqueo público de S3, el cifrado AES256, el disco cifrado e IMDSv2. Solo publicamos el puerto 8501 del tablero; no abrimos SSH. No guardamos claves. Si falla S3, mostramos el error sin cargar copias locales.

Conservamos un presupuesto objetivo de $0 y la alerta mensual de $1 USD, con aviso al superar $0.01 USD de gasto real. EC2, el disco y la dirección IPv4 pueden consumir créditos o generar cargos. La alerta avisa, pero no detiene el consumo. Usamos la URL HTTP para esta entrega; no pedimos credenciales ni capturamos datos adicionales.

Guardamos las capturas en evidencias/s3_raw_clean_real.png, evidencias/dashboard_real_aws.png y evidencias/iam_y_seguridad_real.png.

Para actualizar los datos, ejecutar el pipeline con los Excel nuevos, subir clean/ al mismo bucket y pulsar Recargar datos. Podemos actualizar los archivos sin rehacer el tablero. Plantilla: infra/minetrac-reales.json.

### Diseño del tablero
Seis pestañas: Vista general, Mantenimiento y refacciones, Ciclos, Flota y operación (los 7 camiones del catálogo y aviso de lo que queda para después), Calidad de datos y Explorar datos. Una franja arriba indica qué datos son reales y qué queda fuera del alcance. Los filtros (periodo, camión y sistema) se aplican a los cuatro indicadores y a las gráficas.
