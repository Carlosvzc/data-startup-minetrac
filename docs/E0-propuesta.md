# E0 · Propuesta de negocio

**Proyecto Integrador DATA STARTUP** · Cómputo en la Nube (IAD-2408) y Analítica de Datos (IAD-2403)
Tecnológico Nacional de México campus Colima · Ingeniería en Inteligencia Artificial

| Campo | Información |
|---|---|
| Proyecto | MineTrac · `data-startup-minetrac` |
| Institución | Tecnológico Nacional de México, campus Colima |
| Carrera | Ingeniería en Inteligencia Artificial |
| Asignaturas | Cómputo en la Nube (IAD-2408) y Analítica de Datos (IAD-2403) |
| Cliente | Máquinas Centella S.A. de C.V. |
| Cloud Lead | Carlos Alejandro Vizcaino Anguiano · matrícula 25460343 |
| Data Lead | Diego Reyes Natilla · matrícula 25460331 |

> Estado de la información: este documento se basa solo en el catálogo de equipos, la bitácora de reparaciones de los camiones, el documento de contexto, la carta y la entrevista que entregó o dio la empresa. No usamos datos simulados. Por indicación de la empresa, autorizada por los profesores, el alcance de esta etapa son los 7 camiones; el diseño permite agregar después el resto de la flota. Lo que todavía falta se lista en la sección 8.

---

## 1. Problema y cliente

Trabajamos con una empresa que compra, opera y mantiene maquinaria pesada para minería. Revisamos su catálogo de 21 equipos: 11 cargadores, 2 minicargadores, 1 retroexcavadora y 7 camiones de 12 y 14 m³. Por indicación de la empresa, autorizada por los profesores, trabajamos por ahora solo con los 7 camiones y diseñamos el sistema para poder sumar después el resto de la flota. Quiere un sistema que le permita evaluar la rentabilidad de cada equipo, comparar la durabilidad de las refacciones según su origen (original de fábrica o genérica de proveedor local) y generar balances financieros para decidir en sus contratos.

Hoy esa información está dispersa. Según el documento de contexto, las horas trabajadas se capturan en papel o a mano y no hay un registro digital de horómetro, toneladas ni ingresos por equipo; la empresa nos informó por carta (25 de octubre de 2026) que reuniría el resto de la información y después nos comunicó que no tiene tiempo de entregarla, por lo que nos pidió centrarnos en los camiones. Recibimos una bitácora digital de reparaciones de los 7 camiones, una hoja por camión, con fechas, trabajos realizados y, solo a veces, el monto. La bitácora cubre 257 intervenciones principalmente entre abril de 2024 y octubre de 2026, con registros previos de 2023 y uno que solo indica el año 2022. Únicamente 75 traen monto anotado y suman $928,832 MXN, por lo que el costo total no se puede calcular ni conciliar todavía.

En la bitácora encontramos un ejemplo de un paro largo. El camión C4 registra el 9 de marzo de 2026 que se rompió la base del gato hidráulico y se volteó la caja en la peña; entró a taller en abril y se anotó como entregado el 6 de mayo, casi dos meses después. El entrevistado (sección 3) cuenta un caso muy parecido: el gato perdió presión por una fuga de aceite, el camión se volteó sin lesionados, la pieza nueva tardó cerca de mes y medio en llegar y además hubo que rehacer una parte de la caja. La fecha que él da ("hace unos dos meses") no cuadra con la bitácora, que ubica el caso del C4 entre marzo y mayo de 2026; falta confirmar con la empresa si es el mismo evento. En otro ejemplo, el camión C5 acumula 57 intervenciones, y en 69 ocasiones se volvió a trabajar el mismo componente de un camión en hasta 30 días.

**Decisión de negocio que queremos ayudar a tomar:** si una refacción barata o local compensa frente a una original, qué equipo conviene atender primero y con qué refacciones, y si la tarifa de un contrato debe subirse, mantenerse o descartarse, con datos reales y no a ojo.

## 2. Lean Canvas

