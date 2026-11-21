"""Fase 5 · Exporta los resultados para la interfaz LogWatch.

Genera UI/src/data/resultados.json con todo lo que necesita la interfaz:

    meta        cifras del dataset, del parsing y de la partición
    configs     las 16 configuraciones: hiperparámetros, métricas en CV y en test,
                histograma de probabilidades por clase (200 bins) e importancia de variables
    events      los 29 eventos: plantilla, descripción, media y % de presencia por clase
    triage      muestra de bloques de test con su vector y la probabilidad de cada config
    vectors     los vectores de conteo distintos del dataset y cuántos bloques de cada clase
                tienen cada uno (para detectar en el simulador vectores ambiguos)
    sim         modelos exportados (árboles, coeficientes, parámetros de NB y TF-IDF)
                para evaluarlos en el navegador, más presets y rango de cada evento

Al final verifica que los modelos exportados, reimplementados con numpy igual que
en el navegador, dan las mismas probabilidades que scikit-learn.

Uso:
    python src/export.py
"""
import json
from datetime import date

import joblib
import numpy as np
import pandas as pd

from config import ARTIFACTS, FULL_DIR, MODELS_DIR, ROOT, SEED
from features import load_matrix, load_split
from parse import DEFAULT_SIM_TH

OUT = ROOT / "UI" / "src" / "data" / "resultados.json"
NB_BINS = 200

MODEL_INFO = [
    {"id": "rf", "name": "Random Forest", "short": "RF"},
    {"id": "dt", "name": "Árbol de decisión", "short": "Árbol"},
    {"id": "lr", "name": "Regresión logística", "short": "Reg. log."},
    {"id": "nb", "name": "Naive Bayes", "short": "NB"},
]
REP_INFO = [{"id": "count", "name": "Conteo"}, {"id": "tfidf", "name": "TF-IDF"}]
BAL_INFO = [{"id": "cw", "name": "class_weight"}, {"id": "smote", "name": "SMOTE"}]

# Descripciones en español de los eventos (Tabla II del informe + resto de plantillas de Loghub)
EVENT_DESC = {
    "E1": "Se intenta agregar un bloque que ya existe.",
    "E2": "Un DataNode verifica con éxito la integridad del bloque.",
    "E3": "Un DataNode envía el bloque a un cliente (lectura).",
    "E4": "Excepción mientras un DataNode sirve el bloque.",
    "E5": "Un DataNode inicia la recepción del bloque; una vez por réplica.",
    "E6": "Un DataNode recibe una copia del bloque desde otro nodo (re-replicación).",
    "E7": "Excepción durante la escritura del bloque.",
    "E8": "El hilo que confirma paquetes se interrumpe antes de terminar.",
    "E9": "Un DataNode confirma la recepción completa del bloque y su tamaño.",
    "E10": "Excepción en el hilo que confirma paquetes.",
    "E11": "Cierre normal del hilo que confirma paquetes en el pipeline.",
    "E12": "Excepción al escribir el bloque hacia el siguiente nodo del pipeline.",
    "E13": "Un DataNode recibe un paquete vacío para el bloque.",
    "E14": "Excepción al recibir el bloque.",
    "E15": "Se cambia el offset del archivo del bloque.",
    "E16": "Un DataNode transmite el bloque a otro nodo.",
    "E17": "Falla la transferencia del bloque a otro nodo.",
    "E18": "Se inicia un hilo para transferir el bloque a otro nodo.",
    "E19": "Se reabre el bloque.",
    "E20": "Error al eliminar el bloque: no está en el mapa del volumen.",
    "E21": "Un DataNode elimina el archivo del bloque.",
    "E22": "El NameNode asigna un nuevo bloque a un archivo (inicio del ciclo de vida).",
    "E23": "El NameNode marca el bloque para eliminación en un DataNode.",
    "E24": "El NameNode quita el bloque de la lista de réplicas pendientes.",
    "E25": "El NameNode pide replicar el bloque a otro DataNode.",
    "E26": "El NameNode registra que una réplica del bloque quedó almacenada.",
    "E27": "El NameNode recibe un registro redundante de una réplica.",
    "E28": "El NameNode recibe el registro de un bloque que no pertenece a ningún archivo.",
    "E29": "Se agota el tiempo de espera de una réplica pendiente.",
}


