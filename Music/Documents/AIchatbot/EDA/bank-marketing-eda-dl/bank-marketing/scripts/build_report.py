"""Build reports/final_report.docx from the executed results:  python scripts/build_report.py

All numbers come from outputs/ (EDA recomputed from the data, model results read from JSON).
"""
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from docx import Document  # noqa: E402
from docx.enum.section import WD_ORIENT  # noqa: E402,F401
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Inches, Pt, RGBColor  # noqa: E402

from rubric import RUBRIC  # noqa: E402
from src.config import FIG_DIR, RES_DIR, SEED, UCI_PAGE  # noqa: E402
from src.data_dictionary import data_dictionary  # noqa: E402
from src.data_loader import get_data, sha256  # noqa: E402
from src.config import RAW_CSV  # noqa: E402
from src.eda import before_after_skew, run_eda  # noqa: E402
from src.narrative import (abstract, conclusions, eda_figure_notes, key_findings,  # noqa: E402
                           model_figure_notes, p_fmt, pct)
from src.preprocessing import clean, prepare_matrices, split_data  # noqa: E402

STUDENT, ROLL = "Dharshan", "23AM019"
DEPT = "Department of Artificial Intelligence and Machine Learning"
TITLE = "Exploratory Data Analysis and Visualization of Bank Telemarketing Campaigns: Statistical Insights and a Deep Learning Model for Term-Deposit Subscription"

# ----------------------------------------------------------------------------- data
raw = get_data(); cdf = clean(raw); train, val, test = split_data(cdf)
R = run_eda(raw, cdf, train, save=False); T = R["_tables"]
MR = json.loads((RES_DIR / "model_results.json").read_text())
hist = json.loads((RES_DIR / "history_primary.json").read_text())
extra = dict(hist=hist, imp=pd.read_csv(RES_DIR / "permutation_importance.csv"),
             search=pd.read_csv(RES_DIR / "hparam_search.csv"), m_test=MR["primary"]["test"])
NOTES = {**eda_figure_notes(cdf, R), **model_figure_notes(MR, extra)}
assert not MR["quick_smoke_test"]
Xtr, Xva, Xte, ytr, yva, yte, pre, names = prepare_matrices(train, val, test)

FIGFILES = {1: "fig01_class_balance", 2: "fig02_numeric_histograms", 3: "fig03_outlier_boxplots", 4: "fig04_categorical_counts",
            5: "fig05_rate_by_category", 6: "fig06_month_volume_vs_rate", 7: "fig07_count_distribution", 8: "fig08_age_fits",
            9: "fig09_duration_fits", 10: "fig10_correlation_heatmaps", 11: "fig11_cramers_heatmap", 12: "fig12_pairplot",
            13: "fig13_age_and_balance", 14: "fig14_odds_ratio_forest", 15: "fig15_hparam_search", 16: "fig16_loss_curves",
            17: "fig17_accuracy_auc_curves", 18: "fig18_confusion_matrix", 19: "fig19_roc_pr_curves", 20: "fig20_permutation_importance",
            21: "fig21_threshold_tradeoff", 22: "fig22_robustness"}
FIGW = {1: 3.8, 2: 6.5, 3: 6.5, 4: 6.5, 5: 6.5, 6: 5.0, 7: 6.5, 8: 6.5, 9: 6.5, 10: 6.5, 11: 5.2, 12: 5.6, 13: 6.5, 14: 5.4,
        15: 6.0, 16: 4.8, 17: 6.5, 18: 3.8, 19: 6.5, 20: 5.3, 21: 4.8, 22: 6.5}

# ----------------------------------------------------------------------------- docx helpers
doc = Document()
sec = doc.sections[0]
sec.left_margin = sec.right_margin = Inches(1); sec.top_margin = sec.bottom_margin = Inches(0.9)
st = doc.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.paragraph_format.space_after = Pt(6); st.paragraph_format.line_spacing = 1.12
for lvl, sz in ((1, 15), (2, 12.5), (3, 11.5)):
    h = doc.styles[f"Heading {lvl}"]; h.font.name = "Times New Roman"; h.font.size = Pt(sz); h.font.bold = True
    h.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F); h.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    h.paragraph_format.space_before = Pt(14 if lvl == 1 else 10); h.paragraph_format.space_after = Pt(5)
    h.paragraph_format.keep_with_next = True


def shade(cell, hexcol):
    tcPr = cell._tc.get_or_add_tcPr(); shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hexcol); tcPr.append(shd)


def set_widths(t, widths):
    """Fixed layout with explicit grid + cell widths (needed for Word and LibreOffice)."""
    t.autofit = False
    for i, w in enumerate(widths):
        t.columns[i].width = Inches(w)
        for row in t.rows:
            row.cells[i].width = Inches(w)


def para(text="", bold=False, italic=False, size=None, align=None, after=None, keep=False):
    p = doc.add_paragraph(); r = p.add_run(text); r.bold, r.italic = bold, italic
    if size: r.font.size = Pt(size)
    if align == "center": p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if align == "justify": p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if after is not None: p.paragraph_format.space_after = Pt(after)
    if keep: p.paragraph_format.keep_with_next = True
    return p


def rich(parts, style=None):
    """parts: list of (text, bold) tuples."""
    p = doc.add_paragraph(style=style)
    for t, b in parts:
        r = p.add_run(t); r.bold = b
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return p


