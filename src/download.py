"""Etapa 1 · Obtención de datos.

Uso:
    python src/download.py            # solo la muestra de Loglizer (~39 MB)
    python src/download.py --full     # además, HDFS_v1 completo de Loghub (~187 MB comprimido)
"""
import argparse
import zipfile
from pathlib import Path

import requests

from config import FULL_DIR, FULL_URL, FULL_ZIP, ROOT, SAMPLE_URLS


def download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  ya existe: {dest.relative_to(ROOT)}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))  # tamaño en la red (puede venir comprimido)
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                if total:
                    done = min(r.raw.tell(), total)  # bytes recibidos, antes de descomprimir
                    print(f"\r  {dest.name}: {done / total:6.1%} de {total / 1e6:.0f} MB", end="", flush=True)
    print()
    tmp.rename(dest)  # solo se renombra si la descarga terminó completa


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true", help="descargar también HDFS_v1 completo")
    args = ap.parse_args()

    print("Muestra de Loglizer")
    for dest, url in SAMPLE_URLS.items():
        download(url, dest)

    if args.full:
        print("HDFS_v1 completo (Loghub / Zenodo)")
        download(FULL_URL, FULL_ZIP)
        if not (FULL_DIR / "HDFS.log").exists():
            print("  descomprimiendo...")
            with zipfile.ZipFile(FULL_ZIP) as z:
                z.extractall(FULL_DIR)
        print(f"  contenido: {sorted(p.name for p in FULL_DIR.rglob('*') if p.is_file())}")


if __name__ == "__main__":
    main()