# ---------- exportación de modelos ----------

def r6(a):
    return [round(float(x), 6) for x in np.asarray(a).ravel()]


def exact(a):
    """Sin redondear: TF-IDF y umbrales deben ser exactos o los árboles toman otro camino."""
    return [float(x) for x in np.asarray(a).ravel()]


def export_tree(tree) -> dict:
    """Árbol de sklearn como arrays planos: f=variable (-1 en hojas), t=umbral, l/r=hijos, p=P(anomalía)."""
    t = tree.tree_
    val = t.value[:, 0, :]
    p = val[:, 1] / np.maximum(val.sum(axis=1), 1e-12)
    leaf = t.children_left == -1
    return {
        "f": [int(x) if not lf else -1 for x, lf in zip(t.feature, leaf)],
        "t": [0 if lf else float(x) for x, lf in zip(t.threshold, leaf)],
        "l": t.children_left.tolist(),
        "r": t.children_right.tolist(),
        "p": [round(float(x), 6) if lf else 0 for x, lf in zip(p, leaf)],
    }


def export_pipeline(pipe) -> dict:
    out = {}
    if "tfidf" in pipe.named_steps:
        tf = pipe.named_steps["tfidf"]
        out["tfidf"] = {"idf": exact(tf.idf_), "mean": exact(tf.mean_)}
    clf = pipe.named_steps["clf"]
    name = type(clf).__name__
    if name == "RandomForestClassifier":
        out["type"], out["trees"] = "forest", [export_tree(e) for e in clf.estimators_]
    elif name == "DecisionTreeClassifier":
        out["type"], out["trees"] = "forest", [export_tree(clf)]
    elif name == "LogisticRegression":
        out["type"], out["coef"], out["intercept"] = "logistic", exact(clf.coef_[0]), float(clf.intercept_[0])
    elif name == "GaussianNB":
        out["type"] = "gaussian_nb"
        out["theta"] = [exact(clf.theta_[0]), exact(clf.theta_[1])]
        out["var"] = [exact(clf.var_[0]), exact(clf.var_[1])]
        out["prior"] = exact(clf.class_prior_)
    else:
        raise ValueError(f"Modelo no soportado: {name}")
    return out


def predict_exported(m: dict, X: np.ndarray) -> np.ndarray:
    """Misma lógica que usará el navegador (UI/src/lib/models.js), en numpy."""
    X = X.astype(float)
    if "tfidf" in m:
        X = X * np.array(m["tfidf"]["idf"]) - np.array(m["tfidf"]["mean"])
    if m["type"] == "forest":
        # los árboles de sklearn comparan la entrada convertida a float32 (en JS: Math.fround)
        X = X.astype(np.float32).astype(float)
        out = np.zeros(len(X))
        for tr in m["trees"]:
            for i, x in enumerate(X):
                n = 0
                while tr["f"][n] != -1:
                    n = tr["l"][n] if x[tr["f"][n]] <= tr["t"][n] else tr["r"][n]
                out[i] += tr["p"][n]
        return out / len(m["trees"])
    if m["type"] == "logistic":
        return 1 / (1 + np.exp(-(X @ np.array(m["coef"]) + m["intercept"])))
    if m["type"] == "gaussian_nb":
        jll = []
        for c in (0, 1):
            th, var = np.array(m["theta"][c]), np.array(m["var"][c])
            jll.append(np.log(m["prior"][c]) - 0.5 * np.sum(np.log(2 * np.pi * var)) - 0.5 * np.sum((X - th) ** 2 / var, axis=1))
        jll = np.array(jll).T
        jll -= jll.max(axis=1, keepdims=True)
        e = np.exp(jll)
        return e[:, 1] / e.sum(axis=1)
    raise ValueError(m["type"])


# ---------- main ----------

