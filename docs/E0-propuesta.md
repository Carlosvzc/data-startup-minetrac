# E0 · Propuesta de negocio

**Proyecto Integrador DATA STARTUP** · Cómputo en la Nube (IAD-2408) y Analítica de Datos (IAD-2403)
Tecnológico Nacional de México campus Colima · Ingeniería en Inteligencia Artificial

**Equipo:** MineTrac (`data-startup-minetrac`)
**Integrantes:** Carlos Alejandro Vizcaino Anguiano (matrícula 25460343) · Diego Reyes Natilla (matrícula 25460331)
**Roles:** Carlos Alejandro Vizcaino Anguiano, Cloud Lead · Diego Reyes Natilla, Data Lead
**Cliente:** Máquinas Centella S.A. de C.V.

---

## 1. Problema y cliente

El cliente es una empresa que adquiere, opera y mantiene maquinaria pesada para minería (camiones, cargadores, excavadoras y equipos similares). Su dirección general está a cargo de Fabiola Rodríguez, quien toma la decisión final en cada caso, y nuestro contacto operativo es Andrés Figueroa, que participa en las negociaciones y propone soluciones.

Lo que les duele es muy concreto: **el historial de cada máquina vive en un bloc de notas dentro del celular de la directora**. Cuando un equipo falla no hay un lugar único donde consultar qué piezas ya se cambiaron, qué falló antes y qué sigue pendiente. Cada hora que una máquina está detenida deja de producir y, además, otro equipo tiene que cubrirla. En la entrevista nos contaron un caso de hace unos dos meses: un gato hidráulico con una fuga pequeña de aceite perdió presión al levantar la carga y el camión se volcó de lado. Reparar el gato y la caja dañada tomó cerca de mes y medio, casi todo esperando la refacción.

**Decisión de negocio que queremos ayudar a tomar:** qué equipo atender o preparar primero y con qué refacciones, para reducir las horas fuera de servicio y pasar de mantenimiento correctivo a preventivo.

## 2. Lean Canvas

| Bloque | Contenido |
|---|---|
| **Problema** | 1) El historial de fallas y reparaciones está disperso en notas personales. 2) No se sabe con certeza qué equipo acumula más horas detenido ni qué piezas se repiten. 3) La información de los operadores llega en lenguaje informal (hasta con apodos para las piezas). |
| **Segmento de clientes** | Empresas medianas que compran y operan maquinaria para minería y llevan su mantenimiento en bitácoras o notas. Cliente inicial: Máquinas Centella. |
| **Propuesta de valor** | Un tablero donde se consulta el historial completo de cada máquina en un solo lugar y que avisa qué equipo tiene más riesgo de falla y cuántas horas de paro se esperan. |
| **Solución** | Plataforma en la nube que recibe las bitácoras (API o CSV), las limpia, las guarda en un data lake y las muestra en un tablero con pronóstico de horas fuera de servicio y clasificación de riesgo por equipo. |
| **Canales** | Demostración directa con la dirección de la empresa, acceso por URL desde el celular y recomendación a otras empresas del mismo giro. |
| **Fuentes de ingreso** | Suscripción mensual por flota (el precio se calcula en E5 con los costos de nube). |
| **Estructura de costos** | Servicios en la nube (cómputo, almacenamiento, base de datos, cola de mensajes), tiempo de desarrollo y soporte. En el proyecto el presupuesto de nube es de $0. |
| **Métricas clave** | Horas fuera de servicio por equipo y por mes, proporción de mantenimiento preventivo contra correctivo, días de espera de pieza, error del pronóstico. |
| **Ventaja injusta** | Partimos de entrevistas con quien opera la flota, así que el modelo de datos usa su vocabulario (horómetro, piezas de desgaste, bitácora de lubricación). La ventaja real dependerá de acumular el historial de cada cliente. |

## 3. Entrevista

**Entrevistado:** Andrés Figueroa, Máquinas Centella S.A. de C.V. Aceptó que la entrevista se use con fines académicos.
**Duración de la grabación:** 13 min 12 s. **Evidencia:** `Entrevista.mp4` en Google Drive [PENDIENTE: enlace compartido].

**Pregunta 1. ¿Cuál es su papel y cómo participa cuando un problema operativo afecta compromisos con el cliente?**
Representa a la empresa, propone ideas o soluciones y apoya en las negociaciones. La decisión final es de la directora general.

**Pregunta 2. Cuéntenos un caso reciente donde una falla complicó la operación.**
El caso del gato hidráulico con fuga de aceite que provocó el volcamiento del camión (descrito arriba). La pieza nueva tardó cerca de mes y medio y hubo que rehacer parte de la caja. Mientras tanto otro equipo tuvo que cubrir y el camión dejó de generar.

**Pregunta 3. ¿Cómo registran la falla y cómo verifican que ya quedó bien?**
Todo se lleva en bitácoras y el horómetro indica el tiempo de trabajo de cada equipo. Cada 8 horas se hace un servicio de lubricación con revisión completa y ahí se detectan la mayoría de las fallas. Tras la reparación, un operador con experiencia hace una prueba extrema en el taller para confirmar que la pieza quedó bien.

