# MineTrac · data-startup-minetrac

Proyecto Integrador DATA STARTUP · Cómputo en la Nube (IAD-2408) y Analítica de Datos (IAD-2403)
Tecnológico Nacional de México campus Colima · Ingeniería en Inteligencia Artificial

**Qué es:** plataforma en la nube para controlar costos, mantenimiento y operación de maquinaria pesada. Hoy muestra qué refacciones pesan más en el gasto de mantenimiento y qué camiones se reparan más; el balance por equipo y las tarifas de contrato se agregan cuando la empresa entregue sus horas y toneladas.
**Cliente:** Máquinas Centella S.A. de C.V.
**Nube:** Amazon Web Services (AWS, capa gratuita)
**URL pública:** http://54.204.60.100:8501/

## Equipo
- Carlos Alejandro Vizcaino Anguiano · Cloud Lead
- Diego Reyes Natilla · Data Lead

## Entregables
| Entrega | Documento |
|---|---|
| E0 Propuesta | [docs/E0-propuesta.md](docs/E0-propuesta.md) |
| E1 Dashboard | [docs/E1-dashboard.md](docs/E1-dashboard.md) · [Informe PDF](docs/E1-informe.pdf) · [Matriz de evidencia](docs/matriz_E1.md) |
| E2 a E5 | entregas posteriores |

## Datos
| Dato | Estado | Archivo |
|---|---|---|
| Catálogo de 21 equipos (11 cargadores, 2 minicargadores, 1 retroexcavadora, 7 camiones) | Real | `EQUIPOS MAQ CENTELLA.xlsx` |
| Bitácora de reparaciones de los 7 camiones (257 intervenciones, $928,832 MXN anotados) | Real | `CAMIONES 12M3 Y 14M3.xlsx` |
| Horas trabajadas, toneladas, tarifas, ingresos y horómetro | **Pendiente**: la empresa los consolida en un Excel (carta del 25 de octubre de 2026) | — |

No se generan registros simulados ni montos faltantes. Las fechas inferidas y el reparto de costos son transformaciones analíticas documentadas. Cuando llegue el Excel consolidado se agregan el balance por equipo y el indicador de tarifas.

**Privacidad.** Los Excel originales y los datos completos no se suben a GitHub (`data/raw/` y `data/clean/` están en `.gitignore`). La tabla limpia no trae texto libre y los proveedores permanecen como sin_dato si no se cuenta con una identificación validada. En `data/sample/` hay muestras de 60 filas.

## Reproducir (Python 3.11 o posterior)
Desde la raíz del repositorio, con los dos Excel en `data/raw/` o indicando su ruta:

    python -m pip install -r requirements-dev.txt
    python scripts/pipeline_e1.py --equipos "EQUIPOS MAQ CENTELLA.xlsx" --camiones "CAMIONES 12M3 Y 14M3.xlsx"
    python scripts/generar_reporte.py      # gráficas y docs/E1-dashboard.md con las cifras
    python scripts/exportar_informe.py     # docs/E1-informe.pdf
    python -m pytest tests -q
    python -m streamlit run services/tablero/app.py

`pipeline_e1.py` limpia la bitácora, calcula indicadores y FFT, y escribe `data/raw/`, `data/clean/`, `data/sample/` y `docs/auditoria.csv`.

## E1 · Dashboard empresarial
- **Limpieza (cinco errores) de la bitácora real:** 182 intervenciones sin monto (no se inventan) y 15 filas sin fecha, 0 duplicados, 0 negativos, 1 atípico anotado, pendiente de comprobante ($149,000, ajuste de motor) y 16 problemas de formato (fechas escritas a mano, años equivocados, montos dentro del texto).
- **4 KPIs:** intervenciones, gasto registrado, costo promedio por intervención con monto y repeticiones por 100 intervenciones (hasta 30 días).
- **6 visualizaciones** con título de hallazgo, **FFT** de las intervenciones diarias (el ciclo de 7 días destaca; el de 15 no) y **3 recomendaciones** calculadas con los filtros.
- **Módulo 1 del documento de contexto (refacciones e insumos):** gasto por componente, línea de tiempo, días entre cambios y trabajos repetidos.
- **Pendiente con la empresa:** tipo de pieza (original o genérica), proveedor y horómetro al cambio; y el Excel consolidado con horas, toneladas y tarifas (módulos 2 y 3).

### Nube y presupuesto

Arquitectura verificada el 26 de octubre de 2026: pipeline de limpieza -> bucket S3 privado minetrac-reales-251869518832-20261026 en us-east-1, con raw/ (dos Excel originales) y clean/ (cuatro archivos depurados) -> Streamlit en EC2 t3.micro. URL: http://54.204.60.100:8501/ . Stack: minetrac-e1-reales. Usuario de despliegue: admin-25460343; rol de instancia minetrac-e1-reales-ReadRole-XxCmmx32Dnlz, con lectura de tres tablas clean y del ZIP de aplicación; ListBucket limitado por prefijo. El rol no lee raw/. Bloqueo público de S3 activado y cifrado AES256; disco cifrado e IMDSv2. Puerto 8501 para el tablero, sin SSH público. No se guardan claves. Si S3 falla no se usan copias locales. Evidencias: evidencias/s3_raw_clean_real.png, evidencias/dashboard_real_aws.png, evidencias/iam_y_seguridad_real.png. Presupuesto objetivo $0; se conserva la alerta mensual de $1 USD con umbral real $0.01 USD. EC2, disco e IPv4 pueden consumir créditos o generar cargos; la alerta no detiene el consumo. La URL HTTP es para la entrega académica autorizada; no captura credenciales ni datos adicionales.

Para actualizar los datos, ejecutar el pipeline con los Excel nuevos, subir clean/ al mismo bucket y pulsar Recargar datos. El código no necesita rehacerse. Plantilla: infra/minetrac-reales.json. La simulación previa ya no forma parte de esta entrega.

### Diseño del tablero
Seis pestañas: Vista general, Mantenimiento y refacciones, Ciclos, Flota y operación (catálogo y aviso de lo pendiente), Calidad de datos y Explorar datos. Una franja arriba indica qué datos son reales y qué está pendiente. Los filtros (periodo, camión y sistema) se aplican a los cuatro indicadores y a las gráficas.
