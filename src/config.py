"""Rutas y constantes compartidas por todo el pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
ARTIFACTS = ROOT / "artifacts"
MODELS_DIR = ARTIFACTS / "models"

# Muestra preprocesada de Loglizer (primeras ~100k líneas, ya parseadas con Drain)
SAMPLE_DIR = RAW / "loglizer_sample"
SAMPLE_STRUCTURED = SAMPLE_DIR / "HDFS_100k.log_structured.csv"
SAMPLE_LABELS = SAMPLE_DIR / "anomaly_label.csv"
SAMPLE_URLS = {
    SAMPLE_STRUCTURED: "https://raw.githubusercontent.com/logpai/loglizer/master/data/HDFS/HDFS_100k.log_structured.csv",
    SAMPLE_LABELS: "https://raw.githubusercontent.com/logpai/loglizer/master/data/HDFS/anomaly_label.csv",
}

# Dataset completo de Loghub (logs en bruto)
FULL_DIR = RAW / "HDFS_v1"
FULL_ZIP = RAW / "HDFS_v1.zip"
FULL_URL = "https://zenodo.org/api/records/8196385/files/HDFS_v1.zip/content"

# Un bloque de HDFS se identifica como blk_<entero con signo>
BLOCK_ID_REGEX = r"blk_-?\d+"

SEED = 42
TEST_SIZE = 0.20
CV_FOLDS = 5
