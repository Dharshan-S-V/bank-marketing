"""Write README.md with the real numbers from the executed experiment:  python scripts/build_readme.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd  # noqa: E402

MR = json.loads((ROOT / "outputs/results/model_results.json").read_text())
ER = json.loads((ROOT / "outputs/results/eda_results.json").read_text())
S, P, B, CH = MR["test_mean_std"], MR["primary"]["test"], MR["baselines"], MR["chronological"]
rob = pd.read_csv(ROOT / "outputs/results/robustness.csv")
dur = MR["duration_ablation_mlp"]["test_roc_auc"]
bc = MR["best_config"]

readme = f"""# Bank Telemarketing: EDA, Statistical Visualization and Deep Learning

Case study for **U21ADP05 - Exploratory Data Analysis and Visualization** (KPR Institute of Engineering and Technology, Assignment II, 2026-27 odd semester).
Student: Dharshan - Roll no. 23AM019. Final report: [`reports/final_report.pdf`](reports/final_report.pdf) ([.docx](reports/final_report.docx)).

## 1. Problem statement
A Portuguese bank sold term deposits by telephone. Only {ER['bernoulli']['p_hat'] * 100:.1f}% of {ER['n_rows']:,} calls succeeded. Which client and campaign factors are associated with success,
and how well can a neural network rank clients by their probability of subscribing **using only information available before the call**?

## 2. Objectives
Acquire and document a real dataset (>= 15 features) - clean it without leakage - quantify univariate, distributional, bivariate and multivariate behaviour - communicate it with
interpreted visualizations covering the **seven stages** (Acquire, Parse, Filter, Mine, Represent, Refine, Interact) - build and honestly evaluate a deep-learning model - state conclusions, limitations and future scope.

## 3. Dataset
UCI Machine Learning Repository **Bank Marketing** (id 222), `bank-full.csv`: {ER['n_rows']:,} rows, 16 input features (7 numeric, 9 categorical) + target `y`.
Source: <https://archive.ics.uci.edu/dataset/222/bank+marketing>. Citation: Moro, Cortez & Rita (2014), *Decision Support Systems* 62:22-31, doi:10.1016/j.dss.2014.03.001.
The file is included in `data/raw/`; `python -m src.data_loader` re-downloads and validates it (UCI first, mirror fallback; manual fallback in [`data/README.md`](data/README.md)).
Data dictionary: [`data/data_dictionary.csv`](data/data_dictionary.csv).

## 4. Features and preprocessing
* No NaN cells, but hidden missingness: `'unknown'` labels (poutcome 81.7%, contact 28.8%, education 4.1%) and the sentinel `pdays = -1` (81.7%). `unknown` is kept as a category; `pdays` becomes a flag + cleaned value.
* No duplicates; outliers retained and tamed with signed-log (balance) or cap-at-train-99th-percentile + log (campaign, previous); one-hot encoding + standardisation, **all fitted on the training split only**.
* `duration` (call length) is **excluded** from the primary model - it is only known after the call (leakage). A sensitivity run includes it.
* Splits: 70/15/15 stratified (primary) and chronological (robustness check).

## 5. Statistical analysis (CO4)
Univariate summaries; **Bernoulli** outcome model; **Poisson vs Negative Binomial** for `campaign` and `previous` (variance/mean = {ER['campaign_counts']['dispersion_index_var_over_mean']:.1f} and {ER['previous_counts']['dispersion_index_var_over_mean']:.1f} -> NB far better);
**Normal / Lognormal / Gamma** for age and **Exponential / Lognormal / Gamma / Weibull** for duration (AIC, KS distance, Q-Q plots); Spearman vs Pearson, Mann-Whitney + Cliff's delta, chi-square + Cramer's V,
Kruskal-Wallis, and a logistic regression with VIF diagnostics (max VIF {ER['vif']['max_before']:.0f} -> {ER['vif']['max_after']:.1f} after removing redundant history variables).

## 6. The seven visualization stages
| Stage | Evidence |
|---|---|
| 1 Acquire | `src/data_loader.py` - download, validation, SHA-256 |
| 2 Parse | structure + data-quality tables (notebook section 2) |
| 3 Filter | `src/preprocessing.py` - cleaning, transforms, splits |
| 4 Mine | `src/eda.py` - statistics and tests (`outputs/tables/`) |
| 5 Represent | Figures 1-22 in `outputs/figures/` |
| 6 Refine | integer-aligned bins, log scales, CIs, annotated n, consistent colours |
| 7 Interact | `outputs/interactive/explorer.html` (Plotly) |

## 7. Main findings
* Outcome is imbalanced (11.7% yes); accuracy of always-"no" is 88.3%, so ROC-AUC / PR-AUC / F1 are used.
* Previous campaign success converts at 64.7% (vs 9.2% for unknown); calling month matters (busy May: 6.7%; Mar/Sep/Oct/Dec: 44-52% on few calls); age is U-shaped; housing/personal loans go with lower subscription.
* Contact counts are over-dispersed (Poisson rejected, NB preferred); call duration is lognormal-like, not exponential.
* All findings are associations, not causal effects; `contact = unknown` is confounded with May-June.

