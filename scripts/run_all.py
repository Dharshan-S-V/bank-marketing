"""Run the whole pipeline end to end:  python scripts/run_all.py [--skip-train]

1 Acquire -> 2 EDA/statistics -> 3 EDA figures -> 4 DL experiments (resumable) -> 5 model figures
-> 6 interactive explorer -> 7 notebook + report.
"""
import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_loader import get_data  # noqa: E402
from src.eda import run_eda  # noqa: E402
from src.interactive import build_explorer  # noqa: E402
from src.preprocessing import clean, split_data  # noqa: E402
from src.visualizations import make_all_eda_figures  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--skip-train", action="store_true", help="reuse saved model artefacts in outputs/results")
ap.add_argument("--quick", action="store_true", help="smoke-test the training code only (not a full run)")
a = ap.parse_args()

raw = get_data(); cdf = clean(raw); train, val, test = split_data(cdf)
R = run_eda(raw, cdf, train)
print("EDA figures:", len(make_all_eda_figures(cdf, R)))
if not a.skip_train:
    from src.train import run_experiments
    run_experiments(quick=a.quick)
if not a.quick:
    from src.evaluate import make_model_figures
    figs, _ = make_model_figures(); print("Model figures:", len(figs))
print("Explorer:", build_explorer(cdf))
