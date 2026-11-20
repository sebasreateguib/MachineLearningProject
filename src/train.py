"""Etapas 5–8 · Entrenamiento de las 16 configuraciones con GridSearchCV.

    4 modelos  ×  2 representaciones  ×  2 estrategias de desbalance  =  16 configuraciones
    (DT, RF,      (conteo, TF-IDF)        (class_weight/priors, SMOTE)
     LR, NB)

Cada configuración es un Pipeline de imbalanced-learn:

    [TF-IDF]  →  [SMOTE]  →  clasificador

así TF-IDF y SMOTE se ajustan dentro de cada fold de la validación cruzada, solo con
los datos de entrenamiento de ese fold (sin fuga de datos). Los hiperparámetros se
eligen por F1 de la clase anómala en CV estratificada de 5 folds.

Este script NO usa el conjunto de test: eso lo hace src/evaluate.py, una sola vez.

Salidas (en artifacts/):
    models/<config>.joblib    mejor pipeline de cada configuración, reentrenado en todo train
    cv/<config>.csv           resultados de cada combinación de hiperparámetros
    cv_results.csv            resumen: mejor combinación de cada configuración

Si se interrumpe, al volver a ejecutarlo retoma desde donde quedó (las configuraciones
ya guardadas se saltan; usar --force para reentrenarlas).

Uso:
    python src/train.py                 # las 16 configuraciones
    python src/train.py --models dt lr  # solo algunos modelos
    python src/train.py --quick         # prueba rápida con 20k bloques (salida en artifacts/quick/)
"""
import argparse
import json
import math
import time

import joblib
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import make_scorer, precision_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier

from config import ARTIFACTS, CV_FOLDS, SEED
from features import TfidfTransformer, load_split


def _cw(bal):
    return "balanced" if bal == "cw" else None


# id: (nombre, constructor según estrategia de desbalance, grilla de hiperparámetros)
MODELS = {
    "nb": ("Naive Bayes",
           # GaussianNB no admite class_weight: el equivalente es fijar priors iguales.
           # Con SMOTE las clases ya quedan balanceadas y se usan los priors empíricos.
           lambda bal: GaussianNB(priors=[0.5, 0.5] if bal == "cw" else None),
           {"var_smoothing": [1e-9, 1e-7, 1e-5]}),
    "lr": ("Regresión logística",
           lambda bal: LogisticRegression(max_iter=5000, class_weight=_cw(bal)),
           # la primera corrida eligió C=10, el extremo de [0.01..10]: se amplió la grilla
           {"C": [0.01, 0.1, 1, 10, 100, 1000]}),
    "dt": ("Árbol de decisión",
           lambda bal: DecisionTreeClassifier(random_state=SEED, class_weight=_cw(bal)),
           {"max_depth": [5, 10, 20, None], "min_samples_leaf": [1, 5, 20]}),
    "rf": ("Random Forest",
           # n_jobs=1: el paralelismo lo hace GridSearchCV (un fit por núcleo)
           lambda bal: RandomForestClassifier(random_state=SEED, n_jobs=1, class_weight=_cw(bal)),
           {"n_estimators": [100, 300], "max_depth": [10, 20, None]}),
}
REPS = {"count": "Conteo", "tfidf": "TF-IDF"}
BALS = {"cw": "class_weight", "smote": "SMOTE"}
SCORING = {
    "f1": "f1",
    "precision": make_scorer(precision_score, zero_division=0),
    "recall": "recall",
    "ap": "average_precision",
}


def config_id(model: str, rep: str, bal: str) -> str:
    return f"{model}_{rep}_{bal}"


def build_pipeline(model: str, rep: str, bal: str) -> Pipeline:
    steps = []
    if rep == "tfidf":
        steps.append(("tfidf", TfidfTransformer()))
    if bal == "smote":
        steps.append(("smote", SMOTE(random_state=SEED)))
    steps.append(("clf", MODELS[model][1](bal)))
    return Pipeline(steps)


