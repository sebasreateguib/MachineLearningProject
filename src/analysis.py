"""Fase 4 · Análisis de la solución y alternativas de mejora (para la Discusión del informe).

Secciones:
  1. ¿Por qué falla Naive Bayes?            hipótesis (correlación, no-gaussianidad) vs. interacciones
  2. Anomalías indistinguibles por conteo    qué vectores comparten ambas clases y qué patrón tienen
  3. Errores del mejor modelo de árboles     cuáles son inevitables por conteo y cuáles no
  4. Alternativa de mejora: orden            pares de eventos consecutivos (requiere src/sequences.py)
  5. Robustez: partición cronológica         entrenar con bloques antiguos, evaluar con recientes

Usa los hiperparámetros elegidos en la Fase 3 (artifacts/cv_results.csv) y la misma
partición de src/features.py. Guarda un resumen en artifacts/analysis.json.

Uso:
    python src/analysis.py               # todas las secciones (~10 min, la 4 entrena con 300+ variables)
    python src/analysis.py --only 1 2 3  # algunas secciones
"""
import argparse
import json
import time

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier

from config import ARTIFACTS, CV_FOLDS, PROCESSED, SEED, TEST_SIZE
from features import load_matrix, load_split

SUMMARY = {}


def section(title):
    print(f"\n{title}\n" + "─" * len(title), flush=True)


def scores(y, p) -> dict:
    y, p = np.asarray(y), np.asarray(p)
    return {"f1": round(f1_score(y, p), 4), "precision": round(precision_score(y, p, zero_division=0), 4),
            "recall": round(recall_score(y, p), 4),
            "fp": int(((p == 1) & (y == 0)).sum()), "fn": int(((p == 0) & (y == 1)).sum())}


def fmt(s: dict) -> str:
    return f"F1 {s['f1']:.4f} · P {s['precision']:.4f} · R {s['recall']:.4f} · FP {s['fp']:>4} · FN {s['fn']:>3}"


def vector_groups(M: pd.DataFrame, y: pd.Series):
    """Agrupa bloques por vector idéntico: cuántos anómalos (a) y normales (n) hay en cada uno."""
    key = pd.util.hash_pandas_object(M, index=False)
    g = pd.DataFrame({"k": key.values, "y": y.values}).groupby("k")["y"].agg(["sum", "count"])
    g = g.rename(columns={"sum": "a"})
    g["n"] = g["count"] - g["a"]
    return key, g


def ambiguity(M, y) -> dict:
    _, g = vector_groups(M, y)
    amb = g[(g["a"] > 0) & (g["n"] > 0)]
    return {"distinct_vectors": int(len(g)), "ambiguous_vectors": int(len(amb)),
            "ambiguous_anomalies": int(amb["a"].sum()), "normals_in_ambiguous": int(amb["n"].sum()),
            "min_errors": int(np.minimum(g["a"], g["n"]).sum())}


def best_models() -> dict:
    """Mejor configuración de cada modelo con conteo + class_weight (hiperparámetros de la Fase 3)."""
    cv = pd.read_csv(ARTIFACTS / "cv_results.csv").set_index("config")
    p = {m: json.loads(cv.loc[f"{m}_count_cw", "best_params"]) for m in ("dt", "rf", "lr", "nb")}
    return {
        "dt": DecisionTreeClassifier(random_state=SEED, class_weight="balanced", **p["dt"]),
        "rf": RandomForestClassifier(random_state=SEED, class_weight="balanced", n_jobs=-1, **p["rf"]),
        "lr": LogisticRegression(max_iter=5000, class_weight="balanced", **p["lr"]),
        "nb": GaussianNB(priors=[0.5, 0.5], **p["nb"]),
    }


