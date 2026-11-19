"""Etapa 2 · Parsing de los logs en bruto con Drain.

Lee HDFS.log línea por línea, agrupa cada mensaje en una plantilla (cluster) con
Drain3 y guarda, para cada línea, qué bloques menciona y en qué cluster cayó.

Drain numera sus clusters de forma arbitraria (1, 2, 3...). Para que los eventos se
puedan comparar con el informe y la literatura, al final cada cluster recibe el
EventId de la plantilla oficial de Loghub con la que coincide (E1–E29). Ese paso
solo pone nombres: el agrupamiento lo decide Drain.

Salidas (en data/processed/):
    full_pairs.parquet      una fila por (línea, bloque): LineId, BlockId, ClusterId
    full_templates.csv      cada cluster de Drain, su tamaño y el EventId asignado

Uso:
    python src/parse.py                 # todo HDFS.log (11.2 M líneas)
    python src/parse.py --limit 200000  # prueba rápida con las primeras líneas
"""
import argparse
import re
import time

import numpy as np
import pandas as pd
from drain3 import TemplateMiner
from drain3.masking import MaskingInstruction
from drain3.template_miner_config import TemplateMinerConfig

from config import BLOCK_ID_REGEX, FULL_DIR, PROCESSED

LOG_FILE = FULL_DIR / "HDFS.log"
LOGHUB_TEMPLATES = FULL_DIR / "preprocessed" / "HDFS.log_templates.csv"
PAIRS_OUT = PROCESSED / "full_pairs.parquet"
TEMPLATES_OUT = PROCESSED / "full_templates.csv"

# Formato HDFS: <Date> <Time> <Pid> <Level> <Component>: <Content>
HEADER = re.compile(r"^(\d+) (\d+) (\d+) (\w+) (.+?): (.*)$")
BLOCK = re.compile(BLOCK_ID_REGEX)
# Con 0.5 (valor de Loghub) Drain fusiona E8 "PacketResponder .. for block .. Interrupted."
# con E11 "PacketResponder .. for block .. terminating": difieren solo en la última palabra,
# pero una es señal de falla y la otra el cierre normal. Con 0.7 se separan; con >= 0.85
# Drain fragmenta en miles de clusters y es 10-40x más lento (probado con 2 M líneas).
DEFAULT_SIM_TH = 0.7


def make_miner(sim_th: float) -> TemplateMiner:
    """Drain con profundidad 4 (la que usa Loghub para HDFS).

    Los identificadores de bloque y las direcciones IP se enmascaran antes de agrupar,
    para que dos mensajes iguales salvo por esos valores caigan en la misma plantilla.
    """
    cfg = TemplateMinerConfig()
    cfg.drain_depth = 4
    cfg.drain_sim_th = sim_th
    cfg.masking_instructions = [
        MaskingInstruction(BLOCK_ID_REGEX, "BLK"),
        MaskingInstruction(r"/?(?:\d+\.){3}\d+(?::\d+)?", "IP"),
    ]
    cfg.parametrize_numeric_tokens = True
    cfg.profiling_enabled = False
    return TemplateMiner(config=cfg)


def loghub_patterns() -> list[tuple[str, re.Pattern, int]]:
    """Plantillas oficiales de Loghub como regex: '[*]' significa 'cualquier texto'."""
    tpl = pd.read_csv(LOGHUB_TEMPLATES)
    out = []
    for eid, t in zip(tpl["EventId"], tpl["EventTemplate"]):
        literals = [p for p in t.split("[*]")]
        rx = re.compile(".*".join(re.escape(p.strip()) for p in literals), re.DOTALL)
        out.append((eid, rx, sum(len(p.strip()) for p in literals)))
    return out


def name_cluster(template: str, patterns) -> str:
    """EventId de Loghub cuya plantilla coincide con la de Drain (la más específica si hay varias)."""
    hits = [(spec, eid) for eid, rx, spec in patterns if rx.search(template)]
    return max(hits)[1] if hits else "UNMATCHED"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0, help="procesar solo las primeras N líneas")
    ap.add_argument("--sim-th", type=float, default=DEFAULT_SIM_TH, help="umbral de similitud de Drain")
    args = ap.parse_args()
    if not LOG_FILE.exists():
        raise SystemExit(f"No existe {LOG_FILE}. Ejecuta primero: python src/download.py --full")

    miner = make_miner(args.sim_th)
    line_ids, block_ids, cluster_ids = [], [], []
    bad_header = no_block = 0
    t0 = time.time()
    total_est = 11_175_629 if not args.limit else args.limit

    with open(LOG_FILE, encoding="utf-8", errors="replace") as f:
        for n, line in enumerate(f, start=1):
            if args.limit and n > args.limit:
                n -= 1
                break
            m = HEADER.match(line.rstrip("\n"))
            if not m:
                bad_header += 1
                continue
            content = m.group(6)
            cid = miner.add_log_message(content)["cluster_id"]
            blocks = list(dict.fromkeys(BLOCK.findall(content)))
            if not blocks:
                no_block += 1
            for b in blocks:
                line_ids.append(n)
                block_ids.append(b)
                cluster_ids.append(cid)
            if n % 500_000 == 0:
                el = time.time() - t0
                print(f"  {n:>11,} líneas · {n / el:,.0f} líneas/s · faltan ~{(total_est - n) / (n / el) / 60:.1f} min · "
                      f"{len(miner.drain.clusters)} clusters", flush=True)

    el = time.time() - t0
    print(f"Parsing terminado: {n:,} líneas en {el / 60:.1f} min ({n / el:,.0f} líneas/s)")
    print(f"  líneas con formato inesperado: {bad_header:,} · líneas sin BlockId: {no_block:,}")

    patterns = loghub_patterns()
    clusters = pd.DataFrame(
        [(c.cluster_id, c.size, c.get_template()) for c in miner.drain.clusters],
        columns=["ClusterId", "Size", "DrainTemplate"],
    ).sort_values("Size", ascending=False)
    clusters["EventId"] = clusters["DrainTemplate"].map(lambda t: name_cluster(t, patterns))

    PROCESSED.mkdir(parents=True, exist_ok=True)
    clusters.to_csv(TEMPLATES_OUT, index=False)
    pd.DataFrame({
        "LineId": np.asarray(line_ids, dtype=np.int32),
        "BlockId": pd.Categorical(block_ids),
        "ClusterId": np.asarray(cluster_ids, dtype=np.int16),
    }).to_parquet(PAIRS_OUT)

    unmatched = clusters[clusters["EventId"] == "UNMATCHED"]
    print(f"\n{len(clusters)} clusters de Drain → {clusters['EventId'].nunique()} EventIds de Loghub "
          f"· sin nombre: {len(unmatched)} clusters ({unmatched['Size'].sum():,} líneas)")
    with pd.option_context("display.max_colwidth", 90, "display.width", 200):
        print(clusters.to_string(index=False))
    print(f"\nGuardado: {PAIRS_OUT.name} ({len(line_ids):,} pares línea-bloque) y {TEMPLATES_OUT.name}")


if __name__ == "__main__":
    main()
