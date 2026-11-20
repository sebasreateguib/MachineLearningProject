# Detección de Anomalías en Logs de HDFS

Proyecto final del curso de **Machine Learning** (UTEC, 2026), dictado por el profesor Victor Martinez Abaunza.

**Integrantes:** Gerard Deker Iruri Espinoza · Sebastian Reategui Bellido · Mijail Saltsin Navarro

---

## 1. De qué trata

Los sistemas distribuidos como HDFS (Hadoop Distributed File System) generan millones de líneas de log al día. Revisarlas a mano es inviable, y no revisarlas significa que fallas reales (pérdida de datos, replicación incompleta, bloques corruptos) pueden pasar desapercibidas.

Este proyecto plantea la detección de anomalías como un problema de **clasificación binaria supervisada**: a partir de los eventos registrados en los logs de cada bloque de datos, el modelo predice si ese bloque es **Normal** o **Anomalía**.

El objetivo no es reemplazar la revisión humana, sino **priorizarla**: en lugar de examinar cientos de miles de bloques, el equipo de operaciones revisa solo los que el modelo marca como sospechosos.

El planteamiento completo, el estado del arte y los resultados preliminares están en [`Informe-IEEE-Transactions.pdf`](Informe-IEEE-Transactions.pdf) (Avance 1).

## 2. Objetivos

**General:** desarrollar un modelo de clasificación binaria que identifique automáticamente bloques con comportamiento anómalo en los logs de HDFS.

**Específicos:**

1. Preprocesar los logs no estructurados con **Drain** y construir una **matriz de conteo de eventos** por bloque.
2. Caracterizar la distribución de clases y la relevancia de cada tipo de evento mediante análisis exploratorio (EDA).
3. Implementar y comparar al menos dos clasificadores con métricas adecuadas para datos desbalanceados (precisión, recall, F1), no solo accuracy.
4. Analizar las limitaciones del enfoque basado en conteo y proponer mejoras.
5. Presentar los resultados en una **interfaz interactiva** (*LogWatch*).

## 3. Datos