# ---------- 1 ----------
def naive_bayes(X_tr, X_te, y_tr, y_te):
    section("1 · ¿Por qué falla Naive Bayes?")
    core = ["E5", "E9", "E11", "E26", "E21", "E23"]
    corr = X_tr[core].corr()
    print("  Correlación entre eventos del ciclo de vida (train):")
    print("  " + corr.round(2).to_string().replace("\n", "\n  "))

    nb = best_models()["nb"]
    drop = ["E9", "E11", "E26"]
    variants = {
        "base (29 eventos)": (X_tr, X_te),
        "(a) sin eventos redundantes E9, E11, E26": (X_tr.drop(columns=drop), X_te.drop(columns=drop)),
        "(b) log(1+x) para acercarse a una gaussiana": (np.log1p(X_tr), np.log1p(X_te)),
    }
    print("\n  Hipótesis puestas a prueba (test):")
    res = {}
    for name, (a, b) in variants.items():
        res[name] = scores(y_te, clone(nb).fit(a, y_tr).predict(b))
        print(f"    {name:<46} {fmt(res[name])}")
    print("  → Ni quitar la redundancia ni transformar los conteos cambia los errores: ninguna de las dos explica el problema.")

    rr = X_te["E6"] > 0   # re-replicación: E6, E16, E18 y E25 aparecen siempre juntos
    pred = pd.read_parquet(ARTIFACTS / "test_predictions.parquet")
    print("\n  Bloques con re-replicación (E6, E16, E18, E25) en test que cada modelo marca como anomalía:")
    rep = {}
    for lab, name in ((0, "normales"), (1, "anómalos")):
        sel = rr & (y_te == lab)
        row = {c: int((pred.loc[sel, c] >= 0.5).sum()) for c in ("nb_count_cw", "lr_count_cw", "dt_count_cw", "rf_count_cw")}
        rep[name] = {"total": int(sel.sum()), **row}
        print(f"    {name:<9} ({int(sel.sum()):>3}): " + " · ".join(f"{c.split('_')[0].upper()} {v} ({v / max(sel.sum(), 1):.0%})" for c, v in row.items()))
    nb_fp = res["base (29 eventos)"]["fp"]
    print(f"  → {rep['normales']['nb_count_cw']} de las {nb_fp} falsas alarmas de NB son re-replicaciones normales.")
    print("    NB evalúa cada evento por separado y la re-replicación es 70 veces más frecuente en anomalías.")
    print("    Los árboles aprenden la combinación: re-replicación + eliminaciones (E21/E23) = anomalía.")
    SUMMARY["naive_bayes"] = {"corr": corr.round(3).to_dict(), "hypotheses": res, "rereplication": rep}


# ---------- 2 ----------
def ambiguous_vectors(X, y):
    section("2 · Anomalías indistinguibles por conteo")
    key, g = vector_groups(X, y)
    first = X.groupby(key.values).head(1)
    first.index = pd.util.hash_pandas_object(first, index=False).values
    typical = first.loc[g["n"].idxmax()]
    amb = g[(g["a"] > 0) & (g["n"] > 0)].sort_values("a", ascending=False)
    rows = []
    for k, r in amb.iterrows():
        v = first.loc[k]
        diff = {e: int(v[e]) for e in X.columns if v[e] != typical[e]}
        rows.append({"anomalies": int(r["a"]), "normals": int(r["n"]), "diff_vs_typical": diff})
        print(f"  A={int(r['a']):>4} N={int(r['n']):>4}  difiere del normal típico en {diff}")
    same_as_typical = int(g.loc[g["n"].idxmax(), "a"])
    print(f"\n  {len(amb)} vectores concentran las {int(amb['a'].sum())} anomalías indistinguibles.")
    print(f"  Anomalías idénticas al bloque normal más común (caso B3 del Avance 1): {same_as_typical}")
    SUMMARY["ambiguous"] = {"vectors": rows, "same_as_typical_normal": same_as_typical, **ambiguity(X, y)}


# ---------- 3 ----------
def model_errors(X, y, X_te, y_te):
    section("3 · Errores de los modelos de árboles en test: ¿evitables?")
    key, g = vector_groups(X, y)
    X_tr_idx = X.index.difference(X_te.index)
    key_tr = set(key.loc[X_tr_idx].values)
    pred = pd.read_parquet(ARTIFACTS / "test_predictions.parquet")
    out = {}
    for cid in ("dt_tfidf_cw", "rf_tfidf_smote"):
        p = pred[cid] >= 0.5
        err = X_te.index[(p & (y_te == 0)) | (~p & (y_te == 1))]
        k = key.loc[err]
        amb = k.map(lambda x: g.loc[x, "a"] > 0 and g.loc[x, "n"] > 0)
        unseen = ~k.isin(key_tr)
        c = {"errors": int(len(err)), "ambiguous_vector": int(amb.sum()),
             "unseen_in_train": int((unseen & ~amb).sum()), "other": int((~amb & ~unseen).sum())}
        out[cid] = c
        print(f"  {cid:<16} {c['errors']:>2} errores: {c['ambiguous_vector']} en vectores ambiguos (inevitables con conteo) · "
              f"{c['unseen_in_train']} con un vector nunca visto en train · {c['other']} otros")
    SUMMARY["errors"] = out


