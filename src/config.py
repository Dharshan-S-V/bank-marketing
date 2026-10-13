"""Central configuration: paths, seeds, column groups, dataset metadata."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_CSV = DATA_DIR / "raw" / "bank-full.csv"
OUT = ROOT / "outputs"
FIG_DIR = OUT / "figures"
TAB_DIR = OUT / "tables"
RES_DIR = OUT / "results"
MODEL_DIR = OUT / "models"
for _d in (FIG_DIR, TAB_DIR, RES_DIR, MODEL_DIR, OUT / "interactive"):
    _d.mkdir(parents=True, exist_ok=True)

SEED = 42

# --- Dataset metadata (UCI Machine Learning Repository, dataset id 222) ---
UCI_PAGE = "https://archive.ics.uci.edu/dataset/222/bank+marketing"
UCI_ZIP = "https://archive.ics.uci.edu/static/public/222/bank+marketing.zip"
# Fallback mirror of the same file (used when UCI is unreachable, e.g. on restricted networks)
MIRROR_CSV = "https://raw.githubusercontent.com/samikabir/BankMarketingPrediction/master/bank-full.csv"
EXPECTED_SHAPE = (45211, 17)  # as documented by UCI: 45,211 instances = 16 inputs + 1 target

TARGET = "y"
NUMERIC = ["age", "balance", "day", "duration", "campaign", "pdays", "previous"]
CATEGORICAL = ["job", "marital", "education", "default", "housing", "loan",
               "contact", "month", "poutcome"]
MONTH_ORDER = ["jan", "feb", "mar", "apr", "may", "jun",
               "jul", "aug", "sep", "oct", "nov", "dec"]

# Model feature groups. `duration` is excluded from the primary ("pre-call") model: it is only
# known after the call ends, so using it would leak the outcome in any realistic deployment.
MODEL_NUMERIC = ["age", "balance", "day", "campaign", "pdays_clean", "previous"]
MODEL_BINARY = ["previously_contacted"]