def save_summary(path, row: dict) -> pd.DataFrame:
    """Agrega o reemplaza la fila de una configuración en el resumen CSV."""
    df = pd.read_csv(path) if path.exists() else pd.DataFrame()
    if len(df):
        df = df[df["config"] != row["config"]]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True).sort_values("f1_mean", ascending=False)
    df.to_csv(path, index=False)
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    ap.add_argument("--force", action="store_true", help="reentrenar aunque el modelo ya exista")
    ap.add_argument("--quick", action="store_true", help="prueba con 20k bloques, 3 folds y grillas mínimas")
    ap.add_argument("--n-jobs", type=int, default=-1)
    args = ap.parse_args()

    out = ARTIFACTS / "quick" if args.quick else ARTIFACTS
    (out / "models").mkdir(parents=True, exist_ok=True)
    (out / "cv").mkdir(parents=True, exist_ok=True)
    summary_path = out / "cv_results.csv"

    X_tr, _, y_tr, _ = load_split("full")  # el test (_) no se usa aquí
    folds = CV_FOLDS
    if args.quick:
        X_tr, _, y_tr, _ = train_test_split(X_tr, y_tr, train_size=20_000, stratify=y_tr, random_state=SEED)
        folds = 3
    print(f"Train: {len(X_tr):,} bloques · {int(y_tr.sum()):,} anomalías ({y_tr.mean():.2%}) · CV {folds} folds")
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=SEED)

    configs = [(m, r, b) for m in args.models for r in REPS for b in BALS]
    t_all = time.time()
    for i, (m, r, b) in enumerate(configs, start=1):
        cid = config_id(m, r, b)
        model_path = out / "models" / f"{cid}.joblib"
        label = f"[{i:2}/{len(configs)}] {MODELS[m][0]} · {REPS[r]} · {BALS[b]}"
        if model_path.exists() and not args.force:
            print(f"{label:<55} ya entrenado, se salta")
            continue

        grid = {f"clf__{k}": (v[:1] if args.quick else v) for k, v in MODELS[m][2].items()}
        gs = GridSearchCV(build_pipeline(m, r, b), grid, scoring=SCORING, refit="f1", cv=cv,
                          n_jobs=args.n_jobs, error_score="raise")
        n_cand = math.prod(len(v) for v in grid.values())
        print(f"{label:<55} {n_cand:>2} combinaciones × {folds} folds ...", end=" ", flush=True)
        t0 = time.time()
        gs.fit(X_tr.values, y_tr.values)
        minutes = (time.time() - t0) / 60

        res = pd.DataFrame(gs.cv_results_)
        res.to_csv(out / "cv" / f"{cid}.csv", index=False)
        k = gs.best_index_
        row = {
            "config": cid, "model": m, "rep": r, "bal": b,
            "best_params": json.dumps({p.removeprefix("clf__"): v for p, v in gs.best_params_.items()}),
            **{f"{s}_{agg}": res.loc[k, f"{agg}_test_{s}"] for s in SCORING for agg in ("mean", "std")},
            "fit_minutes": round(minutes, 2),
        }
        joblib.dump(gs.best_estimator_, model_path, compress=3)
        save_summary(summary_path, row)
        print(f"F1 {row['f1_mean']:.4f} ± {row['f1_std']:.4f} · {minutes:.1f} min · {row['best_params']}", flush=True)

    print(f"\nTiempo total: {(time.time() - t_all) / 60:.1f} min\n")
    if summary_path.exists():
        df = pd.read_csv(summary_path)
        cols = ["config", "f1_mean", "f1_std", "precision_mean", "recall_mean", "ap_mean", "best_params"]
        with pd.option_context("display.width", 200, "display.max_colwidth", 60, "display.float_format", "{:.4f}".format):
            print(df[cols].to_string(index=False))


if __name__ == "__main__":
    main()
