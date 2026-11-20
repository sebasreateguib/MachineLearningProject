"""Etapa 8 · Evaluación final sobre el conjunto de test.

Es el único script que usa el conjunto de test (115,013 bloques). Carga los modelos
entrenados por src/train.py y calcula:

  1. Métricas de la clase anómala con umbral 0.5 para las 16 configuraciones.
  2. El mejor modelo, elegido por F1 en validación cruzada (no en test).
  3. Análisis de umbral del mejor modelo: cuántos bloques revisar para atrapar
     el 95 / 99 / 99.9 % de las anomalías.
  4. ¿Los modelos aprenden la misma regla? Desacuerdos entre la mejor configuración
     de cada familia, bloque por bloque.
  5. Errores del mejor modelo que son inevitables por conteo (vector idéntico a
     bloques de la otra clase).

Salidas (en artifacts/):
    test_metrics.csv           métricas en test de cada configuración
    test_predictions.parquet   probabilidad de anomalía de cada bloque de test, por configuración

Uso:
    python src/evaluate.py
"""
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix, f1_score,
                             precision_recall_curve, precision_score, recall_score)

from config import ARTIFACTS, MODELS_DIR
from features import load_matrix, load_split

NAMES = {"nb": "Naive Bayes", "lr": "Regresión logística", "dt": "Árbol de decisión", "rf": "Random Forest"}


def metrics(y, prob, thr=0.5) -> dict:
    p = (prob >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, p, labels=[0, 1]).ravel()
    return {"accuracy": accuracy_score(y, p), "precision": precision_score(y, p, zero_division=0),
            "recall": recall_score(y, p), "f1": f1_score(y, p), "ap": average_precision_score(y, prob),
            "tn": tn, "fp": fp, "fn": fn, "tp": tp}


def section(title):
    print(f"\n{title}\n" + "─" * len(title))


def main() -> None:
    cv = pd.read_csv(ARTIFACTS / "cv_results.csv").set_index("config")
    _, X_te, _, y_te = load_split("full")
    y = y_te.values
    print(f"Test: {len(y):,} bloques · {int(y.sum()):,} anomalías · {len(cv)} configuraciones entrenadas")

    probs, rows = {}, []
    for cid in cv.index:
        model = joblib.load(MODELS_DIR / f"{cid}.joblib")
        probs[cid] = model.predict_proba(X_te.values)[:, 1]
        rows.append({"config": cid, **metrics(y, probs[cid])})
    res = pd.DataFrame(rows).set_index("config")
    res = res.join(cv[["model", "rep", "bal", "f1_mean", "f1_std", "best_params"]].rename(
        columns={"f1_mean": "cv_f1_mean", "f1_std": "cv_f1_std"}))
    res = res.sort_values("cv_f1_mean", ascending=False)
    res.to_csv(ARTIFACTS / "test_metrics.csv")

    pred = pd.DataFrame(probs, index=X_te.index).astype("float32")
    pred.insert(0, "Label", y_te)
    pred.to_parquet(ARTIFACTS / "test_predictions.parquet")

    section("1 · Métricas en test (clase anómala, umbral 0.5), ordenadas por F1 en CV")
    show = res[["cv_f1_mean", "cv_f1_std", "accuracy", "precision", "recall", "f1", "ap", "fp", "fn"]]
    with pd.option_context("display.width", 200, "display.float_format", "{:.4f}".format):
        print(show.to_string())
    print(f"\n  Línea base «siempre Normal»: accuracy {1 - y.mean():.4f} · recall 0 · F1 0")

    best = res.index[0]
    b = res.loc[best]
    section(f"2 · Mejor configuración según CV: {best}")
    print(f"  {NAMES[b['model']]} · {b['rep']} · {b['bal']} · hiperparámetros {b['best_params']}")
    print(f"  CV F1 {b['cv_f1_mean']:.4f} ± {b['cv_f1_std']:.4f}  →  test F1 {b['f1']:.4f} "
          f"(precisión {b['precision']:.4f}, recall {b['recall']:.4f})")
    print(f"  Matriz de confusión:  TN {b['tn']:,}  FP {b['fp']:,}  /  FN {b['fn']:,}  TP {b['tp']:,}")

    per_model = res.reset_index().groupby("model").first().set_index("config")

    section("3 · Análisis de umbral (mejor configuración de cada modelo)")
    print("  Bloques que habría que revisar para atrapar cierto % de las anomalías del test")
    print(f"  {'config':<16}" + "".join(f"{'recall ≥ ' + format(t, '.1%'):>30}" for t in (0.95, 0.99, 0.999)))
    for cid in per_model.index:
        prec, rec, thr = precision_recall_curve(y, probs[cid])
        cells = []
        for target in (0.95, 0.99, 0.999):
            i = np.where(rec[:-1] >= target)[0][-1]  # el umbral más alto que aún alcanza el recall objetivo
            flagged = int((probs[cid] >= thr[i]).sum())
            cells.append(f"{flagged:>8,} ({flagged / len(y):6.2%}) P={prec[i]:.3f}")
        print(f"  {cid:<16}" + "".join(f"{c:>30}" for c in cells))

    section("4 · ¿Los modelos aprenden la misma regla? (mejor configuración de cada modelo)")
    preds = {cid: (probs[cid] >= 0.5).astype(int) for cid in per_model.index}
    cids = list(preds)
    print("  " + " " * 20 + "".join(f"{c:>18}" for c in cids))
    for a in cids:
        print(f"  {a:<20}" + "".join(f"{int((preds[a] != preds[c]).sum()):>18,}" for c in cids))
    print("  (número de bloques de test en que dos modelos dan predicciones distintas)")

    section("5 · Errores del mejor modelo que son inevitables por conteo")
    X, yy = load_matrix("full")
    key = pd.util.hash_pandas_object(X, index=False)
    mixed = pd.DataFrame({"k": key, "y": yy}).groupby("k")["y"].nunique()
    ambiguous = key.isin(mixed[mixed > 1].index)
    p_best = preds.get(best, (probs[best] >= 0.5).astype(int))
    err = pd.Series(p_best != y, index=X_te.index)
    amb_te = ambiguous.loc[X_te.index]
    print(f"  Errores del mejor modelo: {int(err.sum())} · de ellos en vectores compartidos por ambas clases: "
          f"{int((err & amb_te).sum())}")
    print(f"  Bloques de test con vector compartido por ambas clases: {int(amb_te.sum()):,}")


if __name__ == "__main__":
    main()
