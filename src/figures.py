"""Fase 6 · Figuras del informe final.

Genera en informe/figuras/:
    fig1_clases.png    clases en la muestra y en el conjunto completo
    fig2_importancia.png  importancia del árbol (profundidad 3): muestra vs. completo
    fig3_curva_pr.png               curvas precisión–recall en test (mejor config. de cada modelo)

La Figura 4 (captura de LogWatch) se toma del navegador, no de este script.

Uso:
    PYTHONPATH=src python src/figures.py
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve
from sklearn.tree import DecisionTreeClassifier

from config import ARTIFACTS, ROOT, SEED
from features import load_matrix, load_split

OUT = ROOT / "informe" / "figuras"
INK, MUTED, GRID = "#1f2937", "#6b7280", "#e5e7eb"
C_NORMAL, C_ANOM = "#94a3b8", "#e4572e"
C_MODEL = {"rf": "#0e7490", "dt": "#d97706", "lr": "#64748b", "nb": "#7c3aed"}
NAMES = {"rf": "Random Forest", "dt": "Árbol de decisión", "lr": "Regresión logística", "nb": "Naive Bayes"}
BEST = {"rf": "rf_tfidf_smote", "dt": "dt_tfidf_cw", "lr": "lr_count_cw", "nb": "nb_count_cw"}

plt.rcParams.update({
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "savefig.dpi": 300, "savefig.bbox": "tight", "font.family": "DejaVu Sans",
})


def fig_distribution() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(3.5, 1.9))
    for ax, source, title in zip(axes, ["sample", "full"], ["Muestra (Avance 1)", "Conjunto completo"]):
        _, y = load_matrix(source)
        counts = [int((y == 0).sum()), int((y == 1).sum())]
        bars = ax.bar(["Normal", "Anomalía"], counts, color=[C_NORMAL, C_ANOM], width=0.6)
        for b, c in zip(bars, counts):
            ax.annotate(f"{c:,}\n({c / sum(counts):.2%})", (b.get_x() + b.get_width() / 2, c),
                        ha="center", va="bottom", fontsize=6.5, color=INK, xytext=(0, 2), textcoords="offset points")
        ax.set_title(f"{title}\n{sum(counts):,} bloques", color=INK)
        ax.set_ylim(0, max(counts) * 1.35)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1000:g}k" if v else "0"))
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_clases.png")
    plt.close(fig)


def tree_importance(source: str) -> pd.Series:
    X_tr, _, y_tr, _ = load_split(source)
    tree = DecisionTreeClassifier(max_depth=3, random_state=SEED).fit(X_tr, y_tr)
    return pd.Series(tree.feature_importances_, index=X_tr.columns)


def fig_importance() -> None:
    sample, full = tree_importance("sample"), tree_importance("full")
    events = [e for e in sample.index.union(full.index) if sample.get(e, 0) > 0.001 or full.get(e, 0) > 0.001]
    events = sorted(events, key=lambda e: -(full.get(e, 0) + sample.get(e, 0) / 10))
    s = np.array([sample.get(e, 0) for e in events]) * 100
    f = np.array([full.get(e, 0) for e in events]) * 100
    y = np.arange(len(events))
    fig, ax = plt.subplots(figsize=(3.5, 2.1))
    ax.barh(y - 0.2, s, 0.38, color=C_NORMAL, label="Muestra (7,940 bloques)")
    ax.barh(y + 0.2, f, 0.38, color=C_MODEL["rf"], label="Conjunto completo (575,061)")
    for yi, a, b in zip(y, s, f):
        for v, dy, c in [(a, -0.2, MUTED), (b, 0.2, INK)]:
            ax.text(v + 1, yi + dy, f"{v:.1f}%" if v >= 0.05 else "0", va="center", fontsize=6, color=c)
    ax.set_yticks(y, events)
    ax.invert_yaxis()
    ax.set_xlim(0, 105)
    ax.set_xlabel("Importancia en el árbol (%)")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "fig2_importancia.png")
    plt.close(fig)
    print("  importancia completo:", {e: round(v * 100, 1) for e, v in full[full > 0].sort_values(ascending=False).items()})


def fig_pr() -> None:
    pred = pd.read_parquet(ARTIFACTS / "test_predictions.parquet")
    y = pred["Label"].to_numpy()
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    for m in ["nb", "lr", "dt", "rf"]:
        p, r, t = precision_recall_curve(y, pred[BEST[m]].to_numpy())
        ax.step(r, p, where="post", color=C_MODEL[m], lw=1.6 if m == "rf" else 1.1, label=NAMES[m])
        if m == "rf":
            # punto de operación por defecto (0.5) y el umbral que asegura recall ≥ 99.9 %
            i5 = np.searchsorted(t, 0.5)
            ax.plot(r[i5], p[i5], "o", ms=4, mfc="white", mec=C_MODEL[m], zorder=5)
            ok = np.where(r[:-1] >= 0.999)[0]
            i = ok[-1]                                   # el umbral más alto que aún cumple
            flagged = int((pred[BEST[m]] >= t[i]).sum())
            ax.plot(r[i], p[i], "o", ms=4, color=C_MODEL[m], zorder=5)
            ax.annotate(f"umbral {t[i]:.2f}: revisar {flagged:,} bloques\n({flagged / len(y):.2%}), recall {r[i]:.4f}",
                        (r[i], p[i]), xytext=(0.22, 0.42), textcoords="axes fraction", fontsize=6.5, color=INK,
                        arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
            print(f"  RF: umbral {t[i]:.3f} · {flagged} marcados · precisión {p[i]:.4f} · recall {r[i]:.4f}")
    ax.set_xlim(0.95, 1.001)
    ax.set_ylim(0.85, 1.005)
    ax.set_xlabel("Recall (clase anómala)")
    ax.set_ylabel("Precisión")
    ax.grid(color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)
    fig.tight_layout()
    fig.savefig(OUT / "fig3_curva_pr.png")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig_distribution()
    fig_importance()
    fig_pr()
    print(f"Figuras en {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