# ---------- 4 ----------
def sequence_alternative(X, y):
    section("4 · Alternativa de mejora: incorporar el orden (pares de eventos consecutivos)")
    path = PROCESSED / "full_bigrams.parquet"
    if not path.exists():
        print("  Falta data/processed/full_bigrams.parquet. Ejecuta primero: python src/sequences.py")
        return
    B = pd.read_parquet(path)
    assert (B.index == X.index).all()
    XB = pd.concat([X, B], axis=1)
    a0, a1 = ambiguity(X, y), ambiguity(XB, y)
    print(f"  Variables: {X.shape[1]} conteos  →  {XB.shape[1]} (conteos + {B.shape[1]} pares)")
    print(f"  Anomalías indistinguibles: {a0['ambiguous_anomalies']} → {a1['ambiguous_anomalies']} · "
          f"errores mínimos posibles: {a0['min_errors']} → {a1['min_errors']}")

    X_tr, X_te, y_tr, y_te = load_split("full")
    feats = {"conteo": X, "conteo + orden": XB}
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED)
    models = best_models()
    res = {}
    for m in ("dt", "rf"):
        for fname, M in feats.items():
            t0 = time.time()
            est = clone(models[m])
            if m == "rf":
                est.set_params(n_jobs=1)   # el paralelismo lo hace cross_validate
            cvr = cross_validate(est, M.loc[X_tr.index].values, y_tr.values, cv=cv, scoring="f1", n_jobs=-1)
            est.set_params(**({"n_jobs": -1} if m == "rf" else {}))
            pt = est.fit(M.loc[X_tr.index].values, y_tr.values).predict(M.loc[X_te.index].values)
            s = scores(y_te, pt) | {"cv_f1_mean": round(float(cvr["test_score"].mean()), 4),
                                     "cv_f1_std": round(float(cvr["test_score"].std()), 4)}
            res[f"{m} · {fname}"] = s
            print(f"  {m.upper()} · {fname:<15} CV F1 {s['cv_f1_mean']:.4f} ± {s['cv_f1_std']:.4f} │ test {fmt(s)} "
                  f"({(time.time() - t0) / 60:.1f} min)", flush=True)
    # ¿Por qué empeora? (diagnóstico en una validación interna: el test no se usa)
    from sklearn.model_selection import train_test_split
    itr, iva = train_test_split(np.asarray(X_tr.index, dtype=object), test_size=0.2,
                                stratify=y_tr.values, random_state=SEED)
    unseen = {}
    for fname, M in feats.items():
        k = pd.util.hash_pandas_object(M, index=False)
        u = ~k.loc[iva].isin(set(k.loc[itr]))
        unseen[fname] = {"all": round(float(u.mean()), 4), "anomalies": round(float(u[y.loc[iva] == 1].mean()), 4)}
    print(f"\n  Diagnóstico (validación interna): bloques con un vector nunca visto en train "
          f"{unseen['conteo']['all']:.2%} → {unseen['conteo + orden']['all']:.2%}; "
          f"entre las anomalías {unseen['conteo']['anomalies']:.1%} → {unseen['conteo + orden']['anomalies']:.1%}")
    typ = (X == X[y == 0].mode().iloc[0]).all(axis=1) & (y == 0)
    n_orders = int(B[typ].drop_duplicates().shape[0])
    print(f"  Los {int(typ.sum()):,} bloques normales típicos (idénticos en conteo) tienen {n_orders} órdenes distintos: "
          f"las réplicas se registran en paralelo y su orden en el log varía.")

    # ¿El orden o la latencia separan a los bloques de un mismo vector ambiguo?
    key = pd.util.hash_pandas_object(X, index=False)
    g = pd.DataFrame({"k": key.values, "y": y.values}).groupby("k")["y"].agg(["sum", "count"])
    amb = g[(g["sum"] > 0) & (g["sum"] < g["count"])].sort_values("sum", ascending=False)
    traces = pd.read_csv(PROCESSED.parent / "raw" / "HDFS_v1" / "preprocessed" / "Event_traces.csv",
                         usecols=["BlockId", "Latency"], dtype={"BlockId": str}).set_index("BlockId")["Latency"]
    lat = traces.reindex(X.index)
    kb = pd.util.hash_pandas_object(XB[key.isin(amb.index)], index=False)
    uniq = float((kb.map(kb.value_counts()) == 1).mean())
    print(f"\n  En los vectores ambiguos, el {uniq:.0%} de los bloques queda con un vector único al agregar el orden:")
    print("  la baja de anomalías indistinguibles es en gran parte unicidad, no señal. Dentro de cada vector ambiguo:")
    within = []
    for k, r in amb.iterrows():
        sel = (key == k).values
        ys, Bs, L = y[sel], B[sel].astype(bool), lat[sel]
        d = Bs[ys == 1].mean() - Bs[ys == 0].mean()
        best = d.abs().idxmax()
        row = {"anomalies": int(r["sum"]), "normals": int(r["count"] - r["sum"]), "best_pair": best,
               "pair_in_anomalies": round(float(Bs[ys == 1][best].mean()), 3),
               "pair_in_normals": round(float(Bs[ys == 0][best].mean()), 3),
               "latency_median_anomalies": float(L[ys == 1].median()), "latency_median_normals": float(L[ys == 0].median())}
        within.append(row)
        print(f"    A={row['anomalies']:>3} N={row['normals']:>3} · par más distintivo {best:<9} "
              f"{row['pair_in_anomalies']:.0%} vs {row['pair_in_normals']:.0%} · latencia mediana "
              f"{row['latency_median_anomalies']:>6.0f} vs {row['latency_median_normals']:>6.0f}")
    print("  → Ni el orden ni la latencia separan a anómalos y normales que comparten vector.")

    # Variante en dos etapas: conteo para todo, orden solo para los vectores ambiguos (validación interna)
    s1 = clone(models["rf"]).fit(X.loc[itr].values, y.loc[itr].values)
    gt = pd.DataFrame({"k": key.loc[itr].values, "y": y.loc[itr].values}).groupby("k")["y"].nunique()
    amb_tr = set(gt[gt > 1].index)
    tr_amb = [b for b in itr if key[b] in amb_tr]
    s2 = RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=SEED, n_jobs=-1)
    s2.fit(XB.loc[tr_amb].values, y.loc[tr_amb].values)
    p1 = s1.predict(X.loc[iva].values)
    is_amb = key.loc[iva].isin(amb_tr).values
    p2 = p1.copy()
    p2[is_amb] = s2.predict(XB.loc[iva].values[is_amb])
    two = {"one_stage": scores(y.loc[iva], p1), "two_stage": scores(y.loc[iva], p2), "ambiguous_in_val": int(is_amb.sum())}
    print(f"\n  Dos etapas (validación interna, {two['ambiguous_in_val']} bloques ambiguos): "
          f"solo conteo {fmt(two['one_stage'])} │ dos etapas {fmt(two['two_stage'])}")

    SUMMARY["sequence"] = {"ambiguity_counts": a0, "ambiguity_counts_order": a1, "models": res,
                           "n_bigrams": int(B.shape[1]), "unseen_vectors_val": unseen,
                           "orders_of_typical_normal": n_orders, "unique_after_order": round(uniq, 3),
                           "within_ambiguous_vectors": within, "two_stage_val": two}


