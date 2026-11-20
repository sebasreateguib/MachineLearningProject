# Cambios al informe: del Avance 1 al Informe final

Lista de todo lo que hay que modificar en `Informe-IEEE-Transactions.pdf`, sección por sección. Cada cambio indica si ya se puede escribir o si depende de una fase pendiente.

**Leyenda**

- ✅ **Listo:** las cifras ya están calculadas y verificadas (Fases 1 y 2).
- ⏳ **Pendiente:** depende de resultados de una fase futura. Se indica cuál.
- ✏️ **Corrección:** algo que el Avance 1 dice y hay que corregir o matizar.

> Todas las cifras marcadas ✅ salen de los scripts de `src/`. Para regenerarlas: `python src/reproduce_avance1.py` (muestra) y `python src/validate_parse.py` (dataset completo).

---

## Resumen de cambios

| Sección | Tipo de cambio | Estado |
|---|---|---|
| Encabezado | "AVANCE 1" → "PROYECTO FINAL" | ✅ |
| Resumen (abstract) | Reescribir con resultados sobre el dataset completo | ⏳ Fase 3 |
| I-B Objetivos | Agregar objetivo de la interfaz LogWatch | ✅ |
| I-C Dataset | Actualizar Tabla I; cuantificar el truncamiento | ✅ |
| I-D Preprocesamiento y EDA | Nuevo párrafo de parsing con Drain; nueva tabla de ambigüedad; **corregir Tabla IV y Figura 2** con el dataset completo | ✅ ✏️ |
| II Trabajos relacionados | Agregar referencias de SMOTE, scikit-learn, imbalanced-learn y Drain3 | ✅ |
| III Metodología | Detallar parsing, TF-IDF, fuga de datos y elección de Naive Bayes | ✅ |
| III Resultados preliminares | Responder la hipótesis abierta; quitar el "trabajo futuro (a)", que ya se hizo | ✅ ✏️ |
| **IV Resultados** (nueva) | 16 configuraciones, matriz de confusión, análisis de umbral | ✅ (falta la figura de la curva PR) |
| **V Discusión** (nueva) | Responder las 3 preguntas del proyecto | ✅ casi completa, ⏳ detalles de la Fase 4 |
| **VI Interfaz LogWatch** (nueva) | Descripción y captura | ⏳ Fase 5 |
| **VII Conclusiones** (nueva) | Conclusiones y trabajo futuro | ⏳ Fase 4 |

---

## Encabezado y título

- ✅ Cambiar el encabezado de página `MACHINE LEARNING – UTEC, AVANCE 1, 2026` por `MACHINE LEARNING – UTEC, PROYECTO FINAL, 2026`.
- ✅ En la nota al pie de autores: "Avance 1 – Proyecto 1, 2026" → "Informe final – Proyecto 1, 2026".
- El título puede quedarse igual.

---

## Resumen (abstract)

⏳ **Fase 3.** Hoy describe solo los experimentos preliminares con la muestra. Hay que reescribirlo con los resultados finales. Estructura sugerida:

> Los sistemas distribuidos a gran escala, como HDFS, generan volúmenes de logs que hacen inviable su revisión manual exhaustiva. Este trabajo aborda la detección de anomalías como un problema de clasificación binaria supervisada sobre el conjunto HDFS_v1 de Loghub (575,061 bloques, 2.9 % anómalos). Los 11.2 millones de líneas de log se parsearon con Drain y se transformaron en una matriz de conteo de eventos por bloque, validada contra la matriz de referencia de Loghub con coincidencia total. Se compararon 16 configuraciones (cuatro clasificadores, dos representaciones y dos estrategias de manejo del desbalance) mediante validación cruzada estratificada. El mejor modelo, **[MODELO]**, alcanzó un F1 de **[X]** en la clase anómala sobre el conjunto de prueba. Se muestra además que el recall limitado observado en experimentos preliminares se debía al truncamiento de la muestra: en el conjunto completo, solo el 1.9 % de las anomalías es indistinguible de un bloque normal por sus conteos. Los resultados se presentan en LogWatch, una interfaz interactiva para priorizar la revisión de bloques.

- ⏳ Completar `[MODELO]` y `[X]` con los resultados de la Fase 3.
- ✅ Index Terms: agregar **"Drain"** y **"datos desbalanceados"**.

