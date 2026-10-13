"""Stage 5 (Represent) & Stage 6 (Refine): all exploratory figures.

Design rules used everywhere (Stage 6): descriptive titles that state the question, labelled axes
with units, one consistent colour pair for the outcome (blue = no, orange = yes), reference lines
where they aid reading, annotated sample sizes, and no 3-D or dual-axis effects.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

from .config import FIG_DIR, MONTH_ORDER, SEED
from .eda import CONT_DISTS, age_group, rate_table
from .preprocessing import signed_log1p

C_NO, C_YES, C_GREY, C_ACC = "#4C72B0", "#DD8452", "#8C8C8C", "#2E8B57"
plt.rcParams.update({"figure.dpi": 100, "savefig.dpi": 200, "font.size": 10, "axes.titlesize": 11,
                     "axes.titleweight": "bold", "axes.labelsize": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25,
                     "legend.frameon": False})


def _save(fig, name: str):
    path = FIG_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


# ------------------------------------------------------------------------------ Figure 1
def fig01_class_balance(cdf):
    vc = cdf["y"].value_counts().reindex(["no", "yes"])
    fig, ax = plt.subplots(figsize=(5.2, 4))
    bars = ax.bar(["No (declined)", "Yes (subscribed)"], vc.values, color=[C_NO, C_YES], width=.6)
    for b, v in zip(bars, vc.values):
        ax.text(b.get_x() + b.get_width() / 2, v + 400, f"{v:,}\n({100 * v / vc.sum():.1f}%)", ha="center", va="bottom")
    ax.set_ylim(0, vc.max() * 1.18)
    ax.set_ylabel("Number of clients"); ax.set_title("Fig. 1  Outcome of the telemarketing call (term deposit)")
    ax.grid(axis="x", visible=False)
    return _save(fig, "fig01_class_balance")


# ------------------------------------------------------------------------------ Figure 2
def fig02_numeric_histograms(cdf):
    cols = [("age", "Age (years)", None), ("balance", "Average yearly balance (EUR)", .99),
            ("duration", "Last call duration (seconds)", .99), ("campaign", "Contacts in this campaign (count)", None),
            ("previous", "Contacts before this campaign (count)", None), ("day", "Day of month of last contact", None)]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    for ax, (c, lab, clip) in zip(axes.ravel(), cols):
        s = cdf[c]
        note = ""
        if clip:
            hi = s.quantile(clip); note = f"\n(x-axis cut at 99th pct = {hi:,.0f}; {int((s > hi).sum()):,} larger values not shown)"
            s_plot = s[s <= hi]
        elif c in ("campaign", "previous"):
            hi = 20 if c == "campaign" else 10; s_plot = s[s <= hi]
            note = f"\n(shown up to {hi}; {int((s > hi).sum()):,} larger values not shown)"
        else:
            s_plot = s
        if c in ("campaign", "previous"):
            vc = s_plot.value_counts().sort_index()
            ax.bar(vc.index, vc.values, color=C_NO, width=.8)
        else:
            # integer-valued variables get integer-aligned bins (avoids aliasing gaps)
            bins = np.arange(s_plot.min() - .5, s_plot.max() + 1.5, 1) if c in ("age", "day") else 40
            ax.hist(s_plot, bins=bins, color=C_NO, edgecolor="white", linewidth=.4)
        ax.axvline(s.mean(), color=C_YES, ls="--", lw=1.6, label=f"mean {s.mean():,.1f}")
        ax.axvline(s.median(), color="k", ls=":", lw=1.6, label=f"median {s.median():,.1f}")
        ax.set_xlabel(lab + note, fontsize=8.5); ax.set_ylabel("Number of clients")
        ax.set_title(f"{c}: skew = {stats.skew(s):.2f}"); ax.legend(fontsize=8)
    fig.suptitle("Fig. 2  Univariate distributions of the numeric variables", fontweight="bold", y=1.01)
    fig.tight_layout()
    return _save(fig, "fig02_numeric_histograms")


# ------------------------------------------------------------------------------ Figure 3
def fig03_outlier_boxplots(cdf, outliers):
    specs = [("age", "linear", "Age (years)"), ("balance", "symlog", "Balance (EUR, symlog scale)"),
             ("duration", "log", "Call duration (s, log scale)"), ("campaign", "log", "Contacts in campaign (log scale)"),
             ("previous", "symlog", "Previous contacts (symlog scale)")]
    fig, axes = plt.subplots(1, 5, figsize=(14, 4.6))
    o = outliers.set_index("variable")
    for ax, (c, sc, lab) in zip(axes, specs):
        sub = cdf[cdf[c] > 0] if sc == "log" else cdf
        ax.boxplot(sub[c], whis=1.5, patch_artist=True, boxprops=dict(facecolor="#cfe0f3"),
                   medianprops=dict(color="k"), flierprops=dict(marker=".", markersize=2.5, alpha=.35, markeredgecolor=C_NO))
        if sc == "symlog": ax.set_yscale("symlog", linthresh=(100 if c == "balance" else 1))
        elif sc == "log": ax.set_yscale("log")
        ax.set_xticks([]); ax.set_ylabel(lab)
        ax.set_title(f"{c}\n{o.loc[c, 'pct_outliers']:.1f}% beyond 1.5xIQR\n({int(o.loc[c, 'n_extreme(>3IQR)']):,} beyond 3xIQR)", fontsize=9.5)
    fig.suptitle("Fig. 3  Outlier screening with the IQR rule (whiskers = 1.5 x IQR)", fontweight="bold", y=1.04)
    fig.tight_layout()
    return _save(fig, "fig03_outlier_boxplots")


# ------------------------------------------------------------------------------ Figure 4
def fig04_categorical_counts(cdf):
    cols = ["job", "education", "marital", "contact", "poutcome", "month"]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.4))
    for ax, c in zip(axes.ravel(), cols):
        vc = cdf[c].value_counts()
        vc = vc.reindex(MONTH_ORDER) if c == "month" else vc.sort_values()
        colors = [C_GREY if i == "unknown" else C_NO for i in vc.index]
        ax.barh(vc.index.astype(str), vc.values, color=colors)
        for y, v in enumerate(vc.values):
            ax.text(v, y, f" {100 * v / len(cdf):.1f}%", va="center", fontsize=8)
        ax.set_xlim(0, vc.max() * 1.18); ax.set_xlabel("Number of clients"); ax.set_title(c)
        ax.grid(axis="y", visible=False)
    fig.suptitle("Fig. 4  Category frequencies (grey bars = 'unknown', a hidden form of missing data)",
                 fontweight="bold", y=1.01)
    fig.tight_layout()
    return _save(fig, "fig04_categorical_counts")


# ------------------------------------------------------------------------------ Figure 5
def fig05_rate_by_category(cdf):
    d = cdf.assign(age_group=age_group(cdf["age"]).astype(str))
    base = d["y_bin"].mean()
    cols = ["job", "poutcome", "contact", "education", "housing", "loan"]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.4))
    for ax, c in zip(axes.ravel(), cols):
        t = rate_table(d, c).sort_values("rate")
        err = np.vstack([t["rate"] - t["ci_low"], t["ci_high"] - t["rate"]]) * 100
        ax.barh(t.index.astype(str), t["rate"] * 100, xerr=err, color=C_ACC, ecolor="k", capsize=2, alpha=.85)
        for y, (r, n) in enumerate(zip(t["rate"], t["n"])):
            ax.text(t["ci_high"].iloc[y] * 100 + .8, y, f"{100 * r:.1f}%  (n={int(n):,})", va="center", fontsize=7.5)
        ax.axvline(base * 100, color=C_YES, ls="--", lw=1.4)
        ax.set_xlim(0, max(t["ci_high"]) * 100 * 1.55); ax.set_xlabel("Subscription rate (%)")
        ax.set_title(c); ax.grid(axis="y", visible=False)
    axes.ravel()[0].legend([plt.Line2D([], [], color=C_YES, ls="--")], [f"overall {base * 100:.1f}%"], loc="lower right")
    fig.suptitle("Fig. 5  Subscription rate by client / campaign category (bars = rate, whiskers = exact 95% CI)",
                 fontweight="bold", y=1.01)
    fig.tight_layout()
    return _save(fig, "fig05_rate_by_category")


# ------------------------------------------------------------------------------ Figure 6
def fig06_month_volume_vs_rate(cdf):
    t = rate_table(cdf, "month", order=MONTH_ORDER)
    fig, ax = plt.subplots(figsize=(7.5, 5))
    err = np.vstack([t["rate"] - t["ci_low"], t["ci_high"] - t["rate"]]) * 100
    ax.errorbar(t["n"], t["rate"] * 100, yerr=err, fmt="o", color=C_ACC, ecolor=C_GREY, capsize=3, ms=7)
    for m, r in t.iterrows():
        ax.annotate(m.capitalize(), (r["n"], r["rate"] * 100), textcoords="offset points", xytext=(7, 5), fontsize=9)
    ax.axhline(cdf["y_bin"].mean() * 100, color=C_YES, ls="--", lw=1.3, label=f"overall {cdf['y_bin'].mean() * 100:.1f}%")
    ax.set_xscale("log"); ax.set_xlabel("Calls made in the month (log scale)"); ax.set_ylabel("Subscription rate (%)")
    ax.set_title("Fig. 6  Busy months convert worst: call volume vs. subscription rate"); ax.legend()
    return _save(fig, "fig06_month_volume_vs_rate")


# ------------------------------------------------------------------------------ Figure 7
def fig07_count_distribution(cdf, R):
    fits = [("campaign", cdf["campaign"].values - 1, R["campaign_counts"], "Extra contacts in campaign (= campaign - 1)", 15),
            ("previous", cdf["previous"].values, R["previous_counts"], "Contacts before this campaign", 15)]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    for ax, (nm, x, f, lab, kmax) in zip(axes, fits):
        k = np.arange(0, kmax + 1)
        obs = np.array([(x == i).mean() for i in k])
        ax.bar(k, obs, color="#cfe0f3", edgecolor=C_NO, label="Observed")
        ax.plot(k, stats.poisson.pmf(k, f["poisson_lambda"]), "o-", color=C_YES, label=f"Poisson (lambda={f['poisson_lambda']:.2f})")
        ax.plot(k, stats.nbinom.pmf(k, f["nb_r"], f["nb_p"]), "s-", color=C_ACC, label=f"Neg. binomial (r={f['nb_r']:.2f}, p={f['nb_p']:.2f})")
        ax.set_yscale("log"); ax.set_ylim(1e-6, 1); ax.set_xlabel(lab); ax.set_ylabel("Probability (log scale)")
        ax.set_title(f"{nm}: variance/mean = {f['dispersion_index_var_over_mean']:.1f} (Poisson would give 1)")
        ax.legend(fontsize=8.5)
    fig.suptitle("Fig. 7  Discrete distributions: observed count PMF vs. fitted Poisson and Negative Binomial",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    return _save(fig, "fig07_count_distribution")


# ---------------------------------------------------------------------- Figures 8 & 9
def _fit_overlay(x, tables, names, xmax, xlabel, title, fname, qq_pair, bins=60):
    xs = np.linspace(max(x.min(), 1e-6), xmax, 400)
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.6))
    ax = axes[0]
    ax.hist(x[x <= xmax], bins=bins, density=True, color="#cfe0f3", edgecolor="white", label="Observed")
    cols = [C_YES, C_ACC, "#8172B3", "#C44E52"]
    params = {}
    for nm, c in zip(names, cols):
        r = tables[tables.distribution == nm].iloc[0]
        p = r["params"]; params[nm] = p
        ax.plot(xs, CONT_DISTS[nm].pdf(xs, *p), color=c, lw=2, label=f"{nm} (AIC +{r.delta_AIC:,.0f}, KS D={r.KS_D:.3f})")
    ax.set_xlabel(xlabel); ax.set_ylabel("Density"); ax.set_title("Histogram with fitted densities"); ax.legend(fontsize=8)
    for ax, nm in zip(axes[1:], qq_pair):
        q = np.linspace(.005, .995, 200)
        emp = np.quantile(x, q); th = CONT_DISTS[nm].ppf(q, *params[nm])
        ax.scatter(th, emp, s=9, color=C_NO)
        lim = [min(th.min(), emp.min()), max(th.max(), emp.max())]
        ax.plot(lim, lim, "k--", lw=1); ax.set_xlabel(f"Theoretical quantiles ({nm})"); ax.set_ylabel("Empirical quantiles")
        ax.set_title(f"Q-Q plot vs {nm}")
    fig.suptitle(title, fontweight="bold", y=1.03)
    fig.tight_layout()
    return _save(fig, fname)


def fig08_age_fits(cdf, T):
    return _fit_overlay(cdf["age"].values.astype(float), T["fit_age"], ["normal", "lognormal", "gamma"], 95, "Age (years)",
                        "Fig. 8  Continuous distributions: is age normally distributed?", "fig08_age_fits", ["normal", "lognormal"], bins=39)


def fig09_duration_fits(cdf, T):
    x = cdf.loc[cdf["duration"] > 0, "duration"].values.astype(float)
    return _fit_overlay(x, T["fit_duration"], ["exponential", "lognormal", "gamma", "weibull"], 1500, "Call duration (seconds, cut at 1,500)",
                        "Fig. 9  Continuous distributions: is call duration a memoryless (exponential) waiting time?",
                        "fig09_duration_fits", ["exponential", "lognormal"])


# ------------------------------------------------------------------------------ Figure 10
def fig10_correlation_heatmaps(T):
    lab = {"y_bin": "subscribed (0/1)", "pdays_clean": "pdays (clean)"}
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8))
    for ax, k, ttl in zip(axes, ["corr_spearman", "corr_pearson"], ["Spearman rank correlation", "Pearson linear correlation"]):
        m = T[k].rename(index=lab, columns=lab)
        sns.heatmap(m, annot=True, fmt=".2f", cmap="RdBu_r", vmin=-1, vmax=1, center=0, square=True, linewidths=.5,
                    cbar_kws={"shrink": .75, "label": "correlation coefficient"}, ax=ax, annot_kws={"fontsize": 8})
        ax.set_title(ttl)
    fig.suptitle("Fig. 10  Correlation structure of the numeric variables and the outcome", fontweight="bold", y=1.02)
    fig.tight_layout()
    return _save(fig, "fig10_correlation_heatmaps")


# ------------------------------------------------------------------------------ Figure 11
def fig11_cramers_heatmap(T):
    m = T["cramers_matrix"].astype(float)
    mask = np.triu(np.ones_like(m, dtype=bool), k=1)
    fig, ax = plt.subplots(figsize=(8.5, 7))
    sns.heatmap(m, mask=mask, annot=True, fmt=".2f", cmap="viridis", vmin=0, vmax=.5, square=True, linewidths=.5,
                cbar_kws={"shrink": .75, "label": "Cramer's V (bias-corrected)"}, ax=ax, annot_kws={"fontsize": 8})
    ax.set_title("Fig. 11  Association between categorical variables (and the outcome 'y')")
    return _save(fig, "fig11_cramers_heatmap")


# ------------------------------------------------------------------------------ Figure 12
def fig12_pairplot(cdf, n=2000):
    s = cdf.sample(n, random_state=SEED)
    d = pd.DataFrame({"age": s["age"], "balance\n(signed log)": signed_log1p(s["balance"]),
                      "duration\n(log1p s)": np.log1p(s["duration"]), "campaign\n(log1p)": np.log1p(s["campaign"]),
                      "previous\n(log1p)": np.log1p(s["previous"]), "Subscribed": s["y"].map({"no": "No", "yes": "Yes"})})
    g = sns.pairplot(d, hue="Subscribed", palette={"No": C_NO, "Yes": C_YES}, corner=True, diag_kind="kde", diag_kws={"common_norm": False},
                     plot_kws={"s": 8, "alpha": .45, "edgecolor": "none"}, height=2.1)
    g.figure.suptitle(f"Fig. 12  Pairplot of transformed numeric variables (random sample of {n:,} clients)", fontweight="bold", y=1.02)
    path = FIG_DIR / "fig12_pairplot.png"
    g.figure.savefig(path, bbox_inches="tight", facecolor="white"); plt.close(g.figure)
    return path


# ------------------------------------------------------------------------------ Figure 13
def fig13_age_and_balance(cdf):
    d = cdf.assign(age_group=age_group(cdf["age"]).astype(str))
    t = rate_table(d, "age_group", order=["<25", "25-34", "35-44", "45-54", "55-64", "65+"])
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))
    ax = axes[0]
    err = np.vstack([t["rate"] - t["ci_low"], t["ci_high"] - t["rate"]]) * 100
    ax.errorbar(range(len(t)), t["rate"] * 100, yerr=err, fmt="o-", color=C_ACC, capsize=4, lw=2, ms=7)
    for i, (r, n) in enumerate(zip(t["rate"], t["n"])):
        ax.text(i, r * 100 + 3.2, f"n={int(n):,}", ha="center", fontsize=8)
    ax.axhline(cdf["y_bin"].mean() * 100, color=C_YES, ls="--", label="overall rate")
    ax.set_ylim(0, t["ci_high"].max() * 100 + 9)
    ax.set_xticks(range(len(t))); ax.set_xticklabels(t.index); ax.set_xlabel("Age group (years)"); ax.set_ylabel("Subscription rate (%)")
    ax.set_title("Non-monotonic: the youngest and oldest clients subscribe most"); ax.legend()
    ax = axes[1]
    d2 = pd.DataFrame({"sl": signed_log1p(cdf["balance"]), "Subscribed": cdf["y"].map({"no": "No", "yes": "Yes"})})
    sns.violinplot(data=d2, x="Subscribed", y="sl", hue="Subscribed", palette={"No": C_NO, "Yes": C_YES}, inner="quartile",
                   cut=0, ax=ax, legend=False)
    ticks = np.array([-1000, -100, 0, 100, 1000, 10000, 100000]); ax.set_yticks(signed_log1p(ticks))
    ax.set_yticklabels([f"{t_:,}" for t_ in ticks]); ax.set_ylabel("Balance (EUR, signed-log scale)")
    ax.set_title("Subscribers hold higher balances (but heavily overlap)")
    fig.suptitle("Fig. 13  Age and account balance versus subscription", fontweight="bold", y=1.03)
    fig.tight_layout()
    return _save(fig, "fig13_age_and_balance")


# ------------------------------------------------------------------------------ Figure 14
def fig14_odds_ratio_forest(T, top=16):
    lo = T["logit_odds_ratios"].copy()
    lo["effect"] = np.abs(np.log(lo["odds_ratio"]))
    lo = lo.sort_values("effect", ascending=False).head(top).sort_values("odds_ratio")
    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    ax.errorbar(lo["odds_ratio"], range(len(lo)), xerr=[lo["odds_ratio"] - lo["ci_low"], lo["ci_high"] - lo["odds_ratio"]],
                fmt="o", color=C_ACC, ecolor=C_GREY, capsize=3)
    ax.axvline(1, color="k", ls="--", lw=1); ax.set_xscale("log")
    ax.set_yticks(range(len(lo))); ax.set_yticklabels(lo.index); ax.set_xlabel("Adjusted odds ratio (log scale, 95% CI)")
    ax.set_title("Fig. 14  Multivariable logistic regression: the 16 strongest adjusted associations")
    ax.grid(axis="y", visible=False)
    return _save(fig, "fig14_odds_ratio_forest")


def make_all_eda_figures(cdf, R):
    T = R["_tables"]
    return {1: fig01_class_balance(cdf), 2: fig02_numeric_histograms(cdf), 3: fig03_outlier_boxplots(cdf, T["outliers_iqr"]),
            4: fig04_categorical_counts(cdf), 5: fig05_rate_by_category(cdf), 6: fig06_month_volume_vs_rate(cdf),
            7: fig07_count_distribution(cdf, R), 8: fig08_age_fits(cdf, T), 9: fig09_duration_fits(cdf, T),
            10: fig10_correlation_heatmaps(T), 11: fig11_cramers_heatmap(T), 12: fig12_pairplot(cdf),
            13: fig13_age_and_balance(cdf), 14: fig14_odds_ratio_forest(T)}