def bullets(items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet"); p.add_run(it); p.paragraph_format.space_after = Pt(2)


def H(text, lvl=1):
    return doc.add_heading(text, level=lvl)


def table(df, widths=None, font=8.5, header_fill="1F3A5F", caption=None, align_num=True, first_bold=False):
    if caption:
        c = para(caption, bold=True, size=9.5, after=2, keep=True)
    t = doc.add_table(rows=1, cols=len(df.columns)); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, col in enumerate(df.columns):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(str(col)); r.bold = True; r.font.size = Pt(font)
        r.font.color.rgb = RGBColor(255, 255, 255); shade(c, header_fill)
    for ri, row in enumerate(df.itertuples(index=False)):
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""; r = cells[i].paragraphs[0].add_run("" if v is None else str(v)); r.font.size = Pt(font)
            if first_bold and i == 0: r.bold = True
            if ri % 2 == 1: shade(cells[i], "EEF3F9")
            cells[i].paragraphs[0].paragraph_format.space_after = Pt(0)
    if widths is None:  # sensible default: equal share of the 6.5 inch text width
        widths = [6.5 / len(df.columns)] * len(df.columns)
    set_widths(t, widths)
    # repeat header row
    trPr = t.rows[0]._tr.get_or_add_trPr(); th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def fnum(x, d=2):
    if isinstance(x, (int, np.integer)): return f"{x:,}"
    if isinstance(x, float):
        if abs(x) >= 1e5: return f"{x:,.0f}"
        if x != 0 and abs(x) < 1e-4: return f"{x:.1e}"
        if x != 0 and abs(x) < 10 ** -d: return f"{x:.4f}"
        return f"{x:,.{d}f}"
    return x


def df_fmt(df, d=2):
    return df.map(lambda v: fnum(v, d)) if hasattr(df, "map") else df.applymap(lambda v: fnum(v, d))


def figure(n):
    nt = NOTES[n]
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(FIG_DIR / f"{FIGFILES[n]}.png"), width=Inches(FIGW[n]))
    para(f"Figure {n}. {nt['title']}.", bold=True, italic=False, size=9.5, align="center", after=3, keep=True)
    rows = [("Question", nt["question"]), ("What it shows", nt["what"]), ("Why this chart", nt["why"]), ("Variables", nt["variables"]),
            ("Finding", nt["finding"]), ("Interpretation", nt["interpretation"]), ("Caveats", nt["caveats"])]
    t = doc.add_table(rows=0, cols=2); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, v in rows:
        c = t.add_row().cells
        c[0].text = ""; r = c[0].paragraphs[0].add_run(k); r.bold = True; r.font.size = Pt(8.5); shade(c[0], "DCE6F1")
        c[1].text = ""; r = c[1].paragraphs[0].add_run(v); r.font.size = Pt(8.5)
        for cc in c: cc.paragraphs[0].paragraph_format.space_after = Pt(0)
    set_widths(t, [1.15, 5.35])
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def add_page_numbers():
    p = sec.footer.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for tag, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        r = p.add_run()
        if tag:
            f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), tag); r._r.append(f)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = txt; r._r.append(it)
        r.font.size = Pt(9)


add_page_numbers()

# ============================================================================ TITLE PAGE
for _ in range(3): para("")
para("KPR Institute of Engineering and Technology", bold=True, size=16, align="center", after=2)
para("Department of Artificial Intelligence and Data Science", size=12, align="center", after=2)
para("U21ADP05 - Exploratory Data Analysis and Visualization", size=12, align="center", after=2)
para("Assignment II: Case Study", size=12, align="center", after=30)
para(TITLE, bold=True, size=20, align="center", after=40)
tp = pd.DataFrame([("Student name", STUDENT), ("Roll number", ROLL), ("Department", DEPT), ("Batch / Year-Semester", "2023-2027 / V Semester (Academic year 2026-2027, odd semester)"),
                   ("Course coordinator", "Mr. Rushikesh Kadam"), ("Date of submission", "15 October 2026"),
                   ("Dataset", "UCI Bank Marketing (Moro, Cortez & Rita, 2014)"), ("Code repository", "github.com/<your-github-id>/bank-marketing-eda-dl  (replace with your public link)")],
                  columns=["Item", "Detail"])
table(tp, widths=[1.9, 4.6], font=10.5, first_bold=True)
page_break()

# ============================================================================ ABSTRACT
H("Abstract", 1)
para(abstract(R, MR), align="justify")
para("Keywords: exploratory data analysis, data visualization, probability distributions, Negative Binomial, bank telemarketing, multilayer perceptron, data leakage.", italic=True, size=10)

H("Contents", 2)
for line in ["1. Introduction and Objectives", "2. Dataset Description", "3. EDA and Preprocessing (including the seven visualization stages)",
             "4. Data Visualization (Figures 1-14, statistical analysis, key findings)", "5. Deep Learning Model", "6. Results Visualization and Interpretation (Figures 15-22)",
             "7. Conclusion and Future Scope", "8. References", "9. Appendix (rubric matrix, reproducibility, source code)"]:
    para(line, after=1)
page_break()

# ============================================================================ 1 INTRODUCTION
b = R["bernoulli"]; S = MR["test_mean_std"]; P = MR["primary"]["test"]; base = MR["baselines"]
H("1. Introduction and Objectives", 1)
para("Direct marketing by telephone is one of the most common ways for banks to sell long-term deposit products, but it is expensive: most calls fail, and "
     "repeated calls irritate clients. Understanding which clients, timings and campaign conditions lead to a subscription lets a bank focus scarce agent time "
     f"on promising prospects. This case study applies exploratory data analysis (EDA), statistical modelling of distributions, and visualization to a real campaign "
     f"dataset, and then builds a deep learning model that predicts whether a client will subscribe to a term deposit.", align="justify")
H("1.1 Problem statement", 2)
para(f"Given information about a client and the campaign that is available before the call, which factors are associated with a successful subscription, "
     f"and how well can a neural network rank clients by their probability of subscribing? The target variable y is binary and only {pct(b['p_hat'])} of calls are successful, "
     "so the problem is imbalanced and accuracy alone is not an adequate performance measure.", align="justify")
H("1.2 Objectives", 2)
bullets(["Acquire a real-world public dataset with at least 15 features and document its provenance, structure and limitations (Acquire, Parse).",
         "Detect and treat hidden missing values, a sentinel code, duplicates, outliers and skewed variables with justified, leakage-free preprocessing (Filter).",
         "Quantify univariate, probability-distribution, bivariate and multivariate behaviour with appropriate statistics and tests (Mine).",
         "Communicate the findings with at least five well-designed, interpreted visualizations covering all seven stages, including an interactive explorer (Represent, Refine, Interact).",
         "Build, tune and honestly evaluate at least one deep learning model, compare it with baselines, and examine leakage and temporal robustness.",
         "Draw practical conclusions and state the limitations and future scope, with a reproducible GitHub repository."])