---

## I. Introducción

### I-A Planteamiento del problema

Sin cambios.

### I-B Objetivos

- ✅ Agregar un **objetivo específico 5**:
  > 5. Presentar los resultados en una interfaz interactiva que permita explorar el compromiso entre precisión y recall y priorizar la revisión de bloques sospechosos.
- ✅ Matizar el **objetivo 4**. El informe final ya no solo "propone mejoras": **cuantifica** el límite del enfoque por conteo (ver la nueva tabla de I-D).

### I-C Descripción del dataset

✅ **Tabla I.** Actualizar dos filas de la columna *Loghub (HDFS_v1)*:

| Fila | Hoy dice | Cambiar a |
|---|---|---|
| Parsing | No; requiere aplicar Drain | Drain3 aplicado en este trabajo (Sección I-D) |
| Uso | Entrenamiento y evaluación finales | *(igual)* |

Y agregar una fila nueva:

| Fila | Loghub (HDFS_v1) | Loglizer |
|---|---|---|
| Validación | `Event_occurrence_matrix.csv` (matriz de referencia de Loghub) | — |

✅ **Párrafo sobre el truncamiento.** El que empieza con *"Es importante notar que la muestra corresponde a las primeras líneas del log…"* hoy lo explica de forma cualitativa. Agregar al final:

> En la muestra, 178 de las 313 anomalías (56.9 %) tienen exactamente el mismo vector de conteos que algún bloque normal.

✅ **Tabla II.** Agregar la fila de **E8**, que se usa en la discusión del parsing:

| Evento | Plantilla | Descripción |
|---|---|---|
| E8 | `[*]PacketResponder[*]for block[*]Interrupted[*]` | El hilo que confirma paquetes se interrumpe antes de terminar. Aparece solo en bloques anómalos. |

⏳ Revisar en la Fase 4 si conviene agregar otros eventos que resultan importantes en el dataset completo: **E20, E23, E21 y E6**. Ver la Tabla IV corregida más abajo.

### I-D Preprocesamiento y EDA

✏️ **Primer párrafo.** Hoy dice *"Cada línea de log fue previamente parseada mediante el algoritmo Drain"*. Eso aplica a la muestra, que ya venía parseada. Hay que aclarar que los logs del dataset completo **los parseamos nosotros**. Párrafo nuevo sugerido:

> Para el conjunto completo, los 11,175,629 mensajes se parsearon con Drain3, una implementación de Drain [3], con profundidad 4. Antes de agrupar se enmascararon los identificadores de bloque y las direcciones IP. Con el umbral de similitud de 0.5 que usa Loghub, Drain fusionaba los eventos E8 (*"PacketResponder … Interrupted"*, una interrupción anómala) y E11 (*"PacketResponder … terminating"*, el cierre normal), que difieren solo en la última palabra. Por ello se usó un umbral de 0.7, que los separa sin fragmentar en exceso: se obtuvieron 49 clusters en 54 segundos. Los umbrales de 0.85 o más producían miles de clusters y eran entre 10 y 40 veces más lentos. Cada cluster recibió el identificador de la plantilla oficial de Loghub con la que coincide (E1–E29), lo que permite comparar los eventos con la literatura. La matriz de conteo resultante coincide con la matriz de referencia de Loghub (`Event_occurrence_matrix.csv`) en el 100 % de los 575,061 bloques, los 29 eventos y las etiquetas.

✅ **Nota de reproducibilidad.** Agregar después de la descripción de la matriz de conteo:

> Las filas de la matriz se ordenan por `BlockId`. Este detalle afecta la reproducibilidad: `train_test_split` con `random_state=42` depende del orden de las filas, y con otro orden se obtiene una partición distinta.

✅ **Párrafo de B1/B2/B3.** Agregar una **tabla nueva** que cuantifica el límite del enfoque:

| | Muestra | Conjunto completo |
|---|---|---|
| Bloques | 7,940 | 575,061 |
| Vectores de conteo distintos | 17 | 589 |
| Anomalías con el mismo vector que un bloque normal | 178 de 313 (**56.9 %**) | 319 de 16,838 (**1.9 %**) |
| Errores mínimos de cualquier clasificador basado solo en conteos | 161 | **36** |

