"""Stage 2 (Parse) & Stage 4 (Mine): data quality, univariate, distribution, bivariate and
multivariate statistics. Every number reported in the report is produced here from the data."""
import json

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from scipy.optimize import minimize_scalar

from .config import CATEGORICAL, MONTH_ORDER, NUMERIC, RES_DIR, TAB_DIR, TARGET
from .preprocessing import signed_log1p


# ---------------------------------------------------------------------------------------
# Structure & data-quality
# ---------------------------------------------------------------------------------------
def structure_report(raw: pd.DataFrame) -> pd.DataFrame:
    rep = pd.DataFrame({"dtype": raw.dtypes.astype(str), "n_unique": raw.nunique(),
                        "n_missing_NaN": raw.isna().sum(),
                        "pct_missing_NaN": (raw.isna().mean() * 100).round(3)})
    rep["memory_KB"] = (raw.memory_usage(deep=True, index=False) / 1024).round(1)
    return rep


def quality_report(raw: pd.DataFrame) -> pd.DataFrame:
    """NaN is not the only way a value can be missing: look for 'unknown' labels and sentinels."""
    rows = []
    for c in CATEGORICAL:
        n_unk = int((raw[c].astype(str).str.lower() == "unknown").sum())
        rows.append({"column": c, "issue": "'unknown' label", "count": n_unk,
                     "pct": round(100 * n_unk / len(raw), 2)})
    n_sent = int((raw["pdays"] == -1).sum())
    rows.append({"column": "pdays", "issue": "sentinel -1 (never contacted)", "count": n_sent,
                 "pct": round(100 * n_sent / len(raw), 2)})
    n_neg = int((raw["balance"] < 0).sum())
    rows.append({"column": "balance", "issue": "negative balance (valid overdraft)", "count": n_neg,
                 "pct": round(100 * n_neg / len(raw), 2)})
    n_zero = int((raw["duration"] == 0).sum())
    rows.append({"column": "duration", "issue": "zero-second calls", "count": n_zero,
                 "pct": round(100 * n_zero / len(raw), 3)})
    rows.append({"column": "(all)", "issue": "exact duplicate rows", "count": int(raw.duplicated().sum()),
                 "pct": round(100 * raw.duplicated().mean(), 3)})
    rows.append({"column": "(all)", "issue": "NaN cells", "count": int(raw.isna().sum().sum()), "pct": 0.0})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------
# Univariate
# ---------------------------------------------------------------------------------------
def numeric_summary(df: pd.DataFrame, cols) -> pd.DataFrame:
    out = {}
    for c in cols:
        s = df[c].dropna()
        q1, q3 = s.quantile([.25, .75])
        out[c] = {"count": int(s.count()), "missing": int(df[c].isna().sum()), "mean": s.mean(),
                  "median": s.median(), "mode": s.mode().iloc[0], "min": s.min(), "max": s.max(),
                  "range": s.max() - s.min(), "variance": s.var(), "std": s.std(), "Q1": q1, "Q3": q3,
                  "IQR": q3 - q1, "skewness": stats.skew(s), "excess_kurtosis": stats.kurtosis(s)}
    return pd.DataFrame(out).T