| Bloque | Contenido |
|---|---|
| **Problema** | 1) El historial de cada equipo vive en un bloc de notas en el celular de la directora general; para consultarlo hay que llamarle, y eso frena las decisiones. 2) Cuando un equipo se detiene, no se mide cuántas horas estuvo fuera de servicio ni cuánto tardó en llegar la pieza. 3) En la bitácora de camiones falta el monto en 7 de cada 10 intervenciones y los operadores usan apodos para las piezas, lo que dificulta analizar qué se repara. 4) Las horas trabajadas se anotan en papel, así que no hay balance de ingresos contra gastos por máquina para negociar tarifas. |
| **Segmento de clientes** | Empresas que compran y operan maquinaria pesada para minería y llevan su mantenimiento en bitácoras. Cliente inicial: Máquinas Centella S.A. de C.V. |
| **Propuesta de valor** | Un lugar único donde se consulta el historial de cada equipo (qué se le ha cambiado, qué falla seguido, cuánto estuvo detenido) para decidir por dónde seguir. Después, comparar el costo por hora útil de cada refacción y ver el margen operativo por equipo con un indicador de tarifas. |
| **Solución** | Plataforma en la nube con tres módulos: refacciones e insumos (origen, proveedor, horómetro al cambio y costo), operación y registro de trabajo (horas por turno y toneladas, con tarifas por hora o por tonelada) y balance financiero por equipo. Recibe CSV o formularios, limpia los datos, los guarda en un data lake y los muestra con pronósticos. |
| **Canales** | Por validar con el cliente: demostración directa con la dirección y recomendación a otras empresas del mismo giro. |
| **Fuentes de ingreso** | Suscripción mensual por flota; el precio se calcula en E5 con los costos de nube. Por validar con el cliente. |
| **Estructura de costos** | Servicios en la nube (cómputo, almacenamiento, base de datos, cola de mensajes), tiempo de desarrollo y soporte. En el proyecto el presupuesto de nube es de $0. |
| **Métricas clave** | Horas fuera de servicio por equipo (incluye la espera de la pieza), piezas que más se repiten, fallas por horas de uso, margen operativo neto por equipo, costo por hora útil de cada refacción y porcentaje de intervenciones con monto registrado. |
| **Ventaja injusta** | Partimos de la bitácora real de la empresa y de su documento de contexto, así que el modelo de datos usa su vocabulario (horómetro, peña, pista, camiones de 12 y 14 m³). La ventaja real dependerá de acumular, con captura disciplinada, hasta 10 años de historial por cliente. |

## 3. Entrevista