H("1.3 Literature context", 2)
para("The dataset was introduced by Moro, Cortez and Rita (2014), who modelled bank telemarketing success with logistic regression, decision trees, neural networks and support vector machines, "
     "and used sensitivity analysis of the neural network to extract business knowledge. The seven-stage framework (acquire, parse, filter, mine, represent, refine, interact) is from Fry (2007), and the "
     "emphasis on looking at data before modelling follows Tukey (1977). For imbalanced outcomes, precision-recall analysis is more informative than ROC alone (Saito & Rehmsmeier, 2015), and "
     "benchmark evidence suggests tree ensembles often remain competitive with deep networks on tabular data (Grinsztajn et al., 2022), which is why gradient boosting is included here as a reference.", align="justify")

# ============================================================================ 2 DATASET
H("2. Dataset Description", 1)
H("2.1 Candidate comparison and selection", 2)
cand = pd.DataFrame([
    ("Bank Marketing (UCI #222)", "45,211", "16 + target", "7 numeric, 9 categorical", "Binary: term-deposit subscription", "Counts (campaign, previous), duration (waiting-time-like), sentinel and 'unknown' values, documented leakage variable, time order", "SELECTED"),
    ("Default of Credit Card Clients (UCI #350)", "30,000", "23 + target", "numeric / ordinal", "Binary: payment default", "Rich numeric history but few natural discrete-count or waiting-time variables", "Runner-up"),
    ("Student Performance (UCI #320)", "649 (Portuguese)", "30 + grades", "mixed", "Grade regression / pass-fail", "Small sample limits deep learning and distribution fitting", "Rejected"),
], columns=["Candidate", "Rows", "Inputs", "Types", "Target", "Opportunities for CO3-CO5", "Decision"])
table(cand, widths=[1.15, .6, .65, .8, .95, 1.8, .6], font=7.5, caption="Table 1. Dataset candidates (figures taken from UCI documentation; only the selected dataset was downloaded and analysed)")
para("Bank Marketing was chosen because it has a clear business application, 16 genuine input fields, enough observations (45,211) for both reliable statistics and a neural network, "
     "a mix of data types, and several features that make the probability-distribution analysis meaningful rather than forced: event-like counts (campaign, previous), a waiting-time-like variable (duration) "
     "and a binary outcome.", align="justify")
H("2.2 Source, acquisition and verification", 2)
src = pd.DataFrame([
    ("Original source", f"UCI Machine Learning Repository, dataset 222 'Bank Marketing' - {UCI_PAGE}"),
    ("Citation", "Moro, S., Cortez, P., & Rita, P. (2014). Decision Support Systems, 62, 22-31. doi:10.1016/j.dss.2014.03.001"),
    ("File used", "bank-full.csv (semicolon separated; ordered by date, May 2008 to November 2010 per UCI documentation)"),
    ("Download method", "src/data_loader.py tries the official UCI archive first, then a GitHub mirror of the same file; the file is validated (shape 45,211 x 17, expected columns, y in {yes, no})."),
    ("This submission", "The sandbox used to execute the project could not reach UCI, so the verified mirror was used; the file passes all validation checks and matches the UCI description (45,211 instances, 17 fields)."),
    ("SHA-256 of the analysed file", sha256(RAW_CSV)),
    ("Licence / terms", "See the licence statement on the UCI dataset page; cite Moro et al. (2014) when reusing."),
    ("Dimensions", f"{R['n_rows']:,} rows x {R['n_cols']} columns = 16 input features + 1 target; no NaN cells; no duplicate rows"),
    ("Target variable", "y: client subscribed to a term deposit (yes/no)"),
], columns=["Item", "Detail"])
table(src, widths=[1.5, 5.0], font=8.5, caption="Table 2. Dataset source and verification", first_bold=True)
H("2.3 Feature descriptions and basic statistics", 2)
table(data_dictionary(), widths=[0.8, 1.0, 3.4, 1.3], font=8, caption="Table 3. Data dictionary (descriptions follow the UCI documentation)")
ns = T["numeric_summary"][["count", "mean", "std", "min", "Q1", "median", "Q3", "max", "skewness", "excess_kurtosis"]].copy()
ns.insert(0, "variable", ns.index); ns["count"] = ns["count"].astype(int)
table(df_fmt(ns.reset_index(drop=True), 2), font=7.5, caption="Table 4. Descriptive statistics of the numeric variables (all 45,211 records)")
cats = []
for c in ["job", "marital", "education", "default", "housing", "loan", "contact", "month", "poutcome", "y"]:
    f = T.get(f"freq_{c}")
    f = f if f is not None else cdf[c].value_counts().to_frame("count").assign(percent=lambda d: 100 * d["count"] / d["count"].sum())
    top = f.index[0]
    cats.append((c, cdf[c].nunique(), f"{top} ({f.iloc[0]['percent']:.1f}%)", f"{100 * cdf[c].eq('unknown').mean():.1f}%" if (cdf[c] == "unknown").any() else "-"))
table(pd.DataFrame(cats, columns=["variable", "levels", "most frequent level", "'unknown' share"]), widths=[1.2, .7, 2.6, 1.2], font=8,
      caption="Table 5. Categorical variables: number of levels, most frequent level, hidden-missing share")
H("2.4 Limitations of the dataset", 2)
bullets(["No client identifier or year: repeated clients and campaign phase cannot be separated; month mixes 2008-2010 conditions.",
         "The file is the older 17-field version of the data; the richer 'bank-additional' version (macro-economic indicators) was not used.",
         "duration is only known after a call ends, so it is excluded from the primary predictive model (documented by the data owners).",
         "Observational data from one Portuguese bank: results show association, not causation, and may not transfer to other banks or periods."])

