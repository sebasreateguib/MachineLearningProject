"""Fase 1 · Reproduce los resultados del Avance 1 sobre la muestra de Loglizer.

Compara cada cifra del informe con lo que calcula el pipeline y marca ✓ / ✗.
Sirve para confirmar que el código hace lo mismo que el análisis original antes
de pasar al dataset completo.

Uso:
    python src/reproduce_avance1.py
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier

from config import SEED, TEST_SIZE
from features import load_matrix

OK, BAD = "✓", "✗"


def check(name, got, expected, tol=0.0):
    ok = abs(got - expected) <= tol if isinstance(expected, (int, float)) else got == expected
    print(f"  {OK if ok else BAD} {name:<44} obtenido {got!s:<10} informe {expected}")
    return ok


def section(title):
    print(f"\n{title}\n" + "─" * len(title))


def main() -> None:
    X, y = load_matrix("sample")
    results = []

    section("Sección I-D · Datos")
    results += [
        check("bloques", len(X), 7940),
        check("tipos de evento en la muestra", X.shape[1], 19),
        check("bloques anómalos", int(y.sum()), 313),
        check("% anomalías", round(y.mean() * 100, 2), 3.94),
        check("accuracy de predecir siempre Normal (%)", round((1 - y.mean()) * 100, 1), 96.1),
    ]

    section("Tabla IV · Frecuencia promedio por clase")
    means = X.groupby(y).mean().T.rename(columns={0: "Normal", 1: "Anomaly"})
    tabla4 = {"E9": (3.000, 1.818), "E11": (3.000, 1.831), "E26": (3.001, 1.888),
              "E3": (0.027, 0.649), "E5": (3.001, 2.495), "E7": (0.000, 0.217)}
    for ev, (n, a) in tabla4.items():
        results.append(check(f"{ev} Normal", round(means.loc[ev, "Normal"], 3), n, 0.0015))
        results.append(check(f"{ev} Anomaly", round(means.loc[ev, "Anomaly"], 3), a, 0.0015))

    section("Tabla III · Bloques con el mismo vector y distinta etiqueta (caso B1/B2/B3)")
    key = X.astype(str).agg("|".join, axis=1)
    normal_vectors = set(key[y == 0])
    ambiguous = (y == 1) & key.isin(normal_vectors)
    print(f"  {int(ambiguous.sum())} de {int(y.sum())} anomalías ({ambiguous.sum() / y.sum():.1%}) tienen "
          f"exactamente el mismo vector que algún bloque normal.")
    print("  Ningún clasificador basado solo en conteos puede separarlas de esos bloques normales.")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=TEST_SIZE, stratify=y, random_state=SEED)

    section("Figura 2 · Importancia de variables (árbol, profundidad 3)")
    tree = DecisionTreeClassifier(max_depth=3, random_state=SEED).fit(X_tr, y_tr)
    imp = pd.Series(tree.feature_importances_, index=X.columns).sort_values(ascending=False)
    for ev, v in imp[imp > 0].items():
        print(f"    {ev:<4} {v:6.1%}")
    results += [
        check("E5 (%)", round(imp["E5"] * 100, 1), 93.4, 0.5),
        check("E13 (%)", round(imp.get("E13", 0) * 100, 1), 6.0, 0.5),
        check("E26 (%)", round(imp.get("E26", 0) * 100, 1), 0.6, 0.5),
    ]

    section("Tabla VI · Comparación preliminar de modelos (test 20 %, seed 42)")
    print(f"  train {len(X_tr):,} bloques ({int(y_tr.sum())} anomalías) · test {len(X_te):,} ({int(y_te.sum())} anomalías)")
    models = {
        "Árbol de decisión": DecisionTreeClassifier(random_state=SEED),
        "Random Forest": RandomForestClassifier(random_state=SEED, n_jobs=-1),
        "Regresión logística": LogisticRegression(max_iter=1000),
        "Naive Bayes": GaussianNB(),
    }
    expected = dict(acc=0.980, prec=1.000, rec=0.492, f1=0.660)
    preds = {}
    print(f"\n  {'Modelo':<27}{'Acc.':>7}{'Prec.':>7}{'Rec.':>7}{'F1':>7}")
    for name, model in models.items():
        p = model.fit(X_tr, y_tr).predict(X_te)
        preds[name] = p
        m = dict(acc=accuracy_score(y_te, p), prec=precision_score(y_te, p, zero_division=0),
                 rec=recall_score(y_te, p), f1=f1_score(y_te, p))
        match = all(abs(m[k] - expected[k]) <= 0.0015 for k in m)
        results.append(match)
        print(f"  {OK if match else BAD} {name:<25}" + "".join(f"{m[k]:7.3f}" for k in ("acc", "prec", "rec", "f1")))
    print(f"  {'':2}{'Informe (los 4 modelos)':<25}" + "".join(f"{expected[k]:7.3f}" for k in ("acc", "prec", "rec", "f1")))

    section("Pregunta abierta del informe · ¿los modelos aprenden la misma regla?")
    names = list(preds)
    base = preds[names[0]]
    for n in names[1:]:
        diff = int((preds[n] != base).sum())
        print(f"  {names[0]} vs {n:<26} {'predicciones idénticas' if diff == 0 else f'{diff} bloques distintos'}")
    caught = (y_te.values == 1) & (base == 1)
    missed = (y_te.values == 1) & (base == 0)
    print(f"\n  Anomalías de test atrapadas por el árbol: {caught.sum()} · no detectadas: {missed.sum()}")
    for label, mask in (("atrapadas", caught), ("no detectadas", missed)):
        e5 = X_te.loc[mask, "E5"].value_counts().sort_index()
        print(f"    E5 en las {label:<14} " + ", ".join(f"E5={k}: {v}" for k, v in e5.items()))

    passed = sum(results)
    section(f"Resumen: {passed}/{len(results)} cifras coinciden con el informe")

    section("Sensibilidad a la partición · misma muestra, otras semillas")
    rec = []
    for seed in range(10):
        a, b, c, d = train_test_split(X, y, test_size=TEST_SIZE, stratify=y, random_state=seed)
        rec.append(recall_score(d, DecisionTreeClassifier(random_state=SEED).fit(a, c).predict(b)))
    print(f"  Recall del árbol con 10 particiones distintas: min {min(rec):.3f} · media {np.mean(rec):.3f} · max {max(rec):.3f}")
    print("  Con 63 anomalías en test, un solo bloque mueve el recall en 0.016: hace falta validación cruzada.")


if __name__ == "__main__":
    main()
