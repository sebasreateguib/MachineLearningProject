"""Fase 2 · Valida nuestro parsing contra la matriz oficial de Loghub.

HDFS_v1 incluye `preprocessed/Event_occurrence_matrix.csv`, la matriz de conteo que
publicó Loghub. Si nuestro Drain + extracción de BlockId es correcto, ambas matrices
deberían coincidir bloque por bloque.

Uso:
    python src/validate_parse.py
"""
import pandas as pd

from config import FULL_DIR
from features import load_matrix

LOGHUB_MATRIX = FULL_DIR / "preprocessed" / "Event_occurrence_matrix.csv"


def main() -> None:
    X, y = load_matrix("full")
    ref = pd.read_csv(LOGHUB_MATRIX).set_index("BlockId")
    ev = [c for c in ref.columns if c.startswith("E")]
    ref_y = (ref["Label"] != "Success").astype(int)

    print(f"Nuestra matriz: {X.shape[0]:,} bloques × {X.shape[1]} eventos · {int(y.sum()):,} anomalías ({y.mean():.2%})")
    print(f"Loghub:         {ref.shape[0]:,} bloques × {len(ev)} eventos · {int(ref_y.sum()):,} anomalías ({ref_y.mean():.2%})")

    only_ours, only_ref = X.index.difference(ref.index), ref.index.difference(X.index)
    print(f"\nBloques solo en la nuestra: {len(only_ours):,} · solo en Loghub: {len(only_ref):,}")

    common = X.index.intersection(ref.index)
    A = X.reindex(columns=ev, fill_value=0).loc[common]
    B = ref.loc[common, ev]
    same_row = (A.values == B.values).all(axis=1)
    print(f"Bloques con vector idéntico: {same_row.sum():,} de {len(common):,} ({same_row.mean():.4%})")
    print(f"Etiquetas iguales:           {(y.loc[common] == ref_y.loc[common]).mean():.4%}")

    diff = (A - B)
    per_event = pd.DataFrame({"nuestro": A.sum(), "loghub": B.sum(), "bloques distintos": (diff != 0).sum()})
    per_event = per_event[per_event["bloques distintos"] > 0]
    if len(per_event):
        print("\nEventos con diferencias:")
        print(per_event.to_string())
    else:
        print("\nTodos los eventos coinciden en todos los bloques.")


if __name__ == "__main__":
    main()