| | Muestra (Loglizer) | Dataset completo (Loghub HDFS_v1) |
|---|---|---|
| Uso | Validar el pipeline | Entrenamiento y evaluación final |
| Tamaño | 104,815 líneas · 7,940 bloques | 11,175,629 líneas · 575,061 bloques · 1.47 GiB |
| Formato | Ya parseado con Drain | Texto en bruto, hay que parsearlo |
| Anomalías | 313 (3.94 %) | 16,838 (2.93 %) |
| Fuente | [logpai/loglizer](https://github.com/logpai/loglizer) → `data/HDFS` | [Zenodo 8196385](https://zenodo.org/records/8196385) |

Las etiquetas (`anomaly_label.csv`) fueron asignadas por expertos al construir el dataset; el proyecto no las modifica, solo las une por `BlockId`.

> Los datos **no se suben al repositorio** (pesan demasiado). El script de descarga los deja en `data/raw/`.

## 4. Metodología

El pipeline sigue las 8 etapas definidas en la Sección III del informe:

| # | Etapa | Qué se hace | Script |
|---|---|---|---|
| 1 | **Obtención de datos** | Descargar la muestra de Loglizer y los logs en bruto de Loghub | `src/download.py` |
| 2 | **Parsing** | Aplicar Drain a los logs en bruto, nombrar cada cluster con su `EventId` de Loghub y validar contra la matriz oficial | `src/parse.py`, `src/validate_parse.py` |
| 3 | **Construcción de variables** | Extraer el `BlockId` con una expresión regular y construir la matriz de conteo **X ∈ ℕⁿˣᵐ** (bloques × tipos de evento), unida a las etiquetas | `src/features.py` |
| 4 | **Transformación** | Comparar conteos crudos contra **TF-IDF + normalización** (como en Loglizer) | `src/features.py` |
| 5 | **Partición** | Train/test **80/20 estratificado**, `random_state=42` | `src/train.py` |
| 6 | **Modelado** | Árbol de decisión, Random Forest, Regresión logística y Naive Bayes | `src/train.py` |
| 7 | **Manejo del desbalance** | `class_weight='balanced'` (árbol, RF, LR); ajuste de *priors* (NB); comparación con **SMOTE** | `src/train.py` |
| 8 | **Ajuste y evaluación** | `GridSearchCV` con CV estratificada de 5 particiones, seleccionando por **F1 de la clase anómala**. Reporte de precisión, recall, F1, matriz de confusión y curva precisión–recall en test | `src/evaluate.py` |

### Diseño experimental

Se entrenan **4 modelos × 2 representaciones × 2 estrategias de desbalance = 16 configuraciones**:

- **Modelos:** Árbol de decisión · Random Forest · Regresión logística · Naive Bayes
- **Representación:** Conteo crudo · TF-IDF
- **Desbalance:** `class_weight` / priors · SMOTE

### Cuidados para evitar fuga de datos (*data leakage*)

- TF-IDF y cualquier escalado se ajustan **solo con el conjunto de entrenamiento**.
- SMOTE se aplica **dentro de cada fold** de la validación cruzada (con `imblearn.pipeline.Pipeline`), nunca sobre el test.
- El conjunto de test se usa una sola vez, al final.

### Preguntas que el proyecto debe responder

Vienen de los resultados preliminares del Avance 1, donde los 4 modelos obtuvieron métricas idénticas (precisión 1.00, recall 0.49) sobre la muestra:

1. ¿El recall bajo se debía al **truncamiento de la muestra**? Se espera que mejore mucho con el dataset completo (He et al. reportan F1 > 0.99).
2. ¿Los modelos aprenden **la misma regla**? Se comparan sus predicciones bloque por bloque, no solo las métricas agregadas.
3. ¿Cuántas anomalías son **indistinguibles por conteo**, es decir, tienen el mismo vector que bloques normales (caso B1/B2/B3 del informe)? Esto cuantifica el límite del enfoque.

## 5. Interfaz: *LogWatch*

Los resultados se presentan en una página web interactiva. El diseño ya está definido en [`UI/mockup.html`](UI/mockup.html), que usa datos simulados.

**Arquitectura:** el pipeline en Python exporta los resultados a un archivo JSON y la página (HTML + JavaScript, sin servidor) solo lo lee. Nada se entrena en el navegador.

```
pipeline Python  ──►  UI/data/resultados.json  ──►  UI/index.html
```

| Pestaña | Pregunta que responde | Datos que necesita del pipeline |
|---|---|---|
| Resumen | ¿Qué tan bien funciona el sistema? | Métricas de cada configuración |
| Modelos | ¿Qué modelo y qué variante funcionan mejor? | Métricas y matrices de confusión de las 16 configuraciones |
| Umbral | ¿Cuántas alertas acepto a cambio de cuántas anomalías atrapadas? | Histogramas de probabilidad por clase (en bins) y curvas precisión–recall |
| Triage | ¿Qué bloques revisaría primero el equipo de operaciones? | Muestra de bloques de test con su vector de eventos, etiqueta y probabilidad por modelo |
| Simulador | ¿Cómo reacciona el modelo si cambio los eventos de un bloque? | Modelos exportados a JSON (coeficientes de LR, estructura de los árboles) para evaluarlos en el navegador |
| Datos | ¿Cómo son los datos y qué eventos importan? | Distribución de clases, frecuencias por clase, importancia de variables |

Para que el JSON no sea enorme, se exportan histogramas y curvas ya agregados (no las 115k predicciones individuales), y solo una muestra de bloques para la bandeja de triage.

## 6. Estructura del repositorio

```
Proyecto/
├── README.md
├── requirements.txt
├── Informe-IEEE-Transactions.pdf
├── data/                     # no se versiona
│   ├── raw/                  # HDFS.log, anomaly_label.csv, muestra de Loglizer
│   └── processed/            # caché: full_pairs.parquet, full_templates.csv, *_matrix.parquet
├── src/
│   ├── config.py             # rutas y constantes (semilla, % de test)
│   ├── download.py           # 1. descarga de datos
│   ├── reproduce_avance1.py  # Fase 1: verifica las cifras del Avance 1
│   ├── parse.py              # 2. parsing con Drain
│   ├── validate_parse.py     # Fase 2: compara la matriz con la oficial de Loghub
│   ├── features.py           # 3–4. BlockId, matriz de conteo, TF-IDF
│   ├── train.py              # 5–7. partición, modelos, desbalance, GridSearchCV
│   ├── evaluate.py           # 8. métricas, matriz de confusión, curvas
│   └── export.py             # genera UI/data/resultados.json
├── notebooks/
│   └── eda.ipynb             # análisis exploratorio y figuras para el informe
├── artifacts/                # modelos entrenados (.joblib) y métricas
└── UI/
    ├── mockup.html           # diseño de referencia con datos simulados
    ├── index.html            # interfaz final
    └── data/resultados.json  # generado por src/export.py
```

## 7. Cómo ejecutarlo (planeado)

```bash
# Entorno
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Fase 1: validar el pipeline con la muestra
python src/download.py
python src/features.py
python src/reproduce_avance1.py

# Pipeline completo
python src/download.py --full     # descarga muestra + HDFS_v1
python src/parse.py               # Drain sobre los logs en bruto (~1 min)
python src/features.py --source full   # matriz de conteo 575,061 × 29
python src/validate_parse.py      # compara con la matriz oficial de Loghub
python src/train.py               # 16 configuraciones con GridSearchCV
python src/evaluate.py            # métricas en test
python src/export.py              # genera UI/data/resultados.json

# Interfaz
open UI/index.html
```

Cada paso guarda su salida en `data/processed/` o `artifacts/`, así que si algo falla no hay que repetir los pasos anteriores (en especial el parsing).

**Dependencias principales:** Python 3.10+, pandas, numpy, scikit-learn, imbalanced-learn, drain3, joblib, matplotlib.

## 8. Plan de trabajo

- [x] **Fase 1 · Pipeline sobre la muestra:** reproducir los resultados del Avance 1 para validar que el código funciona. `python src/reproduce_avance1.py` → 24/24 cifras coinciden (Tabla IV, Figura 2, Tabla VI).
  - Las filas deben ir ordenadas por `BlockId`; con otro orden, la partición con `random_state=42` cambia.
  - Los 4 modelos dan **predicciones idénticas** bloque por bloque, no solo las mismas métricas.
  - Las 32 anomalías de test no detectadas tienen **E5 = 3**, el mismo valor que un bloque normal.
  - El **56.9 %** de las anomalías de la muestra tiene exactamente el mismo vector que algún bloque normal.
  - Con otras semillas, el recall del árbol varía entre 0.41 y 0.59, así que hace falta validación cruzada.
- [x] **Fase 2 · Dataset completo:** descargar HDFS_v1, aplicar Drain y construir la matriz de 575,061 bloques.
  - Drain3 (profundidad 4, **similitud 0.7**) parsea las 11,175,629 líneas en ~1 min y produce 49 clusters. A cada cluster se le asigna el EventId de Loghub (E1–E29) cuya plantilla coincide; todos quedan con nombre.
  - Con la similitud 0.5 de Loghub, Drain **fusiona E8** (*Interrupted*, falla) **con E11** (*terminating*, cierre normal). Por eso se usa 0.7.
  - `python src/validate_parse.py`: nuestra matriz coincide con `Event_occurrence_matrix.csv` de Loghub en el **100 %** de los bloques, eventos y etiquetas.
  - En el dataset completo solo el **1.9 %** de las anomalías tiene el mismo vector que un bloque normal (56.9 % en la muestra). Cualquier clasificador por conteo puede equivocarse, como mínimo, en **36 de 575,061 bloques**. Esto confirma que el recall bajo del Avance 1 se debía al truncamiento de la muestra.
- [x] **Fase 3 · Experimentos:** entrenar las 16 configuraciones con GridSearchCV y evaluar en test. `python src/train.py` (~12 min) y `python src/evaluate.py`.
  - **Árbol y Random Forest: F1 ≈ 0.998** en CV y test. Regresión logística: 0.978. Naive Bayes: 0.940. Línea base «siempre Normal»: F1 0.
  - Mejor según CV: árbol de decisión (TF-IDF, class_weight, `max_depth=20`), con test F1 0.9973 (12 FP, 6 FN). Las 6 mejores configuraciones están empatadas dentro de una desviación estándar.
  - **Random Forest atrapa el 99.9 % de las anomalías revisando solo el 2.94 % de los bloques** (precisión 0.997). El árbol, en cambio, da probabilidades escalonadas y no permite ese ajuste fino del umbral.
  - TF-IDF no cambia nada en árbol ni Naive Bayes (son invariantes a transformaciones por columna). SMOTE no mejora frente a `class_weight` y es más lento.
  - A diferencia de la muestra, los modelos **no** aprenden la misma regla: árbol y RF difieren en 6 bloques, pero LR y NB difieren en 140–420.
  - De los 18 errores del mejor modelo, 11 están en vectores que comparten ambas clases (inevitables por conteo).
- [ ] **Fase 4 · Análisis:** comparar predicciones entre modelos, cuantificar las anomalías indistinguibles por conteo y redactar conclusiones.
- [ ] **Fase 5 · Interfaz:** exportar `resultados.json` y conectar *LogWatch* con los datos reales.
- [ ] **Fase 6 · Informe final:** actualizar el informe IEEE con los resultados.
- [ ] *(Opcional)* Explorar representaciones secuenciales (DeepLog, LogRobust) como trabajo futuro.

## 9. Referencias principales

- J. Zhu et al., "Loghub: A large collection of system log datasets for AI-driven log analytics," *ISSRE*, 2023.
- S. He et al., "Experience report: System log analysis for anomaly detection," *ISSRE*, 2016.
- P. He et al., "Drain: An online log parsing approach with fixed depth tree," *ICWS*, 2017.
- W. Xu et al., "Detecting large-scale system problems by mining console logs," *SOSP*, 2009.
- M. Du et al., "DeepLog: Anomaly detection and diagnosis from system logs through deep learning," *CCS*, 2017.

La lista completa está en el informe.
