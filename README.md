# MineTrac · data-startup-minetrac

Proyecto Integrador DATA STARTUP · Cómputo en la Nube (IAD-2408) y Analítica de Datos (IAD-2403)
Tecnológico Nacional de México campus Colima · Ingeniería en Inteligencia Artificial

**Qué es:** plataforma en la nube para llevar el historial de fallas y reparaciones de maquinaria minera, con tablero y pronóstico de horas fuera de servicio y riesgo de falla por equipo.
**Cliente:** Máquinas Centella S.A. de C.V.
**Nube:** Amazon Web Services (AWS, capa gratuita)
**URL pública:** [Dashboard E1 en AWS](http://67.202.18.79:8501/) · escenario simulado

## Equipo
- Carlos Alejandro Vizcaino Anguiano · Cloud Lead
- Diego Reyes Natilla · Data Lead

## Entregables
| Entrega | Documento |
|---|---|
| E0 Propuesta | [docs/E0-propuesta.md](docs/E0-propuesta.md) |
| E1 Dashboard | [docs/E1-dashboard.md](docs/E1-dashboard.md) · [Informe PDF](docs/E1-informe.pdf) |
| E2 a E5 | entregas posteriores |

## Datos
Los datos completos no se suben al repositorio. En `data/sample/` hay una muestra pequeña. Mientras llegan los datos reales del cliente, se genera una bitácora sintética con:

```
cd data && python ../scripts/generar_bitacora.py
```

## E1 · Dashboard empresarial
- 21 equipos del catálogo provisional y 8,820 registros operativos simulados (420 días, semilla 42).
- 40 nulos, 30 duplicados, 15 negativos, 10 atípicos y 25 formatos corregidos.
- 4 KPIs, 6 visualizaciones, FFT con ciclos de 7 y 15 días y 3 recomendaciones.
- Amazon S3 privado con raw/ y clean/. EC2 lee únicamente los objetos autorizados con un rol temporal.
- [Matriz de evidencia](docs/matriz_E1.md), [estado AWS](docs/estado_aws.json) y [notebook ejecutado](notebooks/01_eda_y_limpieza.ipynb).

**Procedencia:** el catálogo es provisional. Horas, paros, tarifas, costos, ingresos y ciclos son sintéticos. Las cifras del tablero no representan resultados reales de Máquinas Centella.

### Reproducir en un entorno Python 3.11 o posterior
Desde la raíz del repositorio:
    python -m pip install -r requirements-dev.txt
    python scripts/generar_datos.py
    python -m pytest tests -q
    python -m streamlit run services/tablero/app.py

Modo local: se muestra expresamente como demostración local. Modo nube: configurar MINETRAC_STORAGE=s3, MINETRAC_BUCKET=minetrac-e1-251869518832 y AWS_DEFAULT_REGION=us-east-1, usando una sesión temporal o un rol de instancia. No se guardan claves en GitHub y no hay sustitución automática de S3 por datos locales.

### Infraestructura y presupuesto
La plantilla [infra/minetrac-ec2.json](infra/minetrac-ec2.json) reproduce la demostración. El puerto público 8501 muestra solo datos simulados. El bucket mantiene bloqueo público. Es HTTP para demostración E1; no debe recibir credenciales ni datos reales confidenciales.
La alerta existente notifica gasto real superior a 0.01 USD. EC2, disco e IPv4 pueden consumir créditos mientras estén provisionados. Detener la instancia tras la evaluación reduce consumo; el disco sigue provisionado. No se cambió el plan de la cuenta.


### Diseño del tablero
Cinco secciones: Vista general, Equipos y costos, Ciclos de operación, Calidad de datos y Explorar datos. Los filtros se aplican a los cuatro indicadores y a las gráficas. La FFT se presenta en días, con explicación accesible y detalle del método. Los periodos menores de 30 días conservan las otras cinco gráficas y muestran la limitación de FFT.

