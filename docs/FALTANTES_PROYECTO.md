# Qué falta para completar el proyecto MineTrac

Corte: 3 de noviembre de 2026 (entrega E2). Con la libreta transcrita, la bitácora de los 7 camiones y el catálogo ya tenemos una base real para el tablero. Lo que sigue se divide en lo que solo puede dar la empresa y lo que construimos nosotros.

## 1. Datos que solo puede dar la empresa

| Prioridad | Dato | Para qué lo necesitamos | Estado |
|---|---|---|---|
| Alta | Fecha de falla y de regreso a operación de cada paro (aunque sea por mes) | Horas fuera de servicio, disponibilidad y predicciones con sentido | La libreta casi nunca lo anota |
| Alta | Excel consolidado: horas trabajadas por turno, toneladas, tarifas e ingresos | Módulo financiero: ingresos, margen operativo neto por equipo y tarifas para contratos | La empresa lo está consolidando (carta del 25 de oct) |
| Alta | Lectura del horómetro al servicio o al cambio de pieza | Intervalos reales de servicio, vida útil y costo por hora | Solo 1 de 540 anotaciones de la libreta |
| Media | Tipo de pieza (original, genérica, reman) y proveedor real en cada compra | Módulo 1: costo por hora útil de cada opción | La libreta lo menciona en 85 anotaciones, sin sistema |
| Media | Montos de las intervenciones sin costo | Que el gasto deje de ser parcial | 182 de 257 en camiones; en la libreta hay 50 anotaciones con varias cifras |
| Media | Validar la libreta: fechas, montos, clasificación y T1 y T2 (¿son parte de la flota?) | Pasar de transcripción a dato confirmado y decidir si el catálogo pasa de 21 a 23 equipos | Pendiente de confirmación |
| Baja | Estado del resto de los equipos (solo se sabe K1 descontinuado y M2 nuevo) | Excluir equipos fuera de servicio del análisis | Pendiente |

Qué hacer mientras llega: usar la libreta y la bitácora para lo descriptivo (qué se repara, cuánto cuesta, cada cuánto se atiende), declarar el límite en cada gráfica y, si hace falta un supuesto (por ejemplo, una tarifa por hora de equipo parado), marcarlo como supuesto del equipo y pedir que la empresa lo confirme.

## 2. Lo que construimos nosotros para E2 (guía, entrega del 3 de noviembre)

| Requisito de E2 | Estado |
|---|---|
| Limpieza modular con pytest en el worker | Avanzado: `etl_bitacora.py` y `etl_libreta.py` con pruebas (17 en total) |
| Series temporales: descomposición, ADF, ACF y PACF | Falta. Con pocos datos conviene hacerlo por semana o mes y declarar la limitación |
| Regresión implementada a mano con NumPy | Falta. Candidato: gasto o anotaciones por mes frente a tendencia |
| Dashboard v2 | Avanzado: ya tiene la pestaña Libreta de taller; falta la sección de series y regresión |
| Diagrama de arquitectura | Falta |
| PostgreSQL | Falta |
| API de ingesta con FastAPI | Falta |
| Cola y worker | Falta |
| Demo: subir un CSV y verlo en el tablero en menos de 5 minutos | Falta |

## 3. Pendientes de nube (Codex)

- Subir `clean/libreta_eventos.csv`, `clean/libreta_resumen.json` y el nuevo `clean/inventario.csv` al bucket y recargar el tablero.
- Ampliar el permiso de lectura del rol de la instancia a esos archivos nuevos (`s3:GetObject` sobre `clean/libreta_*`); con el permiso actual el tablero mostraría la pestaña vacía.
- Subir la transcripción de la libreta a `raw/` (el rol no lee `raw/`), con el bucket privado.
- Repetir la captura de IAM y seguridad con la instancia real (i-081fa473088bece22).
- No borrar recursos de la versión de demostración sin confirmación de Carlos.