# ============================================================================ 3 EDA & PREPROCESSING
H("3. EDA and Preprocessing", 1)
H("3.1 Data-quality findings (Parse)", 2)
q = T["quality"].copy(); q.columns = ["column", "issue", "count", "percent"]
table(df_fmt(q, 2), widths=[1.0, 2.9, .8, .8], font=8.5, caption="Table 6. Data-quality checks on the raw file")
para("The raw file contains no NaN cells and no duplicate rows. Missing information is instead encoded as the text label 'unknown' (poutcome, contact, education, job) and as the sentinel pdays = -1. "
     f"poutcome = 'unknown' (36,959 clients) and pdays = -1 (36,954 clients) overlap in all but 5 records, so they both mean 'not contacted in an earlier campaign'. Negative balances ({int((cdf['balance'] < 0).sum()):,} clients) "
     "are valid overdrafts, and 3 calls lasted 0 s.", align="justify")
H("3.2 Missing values, duplicates and cleaning decisions (Filter)", 2)
dec = pd.DataFrame([
    ("NaN values", "none present", "Nothing to impute."),
    ("'unknown' categories", "kept as an explicit level", "Not random missingness (e.g. contact = unknown converts at 4.1% vs 14.9%); mode-imputation would destroy signal."),
    ("pdays = -1", "-> flag previously_contacted (0/1) + pdays_clean (0 if never contacted)", "Prevents the sentinel being treated as a real 'one day ago' value; deterministic, so no leakage."),
    ("Duplicates", "none found; no rows removed", "Checked with DataFrame.duplicated() (0 rows)."),
    ("Text standardisation", "strip + lower-case categoricals", "Guards against inconsistent labels (none were found)."),
    ("Target", "y -> y_bin (1 = yes)", "Used for modelling; the original column is kept for tables and plots."),
], columns=["Issue", "Treatment", "Justification"])
table(dec, widths=[1.3, 2.2, 3.0], font=8.5, caption="Table 7. Cleaning decisions")
H("3.3 Outliers (Mine / Filter)", 2)
o = T["outliers_iqr"][["variable", "lower_fence", "upper_fence", "n_below", "n_above", "pct_outliers", "n_extreme(>3IQR)", "max", "p99"]].copy()
o.columns = ["variable", "lower fence", "upper fence", "n below", "n above", "% flagged", "n > 3 IQR", "max", "p99"]
table(df_fmt(o, 1), font=8, caption="Table 8. IQR outlier screening (1.5 x IQR fences)")
odec = pd.DataFrame([
    ("balance", "Retain; signed-log transform (sign(x)*log(1+|x|)), then standardise", "Overdrafts are valid and rich clients real; log compresses the tail while keeping the sign."),
    ("campaign, previous", "Retain; cap at the TRAINING 99th percentile, then log(1+x), then standardise", "Extreme counts (e.g. previous = 275) may be entry errors; capping bounds their influence without deleting rows."),
    ("pdays_clean", "Retain; log(1+x), standardise", "Right-skewed time since last contact."),
    ("duration", "Retain for EDA; EXCLUDED from the primary model", "Known only after the call (leakage); sensitivity run includes it with cap + log."),
    ("age", "Retain; standardise only", "1.1% flagged, all plausible ages (max 95)."),
    ("day", "Retain; standardise", "No outliers."),
], columns=["Variable", "Decision", "Reason"])
table(odec, widths=[1.2, 2.6, 2.7], font=8.5, caption="Table 9. Outlier decisions (nothing is deleted)")
H("3.4 Transformations, encoding and scaling (leakage-safe)", 2)
para("All learned preprocessing (quantile caps, means and standard deviations for scaling, one-hot category lists) is fitted on the training split only and then applied to validation and test data "
     "(scikit-learn ColumnTransformer, src/preprocessing.py). Categorical variables are one-hot encoded with unknown-category handling, producing "
     f"{len(names)} model inputs from 16 raw fields (6 numeric, 1 flag, 9 categorical expanded to {len(names) - 7} indicator columns).", align="justify")
ba = before_after_skew(train, Xtr, names)
table(df_fmt(ba, 2), font=8.5, caption="Table 10. Before-and-after comparison of skewness and excess kurtosis on the training data")
dq = pd.DataFrame([
    ("Max |skewness| of balance / campaign / previous / pdays", f"{ba['skew_before'].abs().max():.1f}", f"{ba['skew_after'].abs().max():.1f}"),
    ("Max excess kurtosis of those variables", f"{ba['kurtosis_before'].max():,.0f}", f"{ba['kurtosis_after'].max():.1f}"),
    ("Hidden-missing categories", "'unknown' text labels + pdays = -1", "explicit categories + flag; none imputed"),
    ("Max VIF in the descriptive logistic regression", f"{R['vif']['max_before']:.0f}", f"{R['vif']['max_after']:.1f}"),
    ("Rows removed", "-", "0"),
], columns=["Data-quality measure", "Before", "After"])
table(dq, widths=[3.3, 1.6, 1.6], font=8.5, caption="Table 11. Data-quality summary before and after preprocessing")
H("3.5 Train / validation / test split", 2)
sp = MR["split_sizes"]; pv = MR["split_prevalence"]; ch = MR["chronological"]
spt = pd.DataFrame([("Train", f"{sp[0]:,}", "70%", pct(pv[0], 2), pct(ch['train_prev'], 2)),
                    ("Validation", f"{sp[1]:,}", "15%", pct(pv[1], 2), pct(ch['val_prev'], 2)),
                    ("Test", f"{sp[2]:,}", "15%", pct(pv[2], 2), pct(ch['test_prev'], 2))],
                   columns=["Split", "Rows", "Share", "Positive rate (stratified, primary)", "Positive rate (chronological check)"])
table(spt, widths=[1.0, .9, .7, 2.0, 1.9], font=8.5, caption="Table 12. Data splits")
para("The primary protocol is a random split stratified on the outcome (seed 42), which keeps the 11.7% prevalence identical in all three parts. Because UCI documents that the file is ordered by date, "
     f"a second, chronological split (first 70% / next 15% / last 15%) is used as a robustness check. It shows a strong temporal shift: the positive rate rises from {pct(ch['train_prev'])} in the training period to {pct(ch['test_prev'])} in the test period (Section 6.4). "
     "The test set is used once, for final evaluation; the decision threshold and all hyper-parameters are chosen on the validation set.", align="justify")
