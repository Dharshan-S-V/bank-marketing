"""Generate and execute notebooks/eda_and_modeling.ipynb:  python scripts/build_notebook.py

The notebook calls the reusable modules in src/ and shows the outputs. Markdown interpretations are
produced by src/narrative.py from the executed results, so they match the numbers in the outputs.
"""
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import nbformat as nbf  # noqa: E402
import pandas as pd  # noqa: E402
from nbconvert.preprocessors import ExecutePreprocessor  # noqa: E402

from src.config import RES_DIR  # noqa: E402
from src.data_loader import get_data  # noqa: E402
from src.eda import run_eda  # noqa: E402
from src.narrative import abstract, conclusions, eda_figure_notes, key_findings, model_figure_notes  # noqa: E402
from src.preprocessing import clean, split_data  # noqa: E402

raw = get_data(); cdf = clean(raw); train, val, test = split_data(cdf)
R = run_eda(raw, cdf, train, save=False)
MR = json.loads((RES_DIR / "model_results.json").read_text())
hist = json.loads((RES_DIR / "history_primary.json").read_text())
NOTES = {**eda_figure_notes(cdf, R), **model_figure_notes(MR, dict(
    hist=hist, imp=pd.read_csv(RES_DIR / "permutation_importance.csv"), search=pd.read_csv(RES_DIR / "hparam_search.csv"), m_test=MR["primary"]["test"]))}

nb = nbf.v4.new_notebook(); C = nb.cells
md = lambda s: C.append(nbf.v4.new_markdown_cell(s))  # noqa: E731
code = lambda s: C.append(nbf.v4.new_code_cell(s))  # noqa: E731


def note_md(n):
    t = {k: v.replace('|', '\\|') for k, v in NOTES[n].items()}
    return (f"**Figure {n} - {t['title']}**\n\n| | |\n|---|---|\n| **Question** | {t['question']} |\n| **What it shows** | {t['what']} |\n| **Why this chart** | {t['why']} |\n"
            f"| **Variables** | {t['variables']} |\n| **Finding** | {t['finding']} |\n| **Interpretation** | {t['interpretation']} |\n| **Caveats** | {t['caveats']} |")


md("""# Exploratory Data Analysis and Visualization of Bank Telemarketing Campaigns
**Course:** U21ADP05 Exploratory Data Analysis and Visualization - KPR Institute of Engineering and Technology (Assignment II)  
**Dataset:** UCI *Bank Marketing* (Moro, Cortez & Rita, 2014) - 45,211 calls, 16 input features + target `y` (term-deposit subscription)

This notebook follows the **seven stages of visualization** (Fry, 2007): Acquire -> Parse -> Filter -> Mine -> Represent -> Refine -> Interact, then builds and evaluates a deep-learning model (MLP).
All reusable code lives in `src/`; the notebook calls it and shows the results. Run it from the repository root or from `notebooks/`.

| Stage | Where |
|---|---|
| 1 Acquire | Section 1 |
| 2 Parse | Section 2 |
| 3 Filter | Section 3 |
| 4 Mine | Section 4 |
| 5 Represent, 6 Refine | Section 5 |
| 7 Interact | Section 6 |
| Deep learning + evaluation | Sections 7-8 |""")
code("""import sys, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT))

import json
import numpy as np, pandas as pd
from IPython.display import Image, display, Markdown
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 30)

from src.config import FIG_DIR, RES_DIR, RAW_CSV
from src.data_loader import get_data, sha256
from src.preprocessing import clean, split_data, prepare_matrices
from src.eda import run_eda, structure_report, quality_report, before_after_skew
from src.visualizations import make_all_eda_figures
""")
md("## 1. Acquire\nDownload (UCI first, verified mirror as fallback), validate shape/columns and record a checksum.")
code("""raw = get_data()
print("shape:", raw.shape, "| SHA-256:", sha256(RAW_CSV))
raw.head()""")
md("## 2. Parse\nStructure, data types and data quality. The file has no NaN cells, but missing information is hidden in `'unknown'` labels and the sentinel `pdays = -1`.")
code("""display(structure_report(raw))
display(quality_report(raw))
display(raw.sample(5, random_state=42))""")
md("## 3. Filter\nCleaning, feature construction, leakage-safe preprocessing and train/validation/test splitting. Learned transformations (caps, scalers, one-hot categories) are **fitted on the training split only**.")
code("""cdf = clean(raw)
train, val, test = split_data(cdf, "stratified")
print({k: (len(v), round(v.y_bin.mean(), 4)) for k, v in dict(train=train, val=val, test=test).items()})
Xtr, Xva, Xte, ytr, yva, yte, pre, names = prepare_matrices(train, val, test)
print("model inputs:", len(names), "| train matrix:", Xtr.shape)
display(before_after_skew(train, Xtr, names).round(2))""")
md("## 4. Mine\nAll statistics (univariate, distribution fitting, bivariate tests, logistic regression) are computed in `src/eda.py`.")
code("""R = run_eda(raw, cdf, train, save=False); T = R["_tables"]
display(T["numeric_summary"].round(2))
display(T["outliers_iqr"].round(2))""")
code("""print("Bernoulli outcome:", {k: round(v, 4) for k, v in R["bernoulli"].items()})
display(pd.DataFrame([R["campaign_counts"], R["previous_counts"]]).set_index("variable").T.round(3))
display(T["fit_age"]); display(T["fit_duration"])""")
code("""display(T["mannwhitney"].round(3)); display(T["chi2_target"].round(3))
display(T["logit_odds_ratios"].assign(effect=lambda d: np.abs(np.log(d.odds_ratio))).sort_values("effect", ascending=False).head(12).drop(columns="effect").round(3))
print("VIF max before/after removing redundant history variables:", round(R["vif"]["max_before"]), "->", round(R["vif"]["max_after"], 1))""")
md("## 5. Represent and 6. Refine - exploratory figures\nEach figure is followed by its question, what it shows, why the chart was chosen, the variables, the finding, interpretation and caveats.")
code("""figs = make_all_eda_figures(cdf, R)
print(len(figs), "figures saved to", FIG_DIR)""")
for n in range(1, 15):
    code(f"display(Image(str(FIG_DIR / '{[p for p in sorted((ROOT / 'outputs' / 'figures').glob(f'fig{n:02d}_*.png'))][0].name}'), width=900))")
    md(note_md(n))
