"""Etapas 3–4 · Construcción de variables y transformación.

Convierte los logs parseados (una fila por línea, con su EventId) en una matriz de
conteo de eventos por bloque, unida a las etiquetas:

            E1  E2  E3 ... E29   Label
    blk_A    0   0   1 ...   0       0
    blk_B    0   0   0 ...   2       1

Uso:
    python src/features.py                 # muestra de Loglizer
    python src/features.py --source full   # dataset completo (requiere src/parse.py)
"""
import argparse
import re

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from config import BLOCK_ID_REGEX, PROCESSED, SAMPLE_LABELS, SAMPLE_STRUCTURED, FULL_DIR

SOURCES = {
    # muestra: CSV de Loglizer, una fila por línea con Content y EventId
    "sample": {"structured": SAMPLE_STRUCTURED, "labels": SAMPLE_LABELS},
    # completo: salida de src/parse.py, una fila por (línea, bloque) con el cluster de Drain
    "full": {"structured": PROCESSED / "full_pairs.parquet", "templates": PROCESSED / "full_templates.csv",
             "labels": FULL_DIR / "preprocessed" / "anomaly_label.csv"},
}


def matrix_path(source: str):
    return PROCESSED / f"{source}_matrix.parquet"


def event_sort_key(event_id: str) -> int:
    """E2 < E10 (orden numérico, no alfabético)."""
    m = re.search(r"\d+", event_id)
    return int(m.group()) if m else 10**9


def block_event_counts(structured: pd.DataFrame) -> pd.DataFrame:
    """Cuenta cuántas veces aparece cada EventId en las líneas de cada bloque.

    Una línea puede mencionar más de un bloque (p. ej. eliminaciones en lote); en ese
    caso el evento se cuenta una vez para cada bloque mencionado, igual que en Loglizer.

    Las filas quedan ordenadas por BlockId (orden por defecto de pandas al agrupar). Este
    orden importa: train_test_split con random_state=42 depende del orden de las filas, y
    es el que reproduce exactamente la Tabla VI y la Figura 2 del Avance 1.
    """
    ids = structured["Content"].str.findall(BLOCK_ID_REGEX).map(lambda xs: list(dict.fromkeys(xs)))
    pairs = pd.DataFrame({"BlockId": ids, "EventId": structured["EventId"].values})
    pairs = pairs.explode("BlockId").dropna(subset=["BlockId"])
    counts = pd.crosstab(pairs["BlockId"], pairs["EventId"]).sort_index()
    counts = counts[sorted(counts.columns, key=event_sort_key)]
    counts.columns.name = None
    counts.index.name = "BlockId"
    return counts


def full_event_counts(pairs_path, templates_path) -> pd.DataFrame:
    """Matriz de conteo a partir de la salida de parse.py (cluster de Drain → EventId)."""
    pairs = pd.read_parquet(pairs_path, columns=["BlockId", "ClusterId"])
    tpl = pd.read_csv(templates_path)
    pairs["EventId"] = pairs["ClusterId"].map(dict(zip(tpl["ClusterId"], tpl["EventId"]))).astype("category")
    counts = pairs.groupby(["BlockId", "EventId"], observed=True).size().unstack(fill_value=0)
    counts.index = counts.index.astype(str)
    counts = counts.sort_index()
    counts = counts[sorted(counts.columns, key=event_sort_key)].astype("int32")
    counts.columns = counts.columns.astype(str)
    counts.columns.name = None
    counts.index.name = "BlockId"
    return counts


def attach_labels(counts: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    """Agrega la columna Label (1 = Anomaly, 0 = Normal). Falla si algún bloque no tiene etiqueta."""
    lab = labels.set_index("BlockId")["Label"].reindex(counts.index)
    missing = lab.isna().sum()
    if missing:
        raise ValueError(f"{missing} bloques no tienen etiqueta en anomaly_label.csv")
    out = counts.copy()
    out["Label"] = (lab == "Anomaly").astype(int).values
    return out


def load_matrix(source: str = "sample"):
    """Devuelve (X, y) desde la matriz ya construida."""
    df = pd.read_parquet(matrix_path(source))
    return df.drop(columns="Label"), df["Label"]


class TfidfTransformer(BaseEstimator, TransformerMixin):
    """Ponderación TF-IDF + centrado, como `FeatureExtractor(term_weighting='tf-idf',
    normalization='zero-mean')` de Loglizer.

    idf(evento) = log(N / nº de bloques donde aparece). Se ajusta solo con los datos de
    entrenamiento (fit) para no filtrar información del test.
    """

    def fit(self, X, y=None):
        X = np.asarray(X, dtype=float)
        df = np.maximum((X > 0).sum(axis=0), 1)
        self.idf_ = np.log(X.shape[0] / df)
        self.mean_ = (X * self.idf_).mean(axis=0)
        return self

    def transform(self, X):
        return np.asarray(X, dtype=float) * self.idf_ - self.mean_


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=SOURCES, default="sample")
    args = ap.parse_args()
    src = SOURCES[args.source]
    if not src["structured"].exists():
        hint = "python src/download.py" if args.source == "sample" else "python src/download.py --full && python src/parse.py"
        raise SystemExit(f"No existe {src['structured']}. Ejecuta primero: {hint}")

    print(f"Leyendo {src['structured'].name} ...")
    if args.source == "sample":
        structured = pd.read_csv(src["structured"], usecols=["Content", "EventId"], dtype=str)
        has_block = structured["Content"].str.contains(BLOCK_ID_REGEX, regex=True)
        print(f"  {len(structured):,} líneas · {(~has_block).sum():,} sin BlockId")
        counts = block_event_counts(structured)
    else:
        counts = full_event_counts(src["structured"], src["templates"])
    labels = pd.read_csv(src["labels"], dtype=str)
    matrix = attach_labels(counts, labels)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = matrix_path(args.source)
    matrix.to_parquet(out)
    n, a = len(matrix), int(matrix["Label"].sum())
    print(f"  matriz {n:,} bloques × {matrix.shape[1] - 1} eventos · {a:,} anomalías ({a / n:.2%})")
    print(f"  guardada en {out.relative_to(PROCESSED.parent.parent)}")


if __name__ == "__main__":
    main()