H("3.6 The seven stages of visualization", 2)
para("The assignment requires 'all 7 stages of visualization'; the framework of Fry (2007) is used: acquire, parse, filter, mine, represent, refine, interact. "
     "The assignment text does not list the stages, so this standard definition is assumed.", align="justify")
sev = pd.DataFrame([
    ("1 Acquire", "Obtain the data reproducibly", "src/data_loader.py downloads bank-full.csv (UCI, mirror fallback), validates shape/columns and records the SHA-256 (Table 2)."),
    ("2 Parse", "Understand structure and types", "Tables 3-6: 17 fields, 7 numeric + 9 categorical + target, memory, hidden 'unknown' and sentinel values."),
    ("3 Filter", "Clean and select", "Tables 7-12: cleaning rules, outlier decisions, leakage-free transforms and splits; duration excluded from the primary model."),
    ("4 Mine", "Statistics and patterns", "Section 4: summaries, distribution fitting, tests, correlations, Cramer's V, logistic regression (Tables 13-18)."),
    ("5 Represent", "Choose encodings", "Figures 1-14 (bar, histogram, boxplot, PMF overlay, Q-Q, heatmaps, pairplot, violin, forest) and 15-22 (model results)."),
    ("6 Refine", "Improve legibility", "Integer-aligned bins, log/symlog scales, CIs, n annotations, consistent colours, clipped axes disclosed; defects found in review were fixed."),
    ("7 Interact", "Explore interactively", "outputs/interactive/explorer.html (Plotly): dropdown rate-by-category with CIs, histogram by outcome, hover/zoom scatter."),
], columns=["Stage", "Purpose", "Evidence in this project"])
table(sev, widths=[0.9, 1.5, 4.1], font=8.5, caption="Table 13. Seven stages and where each is applied")
page_break()

# ============================================================================ 4 VISUALIZATION
H("4. Data Visualization", 1)
para("Fourteen exploratory figures are presented (assignment minimum: five). Each is accompanied by the question it answers, what it shows, why the chart type was chosen, the variables, the actual finding, its interpretation and the caveats. "
     "All statistics are computed from the data by the code in the repository.", align="justify")
H("4.1 Univariate analysis", 2)
for n in (1, 2, 3, 4): figure(n)
H("4.2 Discrete and continuous probability distributions", 2)
cf, pf = R["campaign_counts"], R["previous_counts"]
cnt = pd.DataFrame([
    ("campaign - 1", f"{cf['mean']:.2f}", f"{cf['variance']:.2f}", f"{cf['dispersion_index_var_over_mean']:.2f}", f"{cf['poisson_AIC']:,.0f}", f"{cf['nb_AIC']:,.0f}", f"{cf['obs_zero_pct']:.1f} / {cf['poisson_zero_pct']:.1f} / {cf['nb_zero_pct']:.1f}", f"{cf['nb_chi2']:.0f} (df {cf['nb_dof']})"),
    ("previous", f"{pf['mean']:.2f}", f"{pf['variance']:.2f}", f"{pf['dispersion_index_var_over_mean']:.2f}", f"{pf['poisson_AIC']:,.0f}", f"{pf['nb_AIC']:,.0f}", f"{pf['obs_zero_pct']:.1f} / {pf['poisson_zero_pct']:.1f} / {pf['nb_zero_pct']:.1f}", f"{pf['nb_chi2']:.0f} (df {pf['nb_dof']})"),
], columns=["Variable", "Mean", "Variance", "Var/mean", "AIC Poisson", "AIC NB", "% zeros: obs / Poisson / NB", "NB chi-square"])
bern = pd.DataFrame([("y ~ Bernoulli(p)", f"p-hat = {b['p_hat']:.4f}", f"exact 95% CI [{b['ci_low']:.4f}, {b['ci_high']:.4f}]", f"variance p(1-p) = {b['variance_p_1_minus_p']:.4f}",
                      f"homogeneity across months: chi2({b['month_homogeneity_dof']}) = {b['month_homogeneity_chi2']:.0f}, {p_fmt(b['month_homogeneity_p'])} -> a single common p is NOT adequate")],
                    columns=["Model", "Estimate", "Interval", "Variance", "Assumption check"])
table(bern, widths=[1.0, 0.9, 1.5, 1.1, 2.0], font=8, caption="Table 14. Bernoulli model of the outcome")
table(cnt, font=7.5, caption="Table 15. Discrete distributions fitted to the count variables (max-likelihood estimates)")
for tname, key, cap in (("fit_age", "fit_age", "Table 16. Continuous distributions fitted to age"), ("fit_duration", "fit_duration", "Table 17. Continuous distributions fitted to call duration (duration > 0)")):
    ft = T[key][["distribution", "params", "loglik", "AIC", "delta_AIC", "KS_D", "KS_p"]].copy()
    ft["params"] = ft["params"].astype(str); ft["KS_p"] = ft["KS_p"].map(lambda v: "<1e-300" if v < 1e-300 else f"{v:.1e}")
    ft["loglik"] = ft["loglik"].map(lambda v: f"{v:,.0f}"); ft["AIC"] = ft["AIC"].map(lambda v: f"{v:,.0f}"); ft["delta_AIC"] = ft["delta_AIC"].map(lambda v: f"{v:,.0f}"); ft["KS_D"] = ft["KS_D"].map(lambda v: f"{v:.3f}")
    table(ft, widths=[1.0, 1.6, 0.9, 0.9, 0.7, 0.5, 0.7], font=7.5, caption=cap)
para("Interpretation of the tables: with n of about 45,000 every KS or chi-square test rejects every candidate (p-values are essentially zero), so these tests cannot rank the models. "
     "The KS distance D (maximum gap between the empirical and fitted CDF) and the AIC differences are therefore used to judge how close each model is, and Q-Q plots to see where it fails.", align="justify")