> *Errores mínimos* = para cada vector distinto, la cantidad de bloques de la clase minoritaria entre los que comparten ese vector. Es una cota inferior: ningún clasificador determinista que solo vea conteos puede cometer menos errores sobre ese conjunto.

✏️ **Tabla IV: corregir con el dataset completo.** La tabla actual se calculó sobre la muestra truncada. En el conjunto completo, los eventos con mayor diferencia entre clases cambian:

| Evento | Normal | Anomaly | Diferencia |
|---|---|---|---|
| E9 | 3.000 | 1.891 | 1.109 |
| E11 | 3.000 | 1.901 | 1.099 |
| E26 | 3.009 | 2.391 | 0.618 |
| E23 | 2.444 | 1.896 | 0.548 |
| E21 | 2.448 | 2.107 | 0.341 |
| E20 | 0.000 | 0.316 | 0.316 |
| E5 | 3.005 | 2.729 | 0.276 |
| E6 | 0.005 | 0.266 | 0.261 |

> Opción recomendada: mantener la tabla de la muestra como referencia del Avance 1 y agregar esta como "conjunto completo", o reemplazarla directamente.

✅ **Eventos exclusivos de anomalías.** Dato útil para el texto: E7 (excepción en `writeBlock`) aparece en el **19.6 %** de los bloques anómalos y en **ningún** bloque normal. E8 aparece en el **0.27 %** de los anómalos y en ningún normal.

✏️ **Figura 2 y su párrafo: corregir con el dataset completo.** En la muestra, E5 concentraba el 93.4 % de la importancia. En el conjunto completo, el mismo árbol (profundidad 3, entrenado en el 80 % de entrenamiento) reparte la importancia así:

| Evento | Importancia |
|---|---|
| E9 | 43.5 % |
| E20 | 35.0 % |
| E26 | 20.3 % |
| E3 | 1.2 % |
| E5 | 0 % |

Texto sugerido para reemplazar el párrafo actual:

> En la muestra, un único evento (E5) concentraba el 93.4 % de la importancia. Ese resultado era un artefacto del truncamiento: en el conjunto completo, E5 no aparece entre las variables usadas por el árbol, y la importancia se reparte entre E9 (43.5 %), E20 (35.0 %) y E26 (20.3 %). Además, 7,171 bloques anómalos (42.6 %) tienen E5 = 3, igual que un bloque normal, por lo que una regla basada solo en E5 no puede detectarlos.

⏳ **Figura 1.** Agregar o reemplazar por la distribución de clases del conjunto completo: 558,223 normales y 16,838 anómalos (2.93 %).

---

## II. Trabajos relacionados

✅ **Agregar referencias** para las herramientas que usa la metodología y que hoy no se citan:

- N. V. Chawla, K. W. Bowyer, L. O. Hall, and W. P. Kegelmeyer, "SMOTE: Synthetic minority over-sampling technique," *J. Artificial Intelligence Research*, vol. 16, pp. 321–357, 2002.
- F. Pedregosa et al., "Scikit-learn: Machine learning in Python," *J. Machine Learning Research*, vol. 12, pp. 2825–2830, 2011.
- G. Lemaître, F. Nogueira, and C. K. Aridas, "Imbalanced-learn: A Python toolbox to tackle the curse of imbalanced datasets in machine learning," *J. Machine Learning Research*, vol. 18, no. 17, pp. 1–5, 2017.
- Drain3, implementación en línea de Drain desarrollada originalmente por IBM y hoy mantenida por LogPAI: https://github.com/logpai/Drain3

✅ **Tabla V**, fila "Este trabajo": cambiar la representación a **"Conteo de eventos y TF-IDF"**.

---

## III. Metodología

Ajustes a cada paso de la lista:

1. ✅ **Obtención de datos.** Mencionar que el zip de Loghub incluye, además del log en bruto, la matriz de referencia que se usó para validar el parsing.
2. ✅ **Agregar un paso de "Parsing"** entre los pasos 1 y 2, o fusionarlo con el 2. Debe decir: Drain3, profundidad 4, similitud 0.7, enmascarado de bloques e IPs, y asignación de nombres E1–E29. La justificación va en I-D.
3. ✅ **Construcción de variables.** Agregar que las filas se ordenan por `BlockId`.
4. ✅ **Transformación.** Especificar la fórmula de TF-IDF, que hoy solo dice "como en Loglizer":
   > idf(e) = log(N / n_e), donde N es el número de bloques y n_e el número de bloques donde aparece el evento e. Después se centra cada columna restando su media. Ambos parámetros se ajustan solo con el conjunto de entrenamiento.
