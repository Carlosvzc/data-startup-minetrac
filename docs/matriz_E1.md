# Matriz de evidencia E1

| Requisito de la guía | Evidencia |
|---|---|
| Limpieza: 5 errores (nulos, duplicados, negativos, atípicos, formato) con reporte cuantitativo | `docs/auditoria.csv`, `services/worker/etl_bitacora.py`, pestaña "Calidad de datos" del tablero |
| 4 KPIs visibles de inmediato | Tarjetas del tablero (intervenciones, gasto registrado, costo promedio, repeticiones por 100 intervenciones) y prueba de caso pequeño en `tests/test_e1.py` |
| 6 visualizaciones con título de hallazgo | Gráficas 1 a 6 en `docs/` y en el tablero |
| FFT con ciclos de 7 y 15 días traducidos a días | Gráfica 6, sección "FFT" de `docs/E1-dashboard.md`, prueba `test_fft_recupera_ciclos_conocidos`. El ciclo de 7 días destaca descriptivamente; el de 15 no supera el umbral heurístico, sin prueba formal de significancia, y así se reporta |
| 3 recomendaciones en lenguaje de negocio | `docs/E1-dashboard.md` y sección "Tres recomendaciones" del tablero |
| Nube: carpetas `raw/` y `clean/` | Hecho: bucket privado minetrac-reales-251869518832-20261026 (us-east-1), evidencia docs/evidencias/s3_raw_clean_real.png. El script `scripts/ejecutar_aws.sh` sube los Excel originales a `raw/` y las tablas limpias a `clean/` |
| Nube: el tablero lee desde la nube con credenciales seguras | Hecho: http://54.204.60.100:8501/ el 26 de octubre (hoy http://98.93.132.212:8501/, la dirección cambió al reiniciar la instancia); evidencia docs/evidencias/dashboard_real_aws.png. Modo `MINETRAC_STORAGE=s3` con rol temporal de la instancia; no hay claves en el repositorio |
| Nube: acceso seguro (usuario individual, sin cuenta raíz, alerta activa) | Alerta de presupuesto activa (`docs/evidencias/alerta-presupuesto-aws.png`). El script rechaza identidades `root`. Usuario IAM admin-25460343 y rol limitado; evidencia docs/evidencias/iam_y_seguridad_real.png |
| Módulos del documento de contexto | 1) Refacciones e insumos: pestaña "Mantenimiento y refacciones" (falta tipo de pieza y horómetro al cambio). 2) Operación y 3) balance financiero: **fuera del alcance por ahora**: la empresa lleva a mano esa información y todavía no la tiene capturada |
| Código en GitHub | Repositorio `data-startup-minetrac` |

Procedencia: los originales vienen de la empresa (catálogo de equipos y bitácora de los 7 camiones); las fechas inferidas, la asignación de costos y las clasificaciones están documentadas como criterios analíticos. No hay datos simulados. El alcance actual son los camiones, por indicación de la empresa y con autorización de los profesores. En su carta del 25 de octubre de 2026 la empresa indicó que reuniría el resto de la información y después comunicó que no tiene tiempo de entregarla; la carta se entregó por separado en Classroom y no forma parte del repositorio.