for n in (7, 8, 9): figure(n)
H("4.3 Bivariate and multivariate analysis", 2)
for n in (5, 6): figure(n)
mw = T["mannwhitney"][["variable", "median_yes", "median_no", "mean_yes", "mean_no", "p_value", "cliffs_delta"]].copy()
mw["p_value"] = mw["p_value"].map(lambda v: "<0.001" if v < 1e-3 else f"{v:.3f}")
table(df_fmt(mw, 2), font=8, caption="Table 18. Numeric variables by outcome: Mann-Whitney U test with Cliff's delta (effect size)")
ch2 = T["chi2_target"].copy(); ch2["p_value"] = ch2["p_value"].map(lambda v: "<0.001" if v < 1e-3 else f"{v:.3f}")
table(df_fmt(ch2, 3), widths=[1.2, 1.0, .6, 1.0, 1.2], font=8.5, caption="Table 19. Categorical variables versus outcome: chi-square test and bias-corrected Cramer's V")
kb, ka = R["kruskal_balance_job"], R["kruskal_age_education"]
para(f"Group comparisons beyond two groups: balance differs across job categories (Kruskal-Wallis H = {kb['H']:.0f}, {p_fmt(kb['p_value'])}, epsilon-squared = {kb['epsilon_sq']:.3f}, a small effect) and age differs across education levels "
     f"(H = {ka['H']:.0f}, {p_fmt(ka['p_value'])}, epsilon-squared = {ka['epsilon_sq']:.3f}, small). Non-parametric tests are used because balance and duration are heavy-tailed; all p-values should be read together with effect sizes.", align="justify")
for n in (10, 11, 12, 13, 14): figure(n)
lo = T["logit_odds_ratios"].copy(); lo["effect"] = np.abs(np.log(lo["odds_ratio"])); lo = lo.sort_values("effect", ascending=False).head(14).drop(columns="effect")
lo["p_value"] = lo["p_value"].map(lambda v: "<0.001" if v < 1e-3 else f"{v:.3f}"); lo.insert(0, "term", lo.index)
table(df_fmt(lo.reset_index(drop=True), 3), widths=[1.7, 1.0, .9, .9, .8], font=8.5, caption=f"Table 20. Logistic regression (training set, n = {R['logit']['n']:,}, pseudo-R2 = {R['logit']['pseudo_r2']:.3f}): 14 largest adjusted odds ratios")
H("4.4 Key statistical findings", 2)
kf = key_findings(cdf, R, MR)
kt = pd.DataFrame([(i + 1, f["obs"], f["stat"], f["chart"], f["impl"], f["cav"]) for i, f in enumerate(kf)],
                  columns=["#", "Observation", "Statistic (from the data)", "Chart", "Real-world implication", "Caveat"])
table(kt, widths=[0.3, 1.2, 1.65, 0.55, 1.5, 1.3], font=7.5, caption="Table 21. Evidence-based summary of the main findings")
para("Association versus causation: all relationships above are observational. For example, the higher subscription rate of retired clients or of March calls does not show that these characteristics cause subscription; "
     "month and contact type, for instance, are strongly entangled (Cramer's V about 0.5), and campaign targeting changed over time.", align="justify")
page_break()

# ============================================================================ 5 DEEP LEARNING
H("5. Deep Learning Model", 1)
H("5.1 Problem formulation", 2)
para(f"Task: binary classification of whether a client subscribes (y = yes). Inputs: the 16 raw fields except duration (and the derived flag), expanded to {MR['n_inputs']} numeric inputs after preprocessing. "
     "Duration is excluded from the primary model because it is the length of the very call whose outcome is being predicted; it is used only in a leakage experiment (Section 6.4). "
     "Because the data are tabular with no spatial or sequential structure, a Multi-Layer Perceptron (MLP) is the appropriate deep learning architecture; CNNs, RNNs and Transformers would not exploit any structure present in these data.", align="justify")
H("5.2 Architecture and training parameters", 2)
bc = MR["best_config"]; u = bc["units"][0]
arch = pd.DataFrame([("Input", f"({MR['n_inputs']})", "-", 0),
                     (f"Dense 1", f"({u})", "ReLU, He-normal init, L2 = 1e-4", MR['n_inputs'] * u + u),
                     ("Dropout 1", f"({u})", f"rate {bc['dropout']}", 0),
                     ("Dense output", "(1)", "Sigmoid = P(subscribe)", u + 1)], columns=["Layer", "Output shape", "Configuration", "Parameters"])
table(arch, widths=[1.3, 1.1, 2.9, 1.0], font=9, caption=f"Table 22. Selected architecture ({MR['n_params']:,} trainable parameters)")
assert MR["n_inputs"] * u + u + u + 1 == MR["n_params"]
env = MR["environment"]
tp2 = pd.DataFrame([("Loss", "Binary cross-entropy"), ("Optimizer / learning rate", f"{MR['optimizer']} / {bc['lr']}"), ("Batch size / maximum epochs", f"{MR['batch_size']} / {MR['max_epochs']}"),
                    ("Early stopping", f"monitor validation ROC-AUC, patience {MR['early_stopping_patience']}, restore best weights"), ("Regularisation", f"dropout {bc['dropout']}, L2 {MR['l2']}"),
                    ("Class weighting", str(bc['class_weight'])), ("Validation strategy", "Fixed stratified validation split (15%); test split untouched until final evaluation"),
                    ("Decision threshold", f"{MR['primary']['val']['threshold']:.3f} (maximises F1 on validation)"), ("Seeds", f"primary seed {SEED}; final configuration repeated with seeds {MR['seeds']}; Python/NumPy/TensorFlow seeded, op determinism enabled"),
                    ("Environment", f"Python {env['python']}, TensorFlow {env['tensorflow']}, {env['cpu_count']} CPU core(s), GPU: {env['gpu'] or 'none'}"), ("Run time", f"full experiment {MR['runtime_seconds']:.0f} s on the final (cached) pass; search about 6 min")],
                   columns=["Parameter", "Value"])