# ---------- 5 ----------
def chronological(X, y):
    section("5 · Robustez: partición cronológica (entrenar con el pasado, evaluar con el futuro)")
    pairs = pd.read_parquet(PROCESSED / "full_pairs.parquet", columns=["LineId", "BlockId"])
    first_line = pairs.groupby("BlockId", observed=True)["LineId"].min()
    order = first_line.reindex(X.index).sort_values().index   # bloques según su primera aparición en el log
    cut = int(len(order) * (1 - TEST_SIZE))
    tr, te = order[:cut], order[cut:]
    print(f"  Train: primeros {len(tr):,} bloques ({y.loc[tr].mean():.2%} anómalos) · "
          f"test: últimos {len(te):,} ({y.loc[te].mean():.2%} anómalos)")
    random_test = pd.read_csv(ARTIFACTS / "test_metrics.csv").set_index("config")
    res = {}
    for m, est in best_models().items():
        p = clone(est).fit(X.loc[tr].values, y.loc[tr].values).predict(X.loc[te].values)
        s = scores(y.loc[te], p)
        rnd = float(random_test.loc[f"{m}_count_cw", "f1"])
        res[m] = s | {"f1_random_split": round(rnd, 4)}
        print(f"  {m.upper()}  cronológica {fmt(s)} │ aleatoria F1 {rnd:.4f}")
    SUMMARY["chronological"] = {"train": len(tr), "test": len(te), "train_anomaly_rate": round(float(y.loc[tr].mean()), 4),
                                "test_anomaly_rate": round(float(y.loc[te].mean()), 4), "models": res}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="+", type=int, choices=range(1, 6), default=list(range(1, 6)))
    args = ap.parse_args()

    X, y = load_matrix("full")
    X_tr, X_te, y_tr, y_te = load_split("full")
    out = ARTIFACTS / "analysis.json"
    if out.exists():
        SUMMARY.update(json.loads(out.read_text()))
    if 1 in args.only: naive_bayes(X_tr, X_te, y_tr, y_te)
    if 2 in args.only: ambiguous_vectors(X, y)
    if 3 in args.only: model_errors(X, y, X_te, y_te)
    if 4 in args.only: sequence_alternative(X, y)
    if 5 in args.only: chronological(X, y)
    out.write_text(json.dumps(SUMMARY, ensure_ascii=False, indent=1, default=str))
    print(f"\nResumen guardado en {out.relative_to(ARTIFACTS.parent)}")


if __name__ == "__main__":
    main()