5. ✅ **Partición.** Agregar la justificación empírica de la validación cruzada:
   > Sobre la muestra, el recall del árbol de decisión varía entre 0.41 y 0.59 según la semilla de partición (10 semillas). Con 63 anomalías en el conjunto de prueba, un solo bloque cambia el recall en 0.016.
6. ✅ **Modelado.** Especificar que el Naive Bayes es **Gaussiano** (`GaussianNB`). Es el que reproduce la Tabla VI; el Multinomial da resultados distintos.
7. ✅ **Manejo del desbalance.** Precisar que SMOTE se aplica **dentro de cada fold** mediante `imblearn.pipeline.Pipeline`.
8. ⏳ **Ajuste y validación (Fase 3).** Agregar la grilla de hiperparámetros que se use para cada modelo.

✅ **Agregar una subsección "Prevención de fuga de datos"**:

> TF-IDF, el escalado y SMOTE se ajustan exclusivamente con los datos de entrenamiento de cada fold. El conjunto de prueba (115,013 bloques, 3,368 anómalos) se separa al inicio y se usa una sola vez, para la evaluación final.

### Resultados preliminares (Tabla VI y párrafos siguientes)

✅ **Agregar una nota de reproducibilidad** junto a la Tabla VI:

> Estos resultados se reprodujeron de forma exacta con el pipeline final (`src/reproduce_avance1.py`).

✏️ **Responder la hipótesis abierta.** El párrafo que dice *"Confirmar esta hipótesis requiere comparar directamente las predicciones de cada modelo…"* puede reemplazarse por:

> La comparación directa confirma la hipótesis: los cuatro modelos producen predicciones **idénticas bloque por bloque** sobre el conjunto de prueba, no solo métricas agregadas iguales. Las 32 anomalías no detectadas tienen todas E5 = 3, el mismo valor que un bloque normal. En la práctica, los cuatro modelos aprendieron la regla "si E5 ≠ 3, es anomalía".

✏️ **Párrafo de "trabajo futuro inmediato".** El punto (a), escalar al conjunto completo, ya se hizo. Moverlo a la sección de resultados y dejar solo el punto (b), representaciones secuenciales, para las conclusiones.

---

## IV. Resultados (sección nueva) ✅

Todas las cifras salen de `python src/evaluate.py` (archivos `artifacts/cv_results.csv` y `artifacts/test_metrics.csv`).

**Configuración experimental (texto):**

> Se separó el 20 % de los bloques como test (115,013 bloques, 3,368 anómalos) y no se usó hasta la evaluación final. Sobre los 460,048 bloques de entrenamiento se ajustaron las 16 configuraciones con GridSearchCV y validación cruzada estratificada de 5 folds, eligiendo los hiperparámetros por el F1 de la clase anómala. El mejor modelo se seleccionó por F1 en validación cruzada, no en test. El entrenamiento completo tomó 12 minutos en un equipo de 12 núcleos.

**Tabla de hiperparámetros explorados:**

| Modelo | Grilla | Mejor valor (conteo, class_weight) |
|---|---|---|
| Árbol de decisión | `max_depth` ∈ {5, 10, 20, ∞}, `min_samples_leaf` ∈ {1, 5, 20} | `max_depth=20`, `min_samples_leaf=1` |
| Random Forest | `n_estimators` ∈ {100, 300}, `max_depth` ∈ {10, 20, ∞} | `n_estimators=100`, `max_depth=20` |
| Regresión logística | `C` ∈ {0.01, 0.1, 1, 10, 100, 1000} | `C=1000` (meseta desde C=1) |
| Naive Bayes (Gaussiano) | `var_smoothing` ∈ {1e-9, 1e-7, 1e-5} | `1e-7` |

> Nota: en la primera corrida la regresión logística eligió C=10, el extremo de la grilla original {0.01…10}. Se amplió hasta 1000 y se confirmó que el F1 se estabiliza en 0.980 a partir de C=1.