def main() -> None:
    X, y = load_matrix("full")
    X_tr, X_te, y_tr, y_te = load_split("full")
    events = list(X.columns)
    cv = pd.read_csv(ARTIFACTS / "cv_results.csv").set_index("config")
    test = pd.read_csv(ARTIFACTS / "test_metrics.csv").set_index("config")
    probs = pd.read_parquet(ARTIFACTS / "test_predictions.parquet")
    assert (probs.index == X_te.index).all(), "test_predictions no coincide con la partición actual"
    cids = list(cv.index)
    templates = pd.read_csv(FULL_DIR / "preprocessed" / "HDFS.log_templates.csv").set_index("EventId")["EventTemplate"]
    drain = pd.read_csv(ROOT / "data" / "processed" / "full_templates.csv")

    # --- configuraciones
    configs, pipes = {}, {}
    for cid in cids:
        pipe = joblib.load(MODELS_DIR / f"{cid}.joblib")
        pipes[cid] = pipe
        clf = pipe.named_steps["clf"]
        p = probs[cid].values
        b = np.minimum(np.floor(p * NB_BINS + 1e-9).astype(int), NB_BINS - 1)
        c, t = cv.loc[cid], test.loc[cid]
        configs[cid] = {
            "model": c["model"], "rep": c["rep"], "bal": c["bal"],
            "params": json.loads(c["best_params"]),
            "cv": {k: round(float(c[f"{k}_mean"]), 5) for k in ("f1", "precision", "recall", "ap")}
                  | {"f1_std": round(float(c["f1_std"]), 5), "fit_minutes": float(c["fit_minutes"])},
            "test": {k: round(float(t[k]), 5) for k in ("accuracy", "precision", "recall", "f1", "ap")}
                    | {k: int(t[k]) for k in ("tp", "fp", "fn", "tn")},
            "hist": {"n": np.bincount(b[y_te.values == 0], minlength=NB_BINS).tolist(),
                     "a": np.bincount(b[y_te.values == 1], minlength=NB_BINS).tolist()},
            "importance": r6(clf.feature_importances_) if hasattr(clf, "feature_importances_") else None,
        }
    best = cv["f1_mean"].idxmax()
    default = cv[cv["model"] == "rf"]["f1_mean"].idxmax()

    # --- eventos
    mean = X.groupby(y).mean()
    pres = (X > 0).groupby(y).mean()
    ev = [{
        "id": e, "template": templates[e].replace("[*]", " * ").replace("  ", " ").strip(),
        "desc": EVENT_DESC[e], "lines": int(X[e].sum()),
        "mean": [round(float(mean.loc[0, e]), 4), round(float(mean.loc[1, e]), 4)],
        "presence": [round(float(pres.loc[0, e]), 5), round(float(pres.loc[1, e]), 5)],
    } for e in events]

    # --- vectores distintos y ambigüedad
    key = pd.util.hash_pandas_object(X, index=False)
    grp = pd.DataFrame({"k": key.values, "y": y.values}).groupby("k")["y"].agg(["sum", "count"])
    first = X.groupby(key.values).head(1)
    first_key = pd.util.hash_pandas_object(first, index=False)
    vec_df = pd.DataFrame(first.values, index=first_key.values).join(grp)
    vec_df = vec_df.sort_values("count", ascending=False)
    vectors = [{"v": [int(x) for x in r[:len(events)]], "n": int(r["count"] - r["sum"]), "a": int(r["sum"])}
               for _, r in vec_df.iterrows()]
    ambiguous_keys = set(grp[(grp["sum"] > 0) & (grp["sum"] < grp["count"])].index)

    Xs, ys = load_matrix("sample")
    ks = pd.util.hash_pandas_object(Xs, index=False)
    gs = pd.DataFrame({"k": ks.values, "y": ys.values}).groupby("k")["y"].agg(["sum", "count"])
    amb_full = int(y[key.isin(set(grp[grp["sum"] < grp["count"]].index)) & (y == 1)].sum())
    amb_sample = int(ys[ks.isin(set(gs[gs["sum"] < gs["count"]].index)) & (ys == 1)].sum())
    min_err = lambda g: int(np.minimum(g["sum"], g["count"] - g["sum"]).sum())

    # --- muestra para triage: todos los bloques que alguna config clasifica mal + muestra aleatoria
    pred = probs[cids].values >= 0.5
    wrong = (pred != y_te.values[:, None]).any(axis=1)
    rng = np.random.default_rng(SEED)
    idx_a = np.where((y_te.values == 1) & ~wrong)[0]
    idx_n = np.where((y_te.values == 0) & ~wrong)[0]
    pick = np.unique(np.concatenate([np.where(wrong)[0], rng.choice(idx_a, 250, replace=False),
                                     rng.choice(idx_n, 350, replace=False)]))
    te_key = key.loc[X_te.index].values
    triage = [{
        "id": X_te.index[i], "y": int(y_te.iloc[i]), "v": X_te.iloc[i].astype(int).tolist(),
        "p": [round(float(probs[cid].iloc[i]), 4) for cid in cids],
        "amb": bool(te_key[i] in ambiguous_keys),
    } for i in pick]

    # --- simulador
    top_normal = next(v for v in vectors if v["n"] > 0 and v["a"] == 0)
    top_anoms = [v for v in vectors if v["a"] > 0 and v["n"] == 0][:3]
    top_amb = max((v for v in vectors if v["a"] > 0 and v["n"] > 0), key=lambda v: v["a"])
    presets = [{"name": "Normal más común", "v": top_normal["v"], "n": top_normal["n"], "a": top_normal["a"]}]
    presets += [{"name": f"Anomalía frecuente {i + 1}", "v": v["v"], "n": v["n"], "a": v["a"]} for i, v in enumerate(top_anoms)]
    presets.append({"name": "Vector ambiguo", "v": top_amb["v"], "n": top_amb["n"], "a": top_amb["a"]})
    # rango de cada slider: hasta el percentil 99.9 del evento (mín. típico + 3, máx. 60)
    slider_max = [min(60, int(max(typ + 3, np.quantile(X[e], 0.999))))
                  for e, typ in zip(events, top_normal["v"])]

    data = {
        "meta": {
            "generated": date.today().isoformat(),
            "dataset": {"lines": 11_175_629, "blocks": int(len(X)), "anomalies": int(y.sum()),
                        "events": len(events), "drain_clusters": int(len(drain)), "drain_sim_th": DEFAULT_SIM_TH,
                        "distinct_vectors": len(vectors)},
            "split": {"train": int(len(X_tr)), "train_anomalies": int(y_tr.sum()),
                      "test": int(len(X_te)), "test_anomalies": int(y_te.sum())},
            "ambiguity": {
                "sample": {"blocks": int(len(Xs)), "anomalies": int(ys.sum()), "ambiguous_anomalies": amb_sample,
                           "distinct_vectors": int(len(gs)), "min_errors": min_err(gs)},
                "full": {"blocks": int(len(X)), "anomalies": int(y.sum()), "ambiguous_anomalies": amb_full,
                         "distinct_vectors": int(len(grp)), "min_errors": min_err(grp)},
            },
            "best_config": best, "default_config": default, "bins": NB_BINS,
        },
        "models": MODEL_INFO, "reps": REP_INFO, "bals": BAL_INFO,
        "config_ids": cids, "configs": configs, "events": ev,
        "triage": triage, "vectors": vectors,
        "sim": {"presets": presets, "slider_max": slider_max, "typical": top_normal["v"],
                "models": {cid: export_pipeline(pipes[cid]) for cid in cids}},
    }

    # --- verificación: modelos exportados == scikit-learn
    print("Verificando modelos exportados contra scikit-learn...")
    check = np.vstack([np.array([v["v"] for v in vectors]), X_te.sample(500, random_state=SEED).values])
    worst = 0.0
    for cid in cids:
        ref = pipes[cid].predict_proba(check)[:, 1]
        got = predict_exported(data["sim"]["models"][cid], check)
        diff = float(np.abs(ref - got).max())
        flips = int(((ref >= 0.5) != (got >= 0.5)).sum())
        worst = max(worst, diff)
        status = "✓" if diff < 1e-4 and flips == 0 else "✗"
        print(f"  {status} {cid:<16} diferencia máx {diff:.2e} · predicciones distintas {flips}")
        if status == "✗":
            raise SystemExit(f"La exportación de {cid} no reproduce a scikit-learn")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"\nGuardado {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB)")
    print(f"  configuraciones {len(cids)} · mejor según CV {best} · por defecto en la UI {default}")
    print(f"  triage {len(triage)} bloques · vectores distintos {len(vectors)} · presets {len(presets)}")


if __name__ == "__main__":
    main()
