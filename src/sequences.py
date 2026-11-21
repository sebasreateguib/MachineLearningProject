"""Fase 4 · Variables de orden: pares de eventos consecutivos (bigramas).

El conteo de eventos descarta el orden en que ocurren. Este script reconstruye la
secuencia de eventos de cada bloque (con el orden de las líneas en HDFS.log, guardado
por src/parse.py) y cuenta cuántas veces aparece cada par consecutivo:

    secuencia de un bloque:  E22 E5 E5 E5 E26 E9 ...
    bigramas:                E22>E5, E5>E5, E5>E5, E5>E26, E26>E9, ...

Es una forma simple de incorporar el orden, en la línea de DeepLog, pero sin redes
neuronales. Se usa como alternativa de mejora en src/analysis.py.

Salida:
    data/processed/full_bigrams.parquet   bloques × bigramas observados (mismo orden que la matriz)

Uso:
    python src/sequences.py
"""
import numpy as np
import pandas as pd

from config import PROCESSED
from features import event_sort_key, load_matrix

OUT = PROCESSED / "full_bigrams.parquet"


def build_bigrams() -> pd.DataFrame:
    pairs = pd.read_parquet(PROCESSED / "full_pairs.parquet")
    tpl = pd.read_csv(PROCESSED / "full_templates.csv")
    events = sorted(tpl["EventId"].unique(), key=event_sort_key)
    code = {e: i for i, e in enumerate(events)}
    ev = pairs["ClusterId"].map(dict(zip(tpl["ClusterId"], tpl["EventId"]))).map(code).to_numpy()

    # ordenar por bloque y, dentro de cada bloque, por línea del log
    blk = pairs["BlockId"].cat.codes.to_numpy()
    order = np.lexsort((pairs["LineId"].to_numpy(), blk))
    blk, ev = blk[order], ev[order]

    same = blk[1:] == blk[:-1]                       # pares consecutivos del mismo bloque
    pair_code = ev[:-1][same] * len(events) + ev[1:][same]
    pair_blk = blk[1:][same]

    df = pd.DataFrame({"b": pair_blk, "p": pair_code}).value_counts().rename("n").reset_index()
    wide = df.pivot(index="b", columns="p", values="n").fillna(0).astype("int32")
    wide.index = pairs["BlockId"].cat.categories[wide.index]
    wide.columns = [f"{events[c // len(events)]}>{events[c % len(events)]}" for c in wide.columns]
    return wide


def main() -> None:
    X, _ = load_matrix("full")
    bi = build_bigrams().reindex(X.index, fill_value=0)   # mismo orden de filas que la matriz de conteo
    bi.index.name = "BlockId"
    bi.to_parquet(OUT)
    print(f"{bi.shape[1]} bigramas distintos observados (de {29 * 29} posibles) · {len(bi):,} bloques")
    print(f"Guardado en {OUT.relative_to(PROCESSED.parent.parent)}")


if __name__ == "__main__":
    main()