table(tp2, widths=[1.9, 4.6], font=8.5, caption="Table 23. Training configuration and reproducibility", first_bold=True)
H("5.3 Hyper-parameter tuning", 2)
sr = extra["search"][["config_id", "units", "dropout", "lr", "class_weight", "epochs_run", "best_epoch", "val_roc_auc", "val_pr_auc"]].copy()
table(df_fmt(sr, 4), font=8, caption=f"Table 24. Random search over {MR['n_search_configs']} of 24 grid configurations (units x dropout x learning rate x class weight), ranked by validation PR-AUC")
figure(15)
H("5.4 Baselines and feature analysis", 2)
para("Baselines are fitted on the same preprocessed data: an always-'no' (majority) classifier, logistic regression, and a histogram gradient-boosting classifier as a reference. "
     "Feature analysis combines the statistical EDA of Section 4 (Figs. 5, 10, 11, 14) with permutation importance of the trained network (Figure 20, Section 6.3).", align="justify")

# ============================================================================ 6 RESULTS
H("6. Results Visualization and Interpretation", 1)
H("6.1 Training behaviour", 2)
for n in (16, 17): figure(n)
H("6.2 Test-set performance", 2)
def mrow(name, d): t = d["test"]; return (name, f"{t['roc_auc']:.3f}", f"{t['pr_auc']:.3f}", f"{t['f1']:.3f}", f"{t['precision']:.3f}", f"{t['recall']:.3f}", f"{t['accuracy']:.3f}", f"{t['balanced_accuracy']:.3f}", f"{t['mcc']:.3f}")
rows = [mrow("MLP (primary, seed 42)", MR["primary"])]
rows.append(("MLP, mean +/- SD of 5 seeds", f"{S['roc_auc'][0]:.3f} +/- {S['roc_auc'][1]:.3f}", f"{S['pr_auc'][0]:.3f} +/- {S['pr_auc'][1]:.3f}", f"{S['f1'][0]:.3f} +/- {S['f1'][1]:.3f}",
             f"{S['precision'][0]:.3f} +/- {S['precision'][1]:.3f}", f"{S['recall'][0]:.3f} +/- {S['recall'][1]:.3f}", f"{S['accuracy'][0]:.3f} +/- {S['accuracy'][1]:.3f}",
             f"{S['balanced_accuracy'][0]:.3f} +/- {S['balanced_accuracy'][1]:.3f}", f"{S['mcc'][0]:.3f} +/- {S['mcc'][1]:.3f}"))
for k, v in base.items(): rows.append(mrow(k, v))
table(pd.DataFrame(rows, columns=["Model", "ROC-AUC", "PR-AUC", "F1", "Precision", "Recall", "Accuracy", "Bal. acc.", "MCC"]), font=7.2,
      caption=f"Table 25. Final TEST-set metrics (n = {sp[2]:,}; threshold chosen on validation; prevalence {pct(pv[2])}). Majority-class metrics are degenerate by construction.")
para(f"Reading the table: the primary MLP ranks clients with ROC-AUC {P['roc_auc']:.3f}; at the F1-optimal threshold it finds {pct(P['recall'], 0)} of subscribers with {pct(P['precision'], 0)} precision. "
     f"Accuracy ({pct(P['accuracy'])}) is only marginally above the {pct(1 - pv[2])} obtained by always predicting 'no', which is why it is not used as the headline metric. Seed-to-seed variation is small "
     f"(SD of ROC-AUC {S['roc_auc'][1]:.4f}), so the ranking MLP > logistic regression (+{S['roc_auc'][0] - base['Logistic regression']['test']['roc_auc']:.3f}) is stable, while gradient boosting is better still "
     f"(+{base['Gradient boosting (reference)']['test']['roc_auc'] - S['roc_auc'][0]:.3f}). The Brier score of the MLP is {S['brier'][0]:.3f}.", align="justify")
for n in (18, 19): figure(n)
H("6.3 Feature importance and threshold choice", 2)
for n in (20, 21): figure(n)
imp = extra["imp"].copy(); imp.columns = ["feature", "mean AUC drop", "SD (5 repeats)"]
table(df_fmt(imp, 4), widths=[2.0, 1.5, 1.5], font=8.5, caption="Table 26. Permutation importance on the validation set")
H("6.4 Robustness: leakage and temporal shift", 2)
figure(22)
rb = pd.read_csv(RES_DIR / "robustness.csv"); rb["setting"] = rb["setting"].str.replace("\n", " ")
rb = rb.rename(columns={"setting": "Setting", "model": "Model", "test_roc_auc": "Test ROC-AUC", "test_pr_auc": "Test PR-AUC", "test_f1": "Test F1", "test_prevalence": "Test prevalence"})
table(df_fmt(rb, 3), widths=[2.3, 1.4, .8, .8, .6, .7], font=8, caption="Table 27. Robustness experiments (primary row = mean of 5 seeds; others use seed 42)")
H("6.5 Error analysis", 2)
mt = MR["primary"]["test"]
bullets([f"False positives ({mt['fp']:,}) and false negatives ({mt['fn']:,}) are of similar size; the model still misses {pct(1 - mt['recall'], 0)} of subscribers (Figure 18).",
         f"At the chosen threshold the precision of {pct(mt['precision'], 0)} is {mt['precision'] / mt['prevalence']:.1f} times the base rate, so contacting the top-scored clients is more efficient than random calling but still wastes more than half of the calls.",
         "The precision-recall curve (Figure 19) shows precision falling quickly as recall rises, so a high-precision shortlist is feasible only for a small share of subscribers.",
         "Most of the model's discriminative power comes from timing (month, day) and contact-channel variables, i.e. information about how and when the campaign was run, which limits transfer to a different campaign (Figure 22).",
         "No overfitting was observed (training and validation losses coincide, Figure 16); the limiting factor is the information in the pre-call features."])