md("### Key statistical findings")
md("\n".join(f"{i + 1}. **{f['obs']}** {f['stat']} ({f['chart']}). *Implication:* {f['impl']} *Caveat:* {f['cav']}" for i, f in enumerate(key_findings(cdf, R, MR))))
md("## 7. Interact\nStage 7: a self-contained Plotly explorer (dropdowns, hover, zoom). Open `outputs/interactive/explorer.html` in a browser.")
code("""from src.interactive import build_explorer
print("Open in your browser:", build_explorer(cdf))""")
md("## 8. Deep learning model (MLP) - training, evaluation and visualization\n"
   "Set `RETRAIN = True` to re-run the whole experiment (about 10-15 min on one CPU core; resumable). With `False` the notebook loads the saved results of the full run (`outputs/results/`), which come from executing `python -m src.train`.")
code("""RETRAIN = False
if RETRAIN:
    from src.train import run_experiments
    run_experiments(quick=False)
MR = json.loads((RES_DIR / "model_results.json").read_text())
assert not MR["quick_smoke_test"]
print("best config:", MR["best_config"], "| parameters:", MR["n_params"], "| inputs:", MR["n_inputs"])
print("\\n".join(MR["architecture_summary"]))""")
code("""rows = {"MLP (primary seed 42)": MR["primary"]["test"]}
rows.update({k: v["test"] for k, v in MR["baselines"].items()})
res = pd.DataFrame(rows).T[["roc_auc", "pr_auc", "f1", "precision", "recall", "accuracy", "balanced_accuracy", "mcc"]].round(3)
display(res)
print("MLP over 5 seeds (mean, sd):", {k: [round(x, 4) for x in v] for k, v in MR["test_mean_std"].items() if k in ("roc_auc", "pr_auc", "f1")})
display(pd.read_csv(RES_DIR / "hparam_search.csv").round(4))
display(pd.read_csv(RES_DIR / "robustness.csv").round(3))""")
code("""from src.evaluate import make_model_figures
mfigs, m_test = make_model_figures()
print({k: v.name for k, v in mfigs.items()})""")
for n in range(15, 23):
    code(f"display(Image(str(FIG_DIR / '{sorted((ROOT / 'outputs' / 'figures').glob(f'fig{n:02d}_*.png'))[0].name}'), width=850))")
    md(note_md(n))
Cn = conclusions(cdf, R, MR)
md("## 9. Conclusion and future scope\n**What was learned**\n" + "\n".join(f"- {x}" for x in Cn["learned"]) + "\n\n**Model**\n" + "\n".join(f"- {x}" for x in Cn["model"]) +
   "\n\n**Challenges**\n" + "\n".join(f"- {x}" for x in Cn["challenges"]) + "\n\n**Future scope**\n" + "\n".join(f"- {x}" for x in Cn["future"]))

nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
out = ROOT / "notebooks" / "eda_and_modeling.ipynb"
ep = ExecutePreprocessor(timeout=900, kernel_name="python3")
ep.preprocess(nb, {"metadata": {"path": str(ROOT / "notebooks")}})
nbf.write(nb, out)
print("executed and saved", out, out.stat().st_size // 1024, "KB")