**Tabla principal: resultados de las 16 configuraciones** (clase anómala, umbral 0.5)

| Modelo | Repr. | Desbalance | F1 CV (media ± desv.) | Precisión test | Recall test | F1 test | FP | FN |
|---|---|---|---|---|---|---|---|---|
| Árbol | TF-IDF | class_weight | **0.9984 ± 0.0006** | 0.9964 | 0.9982 | 0.9973 | 12 | 6 |
| RF | TF-IDF | SMOTE | 0.9984 ± 0.0005 | 0.9967 | 0.9997 | **0.9982** | 11 | 1 |
| Árbol | TF-IDF | SMOTE | 0.9984 ± 0.0005 | 0.9964 | 0.9979 | 0.9972 | 12 | 7 |
| Árbol | Conteo | class_weight | 0.9984 ± 0.0005 | 0.9964 | 0.9982 | 0.9973 | 12 | 6 |
| RF | Conteo | class_weight | 0.9983 ± 0.0006 | 0.9967 | 0.9997 | 0.9982 | 11 | 1 |
| RF | TF-IDF | class_weight | 0.9983 ± 0.0006 | 0.9962 | 0.9997 | 0.9979 | 13 | 1 |
| RF | Conteo | SMOTE | 0.9976 ± 0.0018 | 0.9941 | 0.9997 | 0.9969 | 20 | 1 |
| Árbol | Conteo | SMOTE | 0.9974 ± 0.0018 | 0.9938 | 0.9979 | 0.9959 | 21 | 7 |
| LR | Conteo | class_weight | 0.9802 ± 0.0009 | 0.9568 | 0.9997 | 0.9778 | 152 | 1 |
| LR | Conteo | SMOTE | 0.9801 ± 0.0009 | 0.9568 | 1.0000 | 0.9779 | 152 | 0 |
| LR | TF-IDF | class_weight | 0.9799 ± 0.0008 | 0.9563 | 1.0000 | 0.9776 | 154 | 0 |
| LR | TF-IDF | SMOTE | 0.9797 ± 0.0009 | 0.9568 | 0.9997 | 0.9778 | 152 | 1 |
| NB | (las 4 variantes) | | 0.9440 ± 0.0039 | 0.8875 | 1.0000 | 0.9404 | 427 | 0 |
| *Siempre «Normal»* | | | — | — | 0 | 0 | 0 | 3,368 |

**Mejor modelo según CV:** árbol de decisión (TF-IDF, class_weight, `max_depth=20`). Matriz de confusión en test:

| | Predice Normal | Predice Anomalía |
|---|---|---|
| **Real Normal** | 111,633 | 12 |
| **Real Anomalía** | 6 | 3,362 |

> ✏️ Ojo al redactar: las seis mejores configuraciones están empatadas dentro de una desviación estándar en CV (0.9983–0.9984 ± 0.0006). Elegir el árbol es correcto por el criterio fijado (mayor F1 medio en CV), pero conviene decir que árbol y Random Forest son estadísticamente equivalentes. En test, RF obtiene F1 0.9982 frente a 0.9973 del árbol.

**Análisis de umbral** (cuántos bloques revisar para atrapar cierto % de las anomalías del test):

| Mejor config. de cada modelo | Recall ≥ 95 % | Recall ≥ 99 % | Recall ≥ 99.9 % |
|---|---|---|---|
| Random Forest | 3,226 (2.80 %) | 3,349 (2.91 %) | **3,376 (2.94 %)**, precisión 0.997 |
| Árbol de decisión | 3,298 (2.87 %) | 3,369 (2.93 %) | 115,013 (100 %): no alcanzable |
| Regresión logística | 3,400 (2.96 %) | 3,499 (3.04 %) | 3,518 (3.06 %) |
| Naive Bayes | 3,795 (3.30 %) | 3,795 (3.30 %) | 3,795 (3.30 %) |

Texto sugerido:

> Aunque el árbol de decisión y Random Forest obtienen el mismo F1 con umbral 0.5, solo Random Forest permite ajustar el umbral con precisión. El árbol asigna probabilidades casi binarias (la pureza de cada hoja), por lo que no existe un umbral que alcance un recall de 99.9 % sin marcar todos los bloques. Random Forest, al promediar 100 árboles, produce probabilidades graduales: revisando solo el 2.94 % de los bloques se atrapa el 99.9 % de las anomalías, con precisión 0.997. Para el caso de uso planteado, priorizar la revisión humana, Random Forest es la opción recomendada.

**Hallazgos sobre el diseño experimental** (para el texto):

- **TF-IDF no afecta al árbol ni a Naive Bayes.** Obtienen métricas idénticas con conteo y con TF-IDF, porque TF-IDF es una transformación afín por columna. Los árboles solo dependen del orden de los valores, y GaussianNB ajusta media y varianza por columna. Solo afecta a la regresión logística: con TF-IDF necesita C ≥ 100 para igualar al conteo.
- **SMOTE no mejora frente a class_weight.** En el árbol y RF con conteos incluso aumenta los falsos positivos (de 12 a 21 y de 11 a 20), y es entre 1.5 y 9 veces más lento de entrenar.
- **Naive Bayes** obtiene recall perfecto pero 427 falsas alarmas. Una explicación probable es que su supuesto de independencia entre eventos no se cumple: E5, E9, E11 y E26 describen las mismas tres réplicas y tienden a variar juntos. ⏳ Verificar con la matriz de correlación en la Fase 4 antes de afirmarlo.

**Comparación con la literatura:** He et al. [2] reportan F1 > 0.99 con modelos supervisados sobre el mismo conjunto. Nuestros resultados (0.997–0.998) son consistentes con ese valor.

---

## V. Discusión (sección nueva)

Responder las tres preguntas del proyecto:

1. ✅ **¿El recall bajo se debía al truncamiento?** Sí. En la muestra, el 56.9 % de las anomalías era indistinguible de un bloque normal; en el conjunto completo, solo el 1.9 %. El mínimo de errores posibles pasa de 161 a 36 bloques. Con los mismos cuatro tipos de modelo, el recall sube de **0.492** (muestra) a **0.998** (árbol) y **0.9997** (RF) en el conjunto completo.
2. ✅ **¿Los modelos aprenden la misma regla?** En la muestra, sí: predicciones idénticas. En el conjunto completo, **no**. Desacuerdos en test entre la mejor configuración de cada modelo:

   | | Árbol | RF | LR | NB |
   |---|---|---|---|---|
   | Árbol | 0 | 6 | 149 | 421 |
   | RF | 6 | 0 | 143 | 417 |
   | LR | 149 | 143 | 0 | 276 |
   | NB | 421 | 417 | 276 | 0 |

   Los dos modelos de árboles convergen a casi la misma frontera (difieren en 6 bloques). Los modelos lineal y probabilístico se equivocan en otros bloques, casi siempre por exceso de falsos positivos.
3. ✅ **¿Cuántas anomalías son indistinguibles por conteo?** 319 de 16,838 (1.9 %). En el test hay 129 bloques con un vector que comparten ambas clases. **11 de los 18 errores** del mejor modelo caen en esos bloques: son errores inevitables para cualquier modelo basado solo en conteos. ⏳ En la Fase 4: analizar qué tipo de anomalías son y si el orden de los eventos (DeepLog) podría separarlas.

---

## VI. Interfaz LogWatch (sección nueva) ⏳ Fase 5

- Descripción breve: arquitectura (el pipeline exporta un JSON y una página HTML lo lee) y las seis pestañas.
- **Figura:** captura de la pestaña *Umbral*, que es la que mejor muestra el compromiso entre precisión y recall.
- Vincular con la motivación de la Sección I-A: la interfaz materializa la idea de priorizar la revisión humana.

---

## VII. Conclusiones y trabajo futuro (sección nueva) ⏳ Fase 4

- Resumen de hallazgos: el parsing validado, la hipótesis del truncamiento confirmada y el mejor modelo.
- Limitación principal: el 1.9 % de las anomalías es indistinguible por conteo.
- Trabajo futuro: representaciones secuenciales (DeepLog [6], LogRobust [7]) y partición cronológica en lugar de aleatoria, como sugieren Le y Zhang [8].
- Agregar una nota de disponibilidad del código: un enlace al repositorio, si lo van a publicar.