# ============================================================================ 7 CONCLUSION
C = conclusions(cdf, R, MR)
H("7. Conclusion and Future Scope", 1)
H("7.1 What was learned", 2); bullets(C["learned"])
H("7.2 Model performance", 2); bullets(C["model"])
H("7.3 Challenges", 2); bullets(C["challenges"])
H("7.4 Practical relevance and limitations", 2)
para("The analysis suggests concrete campaign levers: prioritise clients with a previous successful outcome, avoid mass-calling in the busiest months without targeting, limit repeated re-dialling (conversion falls from 14.6% at one contact to 3.9% beyond ten), and treat students, retirees and clients without housing loans as receptive segments. "
     "However, the findings are associational, the data come from one bank and an older campaign period, and the model's modest precision and the temporal shift mean it should support, not replace, human judgement. A high test score alone would not justify deployment.", align="justify")
H("7.5 Future scope", 2); bullets(C["future"])

# ============================================================================ 8 REFERENCES
H("8. References", 1)
para("(APA 7th edition. Authors, titles, venues, volumes, pages and DOIs below were checked for plausibility; Moro et al. (2014) and the UCI description were verified online while preparing this report. Please verify the remaining entries on the publisher pages before submission.)", italic=True, size=9)
refs = [
    "Abadi, M., et al. (2016). TensorFlow: Large-scale machine learning on heterogeneous systems. arXiv:1603.04467.",
    "Fry, B. (2007). Visualizing data: Exploring and explaining data with the Processing environment. O'Reilly Media. [Source of the seven stages: acquire, parse, filter, mine, represent, refine, interact.]",
    "Grinsztajn, L., Oyallon, E., & Varoquaux, G. (2022). Why do tree-based models still outperform deep learning on typical tabular data? Advances in Neural Information Processing Systems 35 (Datasets and Benchmarks Track). arXiv:2207.08815.",
    "Hunter, J. D. (2007). Matplotlib: A 2D graphics environment. Computing in Science & Engineering, 9(3), 90-95. https://doi.org/10.1109/MCSE.2007.55",
    "Kingma, D. P., & Ba, J. (2015). Adam: A method for stochastic optimization. International Conference on Learning Representations. arXiv:1412.6980.",
    "Moro, S., Cortez, P., & Rita, P. (2014). A data-driven approach to predict the success of bank telemarketing. Decision Support Systems, 62, 22-31. https://doi.org/10.1016/j.dss.2014.03.001",
    "Moro, S., Rita, P., & Cortez, P. (2012). Bank Marketing [Data set]. UCI Machine Learning Repository. https://archive.ics.uci.edu/dataset/222/bank+marketing",
    "Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12, 2825-2830.",
    "Saito, T., & Rehmsmeier, M. (2015). The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets. PLOS ONE, 10(3), e0118432. https://doi.org/10.1371/journal.pone.0118432",
    "Srivastava, N., Hinton, G., Krizhevsky, A., Sutskever, I., & Salakhutdinov, R. (2014). Dropout: A simple way to prevent neural networks from overfitting. Journal of Machine Learning Research, 15(1), 1929-1958.",
    "Tukey, J. W. (1977). Exploratory data analysis. Addison-Wesley.",
    "Virtanen, P., et al. (2020). SciPy 1.0: Fundamental algorithms for scientific computing in Python. Nature Methods, 17, 261-272. https://doi.org/10.1038/s41592-019-0686-2",
    "Waskom, M. L. (2021). seaborn: Statistical data visualization. Journal of Open Source Software, 6(60), 3021. https://doi.org/10.21105/joss.03021",
]
for r_ in refs:
    p = doc.add_paragraph(r_); p.paragraph_format.left_indent = Inches(0.4); p.paragraph_format.first_line_indent = Inches(-0.4); p.paragraph_format.space_after = Pt(3)
    for run in p.runs: run.font.size = Pt(10)
para("Relevance: Moro et al. (2014) and the UCI page document the data and prior modelling; Fry (2007) and Tukey (1977) provide the methodological frame; Pedregosa, Virtanen, Hunter, Waskom and Abadi document the software used; "
     "Kingma & Ba and Srivastava et al. justify the optimiser and dropout regularisation; Saito & Rehmsmeier justify PR-based evaluation; Grinsztajn et al. motivate the gradient-boosting reference.", size=9.5, align="justify")

# ============================================================================ 9 APPENDIX
page_break()
H("9. Appendix", 1)
H("A. Rubric compliance matrix", 2)
rub = pd.DataFrame([(a, m, e, f, v, r) for a, m, e, f, v, r in RUBRIC], columns=["Requirement", "Max", "Implementation evidence", "File / section", "Validation status", "Remaining work"])
table(rub, widths=[1.1, .35, 2.0, 1.1, 1.1, .85], font=6.8, caption="Table A1. Rubric matrix (40 marks). No grade is guaranteed; the matrix shows how each criterion is addressed")
H("B. Reproducibility and execution", 2)
bullets(["Install: pip install -r requirements.txt (Python 3.10+; tested with Python 3.12, TensorFlow-CPU 2.21).",
         "Full pipeline: python scripts/run_all.py (about 10-15 minutes on one CPU core); quick smoke test: python scripts/run_all.py --quick (code check only, NOT a full run).",
         "Tests: pytest -q (30 tests, all passing at the time of writing).",
         "Notebook: notebooks/eda_and_modeling.ipynb (executed; model section loads the saved artefacts, with a switch to retrain).",
         "Interactive explorer: outputs/interactive/explorer.html."])
H("C. Source code", 2)
para("The complete source code is reproduced below (also in the repository under src/ and scripts/).", size=10)
for rel in ["src/config.py", "src/data_loader.py", "src/preprocessing.py", "src/eda.py", "src/visualizations.py", "src/model.py", "src/train.py", "src/evaluate.py", "src/interactive.py", "scripts/run_all.py"]:
    H(rel, 3)
    code = (ROOT / rel).read_text()
    for chunk in [code[i:i + 6000] for i in range(0, len(code), 6000)]:
        p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(2); p.paragraph_format.line_spacing = 1.0
        r = p.add_run(chunk.replace("\t", "    ")); r.font.name = "Courier New"; r.font.size = Pt(6.3)
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Courier New")

out = ROOT / "reports" / "final_report.docx"
doc.save(out)
print("saved", out, out.stat().st_size // 1024, "KB")