**Pregunta 4. ¿Qué información consultan para decidir y cuál es la más difícil de conseguir?**
Lo más difícil es la información que dan los operadores, porque la explican cada uno a su manera y ponen apodos a las piezas. La reparación casi siempre se hace; el problema es cuánto tarda en llegar la pieza. Si el equipo es viejo se canibaliza una refacción mientras llega la nueva. Prefieren el mantenimiento preventivo porque sale mucho más barato que el correctivo.

**Pregunta 5. Si pudieran consultar el historial de cada equipo en un solo lugar, ¿qué querrían ver primero y cómo comprobarían que sirve?**
Hoy todo está en un bloc de notas en el celular de la directora. Lo primero sería ver qué equipo es, qué le ha fallado y qué piezas ya se cambiaron para saber qué más puede fallar. Además, al proponerles preguntas para el sistema respondió que le servirían: qué equipo acumula más horas fuera de servicio, qué equipo genera más dinero, cuáles son las piezas que más se descomponen, cuánto tarda en llegar una pieza y cómo cambia la frecuencia de fallas según las horas de uso.

**Lo que aprendimos.** El cliente ya sabe cuáles son sus piezas repetitivas y tiene varias en stock, pero no lo tiene medido. Lo que más valor tiene para ellos es la consulta rápida del historial y saber cuánto tiempo estará detenido un equipo. También hay que cuidar la privacidad de algunos datos, por lo que cualquier dato real se anonimiza antes de subirlo.

## 4. Cadena de preguntas

| Pregunta de negocio | Pregunta analítica | Variable a predecir |
|---|---|---|
| ¿Cuántas horas de paro tendré la próxima semana y qué tanto debo preparar? | ¿Cuántas horas fuera de servicio tendrá la flota por día durante los próximos 7 y 30 días? | `horas_fuera_servicio` diarias de la flota (horas, horizonte 7 y 30 días) |
| ¿Qué equipo tengo que revisar antes de que falle? | ¿Qué probabilidad tiene cada equipo de presentar una falla en los próximos 7 días? | `falla` (Sí/No) por equipo, horizonte 7 días |
| ¿Cambia la frecuencia de fallas cuando el equipo acumula más horas de uso? | ¿Qué relación hay entre el horómetro y las fallas por mes? | fallas por mes en función de `horometro` |

Las dos primeras alimentan los modelos de E3 (ARIMA y clasificador) y la tercera se resuelve con la regresión de E2. Las preguntas sobre piezas repetitivas y días de espera se responden directo en el tablero de E1.

## 5. Inventario de datos

**Fuente:** el cliente se comprometió a facilitarnos sus datos reales, que hoy viven en las notas de la directora. Se anonimizarán antes de subirlos al repositorio. Mientras llegan trabajamos con datos sintéticos generados con `scripts/generar_bitacora.py`, que simula una flota de 10 equipos con un patrón realista (más fallas en temporada de lluvias, piezas de desgaste frecuentes como mangueras y fugas, y espera larga en piezas mayores como motor y gato hidráulico). Si los datos reales llegan, se reemplazan y el proyecto aplica al bono de negocio real de E5.

| Dato | Detalle |
|---|---|
| Archivo | `bitacora_maquinaria.csv` |
| Periodo | 1 de octubre de 2024 al 30 de septiembre de 2026 (24 meses) |
| Volumen | 7,330 registros (una fila por equipo y día, más duplicados sembrados) |
| Equipos | 10 (3 camiones, 2 cargadores, 2 excavadoras, 1 motoconformadora, 1 perforadora, 1 retroexcavadora) |

| Columna | Descripción |
|---|---|
| `fecha` | Día del registro |
| `equipo_id` | Identificador del equipo (ej. CAM-01) |
| `tipo_equipo` | Camión, cargador, excavadora, etc. |
| `horometro` | Horas acumuladas del equipo |
| `horas_operadas` | Horas trabajadas ese día |
| `horas_fuera_servicio` | Horas detenido por falla, mantenimiento o espera de pieza |
| `tipo_evento` | Operación, Preventivo, Correctivo o Fuera de servicio |
| `componente` | Pieza que falló (manguera, motor, gato hidráulico, etc.) |
| `falla` | Sí/No |
| `dias_espera_pieza` | Días que tardó en llegar la refacción |
| `costo_reparacion_mxn` | Costo de la reparación |
| `validado` | Si la reparación ya fue confirmada |

El script siembra a propósito los cinco errores que pide E1: nulos, negativos, atípicos, formato inconsistente en `equipo_id` y duplicados. En el repositorio solo se sube una muestra de 60 filas en `data/sample/`.

## 6. Arranque técnico

- **Proveedor de nube:** Microsoft Azure (Azure for Students), que se mantendrá todo el proyecto.
- **Alerta de presupuesto:** [PENDIENTE: captura de la alerta activa en Cost Management, de $0 a $5 USD]
- **Repositorio en GitHub:** [PENDIENTE: enlace, con commits de ambos integrantes]
- **Estructura inicial:** carpetas `docs/`, `data/sample/`, `scripts/` ya creadas; faltan `notebooks/`, `services/`, `infra/terraform/`, `k8s/` y `tests/`.

## 7. Uso de IA generativa

Se usó Claude para transcribir la entrevista, ordenar sus respuestas, proponer el borrador del Lean Canvas y programar el generador de datos sintéticos. Las decisiones sobre el cliente, las preguntas y los datos las revisamos nosotros y las podemos explicar en la defensa.