## 8. Deep-learning model
MLP (TensorFlow/Keras): {MR['n_inputs']} inputs -> Dense({bc['units'][0]}, ReLU, L2 1e-4) -> Dropout({bc['dropout']}) -> Dense(1, sigmoid); {MR['n_params']:,} parameters; Adam (lr {bc['lr']}), binary cross-entropy,
batch {MR['batch_size']}, up to {MR['max_epochs']} epochs with early stopping on validation AUC. Configuration chosen by a {MR['n_search_configs']}-configuration random search on the validation set; threshold ({MR['primary']['val']['threshold']:.3f}) chosen on validation to maximise F1.
Seeds: primary 42; final configuration repeated with seeds {MR['seeds']}.

## 9. Results (untouched test set, n = {MR['split_sizes'][2]:,})
| Model | ROC-AUC | PR-AUC | F1 |
|---|---|---|---|
| **MLP (mean +/- SD, 5 seeds)** | **{S['roc_auc'][0]:.3f} +/- {S['roc_auc'][1]:.3f}** | {S['pr_auc'][0]:.3f} +/- {S['pr_auc'][1]:.3f} | {S['f1'][0]:.3f} +/- {S['f1'][1]:.3f} |
| MLP (primary seed 42) | {P['roc_auc']:.3f} | {P['pr_auc']:.3f} | {P['f1']:.3f} |
| Logistic regression | {B['Logistic regression']['test']['roc_auc']:.3f} | {B['Logistic regression']['test']['pr_auc']:.3f} | {B['Logistic regression']['test']['f1']:.3f} |
| Gradient boosting (reference) | {B['Gradient boosting (reference)']['test']['roc_auc']:.3f} | {B['Gradient boosting (reference)']['test']['pr_auc']:.3f} | {B['Gradient boosting (reference)']['test']['f1']:.3f} |
| Always "no" | 0.500 | {B['Majority class']['test']['pr_auc']:.3f} | {B['Majority class']['test']['f1']:.3f} |

At the chosen threshold: precision {P['precision']:.2f}, recall {P['recall']:.2f}, accuracy {P['accuracy']:.3f}.
No overfitting was observed (training and validation losses coincide). Robustness: adding the leaky `duration` feature lifts the MLP to ROC-AUC {dur:.3f}
(not usable pre-call); on a chronological split performance falls to {CH['mlp']['test']['roc_auc']:.3f} because the positive rate shifts from {CH['train_prev'] * 100:.1f}% to {CH['test_prev'] * 100:.1f}%.
The model beats logistic regression but not gradient boosting, and it is **not** presented as deployment-ready.

## 10. Installation
```bash
git clone https://github.com/<your-username>/bank-marketing-eda-dl.git
cd bank-marketing-eda-dl
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt                          # exact tested versions: requirements-lock.txt
```

## 11. How to run
```bash
python -m src.data_loader                 # download + validate the dataset
python scripts/run_all.py                 # EDA, all figures, full DL experiment, explorer (~10-15 min, CPU)
python scripts/run_all.py --skip-train    # reuse saved model results (about 1 min)
python scripts/run_all.py --quick         # smoke test of the training code ONLY (not a full run)
python scripts/build_notebook.py          # regenerate + execute notebooks/eda_and_modeling.ipynb
python scripts/build_report.py            # regenerate reports/final_report.docx
pytest -q                                 # 30 automated tests
```
Training is resumable (per-step cache in `outputs/results/_cache/`, git-ignored). Open `notebooks/eda_and_modeling.ipynb` for the guided walkthrough.

## 12. Repository structure
```
bank-marketing-eda-dl/
|-- README.md, requirements.txt, requirements-lock.txt, .gitignore
|-- data/ (raw/bank-full.csv, data_dictionary.csv, README.md)
|-- notebooks/eda_and_modeling.ipynb        executed notebook
|-- src/  config, data_loader, preprocessing, eda, visualizations, model, train, evaluate, interactive, narrative, data_dictionary
|-- scripts/ run_all, build_notebook, build_report, build_readme, rubric
|-- tests/test_pipeline.py                  30 tests (data, leakage, splits, stats, model, metrics)
|-- outputs/ figures/ (22 PNG), tables/ (CSV), results/ (JSON, predictions), models/, interactive/explorer.html
|-- reports/ final_report.pdf, final_report.docx
`-- docs/ REQUIREMENTS_CHECKLIST.md, RUBRIC_CHECKLIST.md, SUBMISSION_CHECKLIST.md
```

## 13. Limitations and future scope
Observational data from one bank; no year/client identifiers; strong temporal shift; modest predictive ceiling with pre-call features. Future work: the richer `bank-additional` data (macro-economic variables),
count/hurdle models, spline effects for age, calibrated gradient boosting, cost-sensitive thresholds, rolling-origin validation, fairness review and a pilot test before any deployment.

## 14. Submission
Public GitHub link -> Google Form: <https://forms.gle/kT9DU5aERo2peTNh8> (deadline 15 Oct 2026). See [`docs/SUBMISSION_CHECKLIST.md`](docs/SUBMISSION_CHECKLIST.md).
"""
(ROOT / "README.md").write_text(readme, encoding="utf-8")
print("README.md written", len(readme.split()), "words")