**Entrevistado (según la documentación del equipo):** Andrés Figueroa, representante y subdirector de Máquinas Centella S.A. de C.V.; participa en las negociaciones. La decisión final la toma la directora general, Fabiola Rodríguez.
**Fecha y duración reportadas por el equipo:** jueves 22 de octubre de 2026 · 15 min 12 s
**Evidencia:** grabación de video (https://drive.google.com/file/d/1T08lxQsw4fgzoZnzMQLRWwu1T9PTHPg2/view?usp=sharing) y transcripción completa en `docs/evidencias/entrevista_transcripcion.md` (https://github.com/Carlosvzc/data-startup-minetrac/blob/main/docs/evidencias/entrevista_transcripcion.md).
**Consentimiento:** al inicio se le preguntó si aceptaba que la entrevista se usara con fines académicos y respondió que sí.

### Pregunta 1. ¿Cuál es tu papel en las negociaciones y cómo participas cuando un problema operativo afecta los compromisos con el cliente?
Representa a la empresa, propone ideas o caminos a seguir y apoya en las negociaciones. La directora general, Fabiola Rodríguez, tiene la última palabra.

### Pregunta 2. Cuéntanos un caso reciente en que una falla o reparación complicó la operación.
Hace unos dos meses, un gato hidráulico con una pequeña fuga de aceite perdió presión al levantar la carga y el camión se volteó de lado, sin lesionados. Lo enderezaron con otros equipos y llegó al taller por sus propios medios, porque el daño no era estructural. Pidieron la pieza nueva, que tardó cerca de mes y medio en llegar, y al instalarla vieron que también se había doblado parte de la caja, que hubo que cortar, resoldar y acomodar. Mientras el equipo estuvo detenido dejó de generar y hubo que meter otro equipo para cumplir el proyecto. (Se parece al camión C4 de la bitácora: base del gato rota el 9 de marzo de 2026 y entrega el 6 de mayo, con la pieza tardando cerca de mes y medio. Pero la fecha no coincide, así que falta confirmar si es el mismo evento.)

### Pregunta 3. Desde que detectan una falla hasta que el equipo vuelve a trabajar, ¿cómo lo registran y cómo verifican que quedó bien?
Todo se registra en bitácoras. Cada ocho horas se hace un servicio de lubricación con revisión completa y, si hay una falla, el equipo se sustituye en ese momento. El horómetro indica las horas de trabajo y las piezas de desgaste (mangueras, aceite, joystick y otras) ya están contempladas. Para verificar una reparación, uno de los operadores con más experiencia hace en el taller una prueba extrema, llevando el equipo a sus límites.

### Pregunta 4. ¿Qué información consultas para decidir si conviene seguir operando una máquina y cuál es la más difícil de conseguir?
Lo más difícil es la información de los operadores: cada uno explica distinto y ponen apodos a las piezas, y luego no se sabe quién los puso ni por qué. La decisión de reparar casi siempre es "sí", porque no pueden quedarse sin equipos; el problema es cuánto tarda en llegar la pieza y cuánto estará fuera el equipo. Para cubrir esa espera, a veces "canibalizan" un equipo viejo y luego le devuelven la pieza. Prefieren el mantenimiento preventivo porque es mucho más barato que el correctivo.

### Pregunta 5. Si pudieras consultar el historial de cada equipo en un solo lugar, ¿qué necesitarías ver primero y cómo comprobarías que te ayuda?
Hoy todo está en un bloc de notas en el celular de la directora; para consultarlo hay que llamarle, y eso frena los procesos. Lo principal que necesitan ver es el número de equipo, qué tiene, qué le falla y qué le ha fallado en los últimos meses, para no repetir lo ya cambiado (por ejemplo, cabezas de motor o pistones) y saber qué falta por hacer.

### Preguntas que le gustaría que la aplicación responda
1. Qué equipo acumula más horas fuera de servicio por fallas y cuál es el que más dinero genera.
2. Cuáles son las piezas que más se descomponen (creen tener idea, pero quieren certeza).
3. Cuántas horas pasan hasta que llega la pieza y el equipo vuelve a trabajar.
4. Qué reparaciones ya están confirmadas y cuáles siguen pendientes de validar: si llegó la pieza, si se montó y si de verdad era esa la falla ("como ser un poco un médico").
5. Cómo cambia la frecuencia de fallas de cada equipo según sus horas de uso. Dijo que con esa información podrían trabajar bastante bien.

### Conclusiones
- La prioridad de la empresa es consultar el historial de cada máquina en un solo lugar y medir el tiempo fuera de servicio, incluida la espera de la pieza.
- Quieren conocer las piezas que más se repiten y qué equipo genera más dinero.
- El principal obstáculo de datos es la captura: bloc de notas, apodos de piezas y explicaciones distintas de cada operador. Por eso el proyecto clasifica las piezas con palabras clave y esa clasificación debe validarla la empresa.
- Hoy la bitácora no registra la fecha de la falla ni la de regreso a operación de forma sistemática, así que las horas fuera de servicio todavía no se pueden calcular para toda la flota.

## 4. Cadena de preguntas

Las cuatro primeras salen directamente de la entrevista.

| Pregunta de negocio | Pregunta analítica | Variable a predecir | Datos |
|---|---|---|---|
| ¿Qué equipo acumula más horas fuera de servicio por fallas? | ¿Cuántos días pasa detenido cada equipo entre la falla y su regreso, incluida la espera de la pieza? | `horas_fuera_de_servicio` por equipo y por falla | **Pendiente:** fecha de falla y de regreso a operación (hoy solo el caso del camión C4) |
| ¿Cuáles son las piezas que más se descomponen? | ¿Cuánto gasto y cuántas repeticiones concentra cada componente, y cuántos trabajos se repiten en hasta 30 días? | `repite_30d` (Sí/No): el mismo camión repite una falla en el mismo sistema en 1 a 30 días | Bitácora real (disponible) |
| ¿Cómo cambia la frecuencia de fallas con las horas de uso? | ¿Cuántas fallas hay por cada 100 horas de horómetro en cada equipo? | `fallas_por_100h` | **Pendiente:** lectura del horómetro |
| ¿Qué equipo es el que más dinero genera? | ¿Cuál es el margen operativo neto de cada equipo? | `margen_operativo_mxn` por equipo y por mes | **Pendiente:** horas, toneladas y tarifas |
| ¿Cuándo debo preparar taller y refacciones? | ¿Cuántas intervenciones tendrán los camiones por semana en los próximos 7 y 30 días? | `intervenciones_semanales` (conteo; horizontes de 1 y 4 semanas, equivalentes a 7 y 30 días) | Bitácora real (disponible, señal débil) |
| ¿Conviene comprar la pieza original o la local? (documento de contexto) | ¿Cuánto cuesta por hora útil cada refacción según su origen y proveedor? | `costo_por_hora_util` = costo de la pieza ÷ horas hasta el siguiente cambio | **Pendiente:** tipo de pieza y horómetro al cambio |

Con la bitácora se responden hoy las filas 2 y 5, que alimentan E1, E2 y E3 (ARIMA y clasificador). El resto depende de información que la empresa lleva a mano y todavía no captura; el diseño del tablero ya las contempla.

## 5. Inventario de datos

Usamos la información que recibimos de la empresa. No simulamos datos.

| Fuente | Contenido | Periodo | Volumen |
|---|---|---|---|
| `EQUIPOS MAQ CENTELLA.xlsx` | Catálogo (K1 descontinuado; M2 nuevo, sin historial todavía): 11 cargadores (950H, 950K, 966H, 966K, 966M, 972M), 2 minicargadores (236, 226), 1 retroexcavadora (416) y 7 camiones (Sterling, International y Loresa) | Actual | 21 equipos |
| `CAMIONES 12M3 Y 14M3.xlsx` | Bitácora de reparaciones de los 7 camiones: una hoja por camión, columnas por sistema (motor, electrónico, transmisión y dirección, caja y frenos, A/C y eléctrico, estético, llantas y servicio), costo y comentarios | Principalmente abril de 2024 a octubre de 2026; también hay registros de 2023 y uno con solo el año 2022 | 257 intervenciones, 317 registros por sistema |
| `Maquina Centella Contexto.txt` | Descripción de los tres módulos que quiere la empresa | Actual | Documento |
| Carta de Máquinas Centella (25 de octubre de 2026) | Indica que reuniría el resto de la información; después la empresa comunicó que no tiene tiempo de entregarla y pidió centrarnos en los camiones | Actual | Documento |

**Cumplimiento del mínimo de la guía.** Revisamos que la guía pide al menos 12 meses o 5,000 registros. La bitácora cubre 30 meses, así que cumplimos por periodo, aunque tiene pocos registros (317). La señal es limitada para modelos de series de tiempo; lo decimos desde ahora para no exagerar los resultados.

**Fuera del alcance por ahora:** horas trabajadas por turno, toneladas, tarifas por hora y por tonelada, lectura del horómetro, tipo de pieza (original o genérica) y proveedor real. La empresa los lleva en papel y todavía no los tiene capturados. No los simulamos: el tablero lo indica y esos módulos quedan para cuando existan los registros.

**Calidad de la bitácora.** Solo 75 de 257 intervenciones traen monto (29%). Hay fechas escritas a mano (`01/se/25`, `077sep/26`), años equivocados (una fecha de 2029), filas sin fecha, montos escritos dentro del texto y un ajuste de motor de $149,000 que es un monto atípico anotado, pendiente de comprobar. Las fechas inferidas se identifican con fecha_calidad. Documentamos cada transformación y los datos que faltan en la auditoría de E1.

**Columnas del catálogo (`EQUIPOS MAQ CENTELLA.xlsx`).** Una sola hoja (Hoja2) con tres bloques: cargadores (clave K1 a K11 y modelo), minicargadores (clave M1 y M2 y modelo), retroexcavadora (clave R1 y modelo 416) y camiones (clave C1 a C7 y marca). El archivo no trae año, serie, horómetro ni fecha de compra. En `inventario.csv` lo ordenamos así:

| Columna | Descripción | Estado |
|---|---|---|
| `equipo_id` | Clave del equipo (K, M, C) | Completa, 21 de 21 |
| `categoria` | Cargador, minicargador, retroexcavadora o camión; sale del encabezado del bloque | Completa |
| `modelo` | Modelo o marca que anotó la empresa | Completa |
| `estado` | K1 descontinuado, M2 nuevo (sin mantenimiento todavía); en los demás, `sin_indicacion` | Dato que nos dio la empresa para dos equipos |
| `naturaleza_dato` | Marca interna: dato real | Interna |
| `validacion` | Marca interna: pendiente de validar por la empresa | Interna |

| Columna de la bitácora limpia (`mantenimiento.csv`) | Descripción |
|---|---|
| `evento_id`, `camion_id`, `fecha` | Intervención, camión (C1 a C7) y día |
| `sistema`, `componente` | Sistema de la hoja y pieza clasificada con palabras clave |
| `condicion_pieza` | Nueva, reparada o no especificada (interpretación del texto) |
| `proveedor_codigo` | Proveedor anonimizado (P01, P02...) |
| `costo_mxn`, `costo_origen` | Monto repartido entre sistemas y su origen (registrado, extraído de texto o sin dato) |
| `dias_desde_cambio_anterior`, `vida_util_dias`, `reincidencia_30d` | Aproximación de durabilidad con fechas |
| `tipo_pieza` | Original o genérica: **por capturar**, no existe en el historial |

Los archivos completos no se suben al repositorio por privacidad; en `data/sample/` hay muestras de 60 filas sin texto libre ni nombres.

## 6. Arranque técnico

- **Proveedor de nube:** Amazon Web Services (AWS, capa gratuita).
- **Alerta de presupuesto ($0 a $5 USD):** activa. Presupuesto mensual "My Zero-Spend Budget" de $1.00 USD desde el 1 de octubre de 2026, con alerta por correo cuando el costo real supere $0.01 USD (correo verificado). Evidencia: `docs/evidencias/alerta-presupuesto-aws.png`.
- **Repositorio en GitHub:** https://github.com/Carlosvzc/data-startup-minetrac
- **Estructura del repositorio:** `docs/`, `data/sample/`, `scripts/`, `services/` (tablero y módulo de limpieza), `notebooks/`, `tests/`, `infra/` y `k8s/` según la guía; `infra/terraform/` y `k8s/` se llenan en E3.

## 7. Uso de IA generativa

Se usó Claude para ordenar el documento de contexto, proponer el borrador del Lean Canvas, programar la limpieza de la bitácora y construir el tablero. Las decisiones sobre el cliente, las preguntas y la clasificación de piezas las revisamos nosotros y las podemos explicar en la defensa.

## 8. Información pendiente

- **Entrevista:** confirmar si el caso del gato hidráulico que cuenta Andrés es el del camión C4 (la fecha no coincide con la bitácora).
- **De la empresa (cuando haya tiempo):** captura digital de horas y toneladas por turno, tarifas, horómetro, fecha de falla y de regreso a operación de cada paro, tipo de pieza (original o genérica) y proveedor en cada compra, lectura del horómetro al cambiar una pieza y los montos de las intervenciones sin costo.
- **Resto de la flota:** cargadores, minicargadores y retroexcavadora del catálogo; el diseño ya permite agregarlos.


## 9. Alcance de la entrega al 26 de octubre de 2026

Los profesores indicaron verbalmente al equipo que se podía entregar E0 y E1 con la información recibida y completar después los datos pendientes.

Los profesores autorizaron después centrar el proyecto en los 7 camiones, como pidió la empresa. En su carta del 25 de octubre de 2026 la empresa indicó que reuniría el resto de la información y luego comunicó que no tiene tiempo de entregarla. La carta se entregó por separado en Classroom y no forma parte del repositorio.



Las cifras derivan de los Excel originales, sin inventar montos. Algunas fechas se infieren por orden de la hoja; una fecha con solo año 2022 usa 01/01 como referencia técnica, no como día conocido. Se conserva fecha_calidad para auditar estas decisiones. La clasificación de piezas y la asignación igual de costos entre sistemas son criterios analíticos por validar. El indicador de 26.8 repeticiones por 100 intervenciones no representa porcentaje de fallas confirmadas.
