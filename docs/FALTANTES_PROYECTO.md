# Qué falta para completar el proyecto MineTrac

Corte: 13 de noviembre de 2026. Alcance actual: los 7 camiones (por indicación de la empresa, autorizada por los profesores). El diseño permite agregar después el resto de la flota.

## 1. Datos que la empresa lleva a mano y todavía no tiene capturados

| Prioridad | Dato | Para qué lo necesitamos |
|---|---|---|
| Alta | Fecha de falla y de regreso a operación de cada paro | Horas fuera de servicio, disponibilidad y predicciones con sentido |
| Alta | Horas trabajadas por turno, toneladas, tarifas e ingresos | Módulo financiero: ingresos, margen operativo neto por equipo y tarifas para contratos |
| Alta | Lectura del horómetro al servicio o al cambio de pieza | Intervalos reales de servicio, vida útil y costo por hora |
| Media | Tipo de pieza (original, genérica) y proveedor real | Costo por hora útil de cada opción |
| Media | Montos de las intervenciones sin costo (182 de 257) | Que el gasto deje de ser parcial |

Mientras tanto usamos la bitácora para lo descriptivo, declaramos el límite en cada gráfica y marcamos como supuesto del equipo cualquier cosa que no venga de la empresa.

## 2. Entregas

E0, E1 y E2 entregadas o en entrega. Siguen E3 (17 nov), E4 (30 nov) y E5 (2 dic) de Cómputo en la Nube, y Avance 1 (13 nov), Avance 2 (20 nov) y el proyecto integrador (30 nov) de Analítica de Datos.

## 3. Pendientes de nube

- Redesplegar el tablero con el alcance de camiones (ver `infra/e2_aws.sh` y `infra/actualizar_tablero.sh`).
- Cerrar el puerto 8000 al terminar la evaluación; la IP pública no es fija.
- Repetir la captura de IAM y seguridad con la instancia real (i-081fa473088bece22).