def iqr_outliers(df: pd.DataFrame, cols) -> pd.DataFrame:
    rows = []
    for c in cols:
        s = df[c]
        q1, q3 = s.quantile([.25, .75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_lo, n_hi = int((s < lo).sum()), int((s > hi).sum())
        far_hi = q3 + 3 * iqr
        rows.append({"variable": c, "lower_fence": lo, "upper_fence": hi, "n_below": n_lo,
                     "n_above": n_hi, "pct_outliers": 100 * (n_lo + n_hi) / len(s),
                     "n_extreme(>3IQR)": int((s > far_hi).sum() + (s < q1 - 3 * iqr).sum()),
                     "max": s.max(), "p99": s.quantile(.99)})
    return pd.DataFrame(rows)


def categorical_frequency(df: pd.DataFrame, col: str) -> pd.DataFrame:
    vc = df[col].value_counts()
    return pd.DataFrame({"count": vc, "percent": (100 * vc / vc.sum()).round(2)})


def rate_table(df: pd.DataFrame, col: str, order=None) -> pd.DataFrame:
    """Subscription rate per category with exact (Clopper-Pearson) 95 % confidence intervals."""
    g = df.groupby(col)["y_bin"].agg(["sum", "count"])
    g["rate"] = g["sum"] / g["count"]
    ci = [stats.binomtest(int(k), int(n)).proportion_ci(0.95, method="exact") for k, n in zip(g["sum"], g["count"])]
    g["ci_low"], g["ci_high"] = [c.low for c in ci], [c.high for c in ci]
    g = g.rename(columns={"sum": "subscribed", "count": "n"})
    if order is not None:
        g = g.reindex(order)
    return g


# ---------------------------------------------------------------------------------------
# Probability distributions
# ---------------------------------------------------------------------------------------
def bernoulli_summary(df: pd.DataFrame) -> dict:
    k, n = int(df["y_bin"].sum()), len(df)
    ci = stats.binomtest(k, n).proportion_ci(0.95, method="exact")
    # Is one common Bernoulli(p) plausible across months? (homogeneity chi-square)
    ct = pd.crosstab(df["month"], df["y_bin"])
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    monthly = df.groupby("month")["y_bin"].mean()
    return {"k": k, "n": n, "p_hat": k / n, "ci_low": ci.low, "ci_high": ci.high,
            "variance_p_1_minus_p": (k / n) * (1 - k / n),
            "month_homogeneity_chi2": chi2, "month_homogeneity_dof": int(dof), "month_homogeneity_p": p,
            "monthly_rate_min": float(monthly.min()), "monthly_rate_max": float(monthly.max())}


def _nb_fit(x: np.ndarray):
    """MLE of the negative binomial (mean mu = sample mean, size r)."""
    mu = x.mean()

    def nll(log_r):
        r = np.exp(log_r)
        return -stats.nbinom.logpmf(x, r, r / (r + mu)).sum()

    res = minimize_scalar(nll, bounds=(np.log(1e-2), np.log(1e4)), method="bounded")
    r = float(np.exp(res.x))
    return r, r / (r + mu), -res.fun


def count_distribution_fit(x: np.ndarray, name: str, max_bin: int = 9) -> dict:
    """Compare Poisson and Negative-Binomial models for a non-negative count variable."""
    x = np.asarray(x, dtype=int)
    n, mu, var = len(x), x.mean(), x.var(ddof=1)
    r, p, ll_nb = _nb_fit(x)
    ll_pois = stats.poisson.logpmf(x, mu).sum()
    ks = np.arange(0, max_bin + 1)
    obs = np.array([(x == k).sum() for k in ks[:-1]] + [(x >= max_bin).sum()])
    exp_p = np.append(stats.poisson.pmf(ks[:-1], mu), stats.poisson.sf(max_bin - 1, mu)) * n
    exp_n = np.append(stats.nbinom.pmf(ks[:-1], r, p), stats.nbinom.sf(max_bin - 1, r, p)) * n
    chi_p, chi_n = ((obs - exp_p) ** 2 / exp_p).sum(), ((obs - exp_n) ** 2 / exp_n).sum()
    dof_p, dof_n = len(obs) - 1 - 1, len(obs) - 1 - 2
    return {"variable": name, "n": n, "mean": mu, "variance": var, "dispersion_index_var_over_mean": var / mu,
            "poisson_lambda": mu, "poisson_loglik": ll_pois, "poisson_AIC": 2 * 1 - 2 * ll_pois,
            "poisson_chi2": chi_p, "poisson_dof": dof_p, "poisson_p": stats.chi2.sf(chi_p, dof_p),
            "nb_r": r, "nb_p": p, "nb_loglik": ll_nb, "nb_AIC": 2 * 2 - 2 * ll_nb,
            "nb_chi2": chi_n, "nb_dof": dof_n, "nb_p_value": stats.chi2.sf(chi_n, dof_n),
            "obs_zero_pct": 100 * (x == 0).mean(), "poisson_zero_pct": 100 * stats.poisson.pmf(0, mu),
            "nb_zero_pct": 100 * stats.nbinom.pmf(0, r, p), "max_obs": int(x.max()),
            "prob_ge_10_obs_pct": 100 * (x >= 10).mean(), "prob_ge_10_poisson_pct": 100 * stats.poisson.sf(9, mu),
            "prob_ge_10_nb_pct": 100 * stats.nbinom.sf(9, r, p)}


CONT_DISTS = {"normal": stats.norm, "lognormal": stats.lognorm, "gamma": stats.gamma,
              "exponential": stats.expon, "weibull": stats.weibull_min}


def continuous_fits(x: np.ndarray, names, positive_support=True) -> pd.DataFrame:
    """Fit candidate continuous distributions by MLE; compare with AIC and the KS distance.

    With n ~ 45,000 *any* imperfect model is rejected by a KS test (tiny p-values), so the KS
    statistic D (the maximum CDF gap) is read as an effect size, not as a pass/fail verdict.
    """
    rows = []
    x = np.asarray(x, dtype=float)
    for nm in names:
        d = CONT_DISTS[nm]
        params = d.fit(x) if nm == "normal" else d.fit(x, floc=0)
        ll = d.logpdf(x, *params).sum()
        k = 2 if nm in ("normal", "gamma", "lognormal", "weibull") else 1  # free parameters
        ks = stats.kstest(x, d.cdf, args=params)
        rows.append({"distribution": nm, "params": tuple(np.round(params, 4)), "loglik": ll,
                     "AIC": 2 * k - 2 * ll, "KS_D": ks.statistic, "KS_p": ks.pvalue})
    out = pd.DataFrame(rows).sort_values("AIC").reset_index(drop=True)
    out["delta_AIC"] = out["AIC"] - out["AIC"].min()
    return out


def normality_tests(x: np.ndarray, seed=42) -> dict:
    x = np.asarray(x, dtype=float)
    k2, p_k2 = stats.normaltest(x)
    sample = np.random.default_rng(seed).choice(x, size=5000, replace=False)
    sw, p_sw = stats.shapiro(sample)
    return {"dagostino_K2": k2, "dagostino_p": p_k2, "shapiro_W_n5000": sw, "shapiro_p": p_sw,
            "skew": float(stats.skew(x)), "excess_kurtosis": float(stats.kurtosis(x))}


# ---------------------------------------------------------------------------------------
# Bivariate / multivariate
# ---------------------------------------------------------------------------------------
def cramers_v(a: pd.Series, b: pd.Series) -> float:
    """Bias-corrected Cramer's V (Bergsma, 2013)."""
    ct = pd.crosstab(a, b)
    chi2 = stats.chi2_contingency(ct, correction=False)[0]
    n = ct.values.sum()
    phi2 = chi2 / n
    r, k = ct.shape
    phi2c = max(0, phi2 - (k - 1) * (r - 1) / (n - 1))
    rc, kc = r - (r - 1) ** 2 / (n - 1), k - (k - 1) ** 2 / (n - 1)
    denom = min(kc - 1, rc - 1)
    return float(np.sqrt(phi2c / denom)) if denom > 0 else 0.0


def cramers_matrix(df: pd.DataFrame, cols) -> pd.DataFrame:
    m = pd.DataFrame(index=cols, columns=cols, dtype=float)
    for a in cols:
        for b in cols:
            m.loc[a, b] = 1.0 if a == b else cramers_v(df[a], df[b])
    return m


def chi2_vs_target(df: pd.DataFrame, cols) -> pd.DataFrame:
    rows = []
    for c in cols:
        ct = pd.crosstab(df[c], df[TARGET])
        chi2, p, dof, _ = stats.chi2_contingency(ct)
        rows.append({"variable": c, "chi2": chi2, "dof": int(dof), "p_value": p,
                     "cramers_v": cramers_v(df[c], df[TARGET])})
    return pd.DataFrame(rows).sort_values("cramers_v", ascending=False).reset_index(drop=True)


def mannwhitney_vs_target(df: pd.DataFrame, cols) -> pd.DataFrame:
    """Rank-based group comparison (robust to the heavy tails seen in these variables)."""
    rows = []
    yes, no = df[df[TARGET] == "yes"], df[df[TARGET] == "no"]
    for c in cols:
        u, p = stats.mannwhitneyu(yes[c], no[c], alternative="two-sided")
        delta = 2 * u / (len(yes) * len(no)) - 1  # Cliff's delta (= 2*AUC - 1)
        rows.append({"variable": c, "median_yes": yes[c].median(), "median_no": no[c].median(),
                     "mean_yes": yes[c].mean(), "mean_no": no[c].mean(), "U": u, "p_value": p,
                     "cliffs_delta": delta})
    return pd.DataFrame(rows).sort_values("cliffs_delta", key=np.abs, ascending=False).reset_index(drop=True)


def kruskal_effect(df: pd.DataFrame, value: str, group: str) -> dict:
    groups = [g[value].values for _, g in df.groupby(group)]
    h, p = stats.kruskal(*groups)
    k, n = len(groups), len(df)
    return {"value": value, "group": group, "H": h, "p_value": p, "epsilon_sq": (h - k + 1) / (n - k)}


def correlation_matrices(df: pd.DataFrame, cols) -> dict:
    return {"spearman": df[cols].corr(method="spearman"), "pearson": df[cols].corr(method="pearson")}


def _logit_design(train: pd.DataFrame, drop_redundant: bool) -> pd.DataFrame:
    """Design matrix for the descriptive logistic regression (pre-call information only).

    `previous`, `pdays` and `previously_contacted` all describe the same thing (earlier
    contacts), so with drop_redundant=True only log1p(previous) is kept for that concept.
    """
    X = pd.DataFrame({
        "age_per_10y": train["age"] / 10, "balance_signedlog": signed_log1p(train["balance"]),
        "day": train["day"], "log1p_campaign": np.log1p(train["campaign"]),
        "log1p_previous": np.log1p(train["previous"])})
    if not drop_redundant:
        X["log1p_pdays"] = np.log1p(train["pdays_clean"])
        X["previously_contacted"] = train["previously_contacted"]
    for c in CATEGORICAL:
        ref = train[c].value_counts().index[0]  # reference level = most frequent category
        d = pd.get_dummies(train[c], prefix=c).astype(float)
        X = pd.concat([X, d.drop(columns=f"{c}_{ref}")], axis=1)
    return sm.add_constant(X.astype(float))


def vif_table(train: pd.DataFrame, drop_redundant: bool) -> pd.Series:
    """Variance inflation factors (VIF > 10 is the usual warning level)."""
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    X = _logit_design(train, drop_redundant)
    v = {c: variance_inflation_factor(X.values, i) for i, c in enumerate(X.columns) if c != "const"}
    return pd.Series(v).sort_values(ascending=False)


def logit_odds_ratios(train: pd.DataFrame) -> pd.DataFrame:
    """Multivariable logistic regression (descriptive) on pre-call information.

    Odds ratios are *associations adjusted for the other variables*, not causal effects.
    """
    X = _logit_design(train, drop_redundant=True)
    fit = sm.Logit(train["y_bin"].astype(float), X).fit(disp=0, maxiter=200)
    ci = fit.conf_int()
    out = pd.DataFrame({"odds_ratio": np.exp(fit.params), "ci_low": np.exp(ci[0]), "ci_high": np.exp(ci[1]),
                        "p_value": fit.pvalues}).drop(index="const")
    out.attrs["pseudo_r2"] = float(fit.prsquared)
    out.attrs["n"] = int(fit.nobs)
    return out


def before_after_skew(train: pd.DataFrame, Xtr: np.ndarray, names) -> pd.DataFrame:
    """Skewness / excess kurtosis of heavy-tailed variables before and after the learned transforms."""
    rows = []
    for c in ["balance", "campaign", "previous", "pdays_clean"]:
        raw, new = train[c].values.astype(float), Xtr[:, list(names).index(c)]
        rows.append({"variable": c, "skew_before": stats.skew(raw), "skew_after": stats.skew(new),
                     "kurtosis_before": stats.kurtosis(raw), "kurtosis_after": stats.kurtosis(new)})
    return pd.DataFrame(rows)


def age_group(s: pd.Series) -> pd.Categorical:
    bins = [0, 24, 34, 44, 54, 64, 120]
    labels = ["<25", "25-34", "35-44", "45-54", "55-64", "65+"]
    return pd.cut(s, bins=bins, labels=labels)


# ---------------------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------------------
def _clean_json(o):
    if isinstance(o, dict):
        return {str(k): _clean_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean_json(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if (isinstance(o, float) and np.isnan(o)) else float(o)
    return o


def run_eda(raw: pd.DataFrame, cdf: pd.DataFrame, train: pd.DataFrame, save: bool = True) -> dict:
    """Run every statistical analysis and return a dictionary of results (also saved to disk)."""
    R = {}
    num_cols = ["age", "balance", "day", "duration", "campaign", "pdays", "previous"]

    tables = {
        "structure": structure_report(raw), "quality": quality_report(raw),
        "numeric_summary": numeric_summary(cdf, num_cols),
        "outliers_iqr": iqr_outliers(cdf, ["age", "balance", "duration", "campaign", "previous"]),
    }
    R["n_rows"], R["n_cols"] = int(raw.shape[0]), int(raw.shape[1])
    R["class_counts"] = cdf[TARGET].value_counts().to_dict()
    R["bernoulli"] = bernoulli_summary(cdf)

    # categorical frequency tables + subscription rates
    for c in CATEGORICAL:
        tables[f"freq_{c}"] = categorical_frequency(cdf, c)
        tables[f"rate_{c}"] = rate_table(cdf, c, order=MONTH_ORDER if c == "month" else None)
    cdf = cdf.assign(age_group=age_group(cdf["age"]))
    tables["rate_age_group"] = rate_table(cdf, "age_group")

    # discrete distributions
    R["campaign_counts"] = count_distribution_fit(cdf["campaign"].values - 1, "campaign-1 (extra contacts)")
    R["previous_counts"] = count_distribution_fit(cdf["previous"].values, "previous")

    # continuous distributions
    R["age_normality"] = normality_tests(cdf["age"].values)
    tables["fit_age"] = continuous_fits(cdf["age"].values, ["normal", "lognormal", "gamma"])
    dur = cdf.loc[cdf["duration"] > 0, "duration"].values
    R["duration_n_positive"] = int(len(dur))
    tables["fit_duration"] = continuous_fits(dur, ["exponential", "gamma", "weibull", "lognormal"])
    R["balance_normality"] = normality_tests(cdf["balance"].values)

    # bivariate
    corr_cols = ["age", "balance", "day", "duration", "campaign", "pdays_clean", "previous", "y_bin"]
    cm = correlation_matrices(cdf, corr_cols)
    tables["corr_spearman"], tables["corr_pearson"] = cm["spearman"], cm["pearson"]
    tables["mannwhitney"] = mannwhitney_vs_target(cdf, ["age", "balance", "day", "duration", "campaign", "pdays_clean", "previous"])
    tables["chi2_target"] = chi2_vs_target(cdf, CATEGORICAL)
    tables["cramers_matrix"] = cramers_matrix(cdf, CATEGORICAL + [TARGET])
    R["kruskal_balance_job"] = kruskal_effect(cdf, "balance", "job")
    R["kruskal_age_education"] = kruskal_effect(cdf, "age", "education")
    # multivariate
    lo = logit_odds_ratios(train)
    tables["logit_odds_ratios"] = lo
    R["logit"] = {"pseudo_r2": lo.attrs["pseudo_r2"], "n": lo.attrs["n"]}
    v_before, v_after = vif_table(train, False), vif_table(train, True)
    tables["vif_before"], tables["vif_after"] = v_before.to_frame("VIF"), v_after.to_frame("VIF")
    R["vif"] = {"max_before": float(v_before.max()), "max_before_name": v_before.idxmax(),
                "n_above10_before": int((v_before > 10).sum()), "max_after": float(v_after.max()),
                "max_after_name": v_after.idxmax(), "n_above10_after": int((v_after > 10).sum())}
    # contact='unknown' is not evenly spread over time: check its overlap with May
    R["contact_unknown_share_in_may"] = float((cdf.loc[cdf["contact"] == "unknown", "month"] == "may").mean())
    R["contact_unknown_share_in_jun"] = float((cdf.loc[cdf["contact"] == "unknown", "month"] == "jun").mean())

    R["tables_index"] = list(tables.keys())
    if save:
        for k, t in tables.items():
            t.to_csv(TAB_DIR / f"{k}.csv")
        (RES_DIR / "eda_results.json").write_text(json.dumps(_clean_json(R), indent=2))
    R["_tables"] = tables
    return R
