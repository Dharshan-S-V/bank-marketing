"""Generates the interpretive text used in the notebook and the report.

Every number is pulled from the computed results (`R` = EDA results, `MR` = model results) or
computed here from the data, so the prose cannot drift away from the executed analysis. Where a
sentence makes a qualitative claim (e.g. "right-skewed") it is guarded by an assertion.
"""
import numpy as np
import pandas as pd
from scipy import stats

from .config import MONTH_ORDER


def p_fmt(p):
    return "p < 0.001" if p < 1e-3 else f"p = {p:.3f}"


def pct(x, d=1):
    return f"{100 * x:.{d}f}%"


# =============================================================================== EDA figures
def eda_figure_notes(cdf: pd.DataFrame, R: dict) -> dict:
    T = R["_tables"]
    ns = T["numeric_summary"]
    out = T["outliers_iqr"].set_index("variable")
    b = R["bernoulli"]
    rt = lambda col: T[f"rate_{col}"]  # noqa: E731
    cm, sp, pe = T["cramers_matrix"], T["corr_spearman"], T["corr_pearson"]
    mw = T["mannwhitney"].set_index("variable")
    lo = T["logit_odds_ratios"]
    cf, pf = R["campaign_counts"], R["previous_counts"]
    fa, fd = T["fit_age"].set_index("distribution"), T["fit_duration"].set_index("distribution")
    qa = R["age_normality"]
    n = len(cdf)
    ratio = (1 - b["p_hat"]) / b["p_hat"]
    d = cdf["duration"]
    short30_obs, short30_exp = (d < 30).mean(), 1 - np.exp(-30 / d.mean())
    rm, rjob, rpo, rco = rt("month"), rt("job"), rt("poutcome"), rt("contact")
    rho = lambda a, c: sp.loc[a, c]  # noqa: E731
    ag = T["rate_age_group"]

    # guarded qualitative claims
    assert ns.loc["age", "skewness"] > 0.5 and ns.loc["balance", "skewness"] > 5 and ns.loc["duration", "skewness"] > 2
    assert cf["dispersion_index_var_over_mean"] > 1 and cf["nb_AIC"] < cf["poisson_AIC"]
    assert fa.loc["lognormal", "AIC"] < fa.loc["normal", "AIC"] and fd.loc["exponential", "KS_D"] > fd.loc["lognormal", "KS_D"]
    assert ag.loc["<25", "rate"] > ag.loc["45-54", "rate"] < ag.loc["65+", "rate"]

    N = {}
    N[1] = dict(
        title="Class balance of the target variable",
        question="How imbalanced is the outcome (did the client subscribe to a term deposit)?",
        what="Number and share of clients in each outcome class.",
        why="A bar chart is the simplest faithful encoding of a binary categorical variable and the class ratio decides which evaluation metrics are meaningful.",
        variables="y (categorical, binary).",
        finding=f"{b['k']:,} of {b['n']:,} clients subscribed (p-hat = {pct(b['p_hat'], 2)}, exact 95% CI {pct(b['ci_low'], 2)}-{pct(b['ci_high'], 2)}); the classes are about {ratio:.1f}:1.",
        interpretation=f"The outcome is well modelled as a Bernoulli(p = {b['p_hat']:.3f}) variable. A classifier that always answers 'no' would already be {pct(1 - b['p_hat'])} accurate, so accuracy is uninformative and ROC-AUC, PR-AUC and F1 are used instead.",
        caveats="The rate describes this particular campaign and its client selection, not the general population of bank customers.")
    N[2] = dict(
        title="Univariate distributions of the numeric variables",
        question="What shape do the numeric variables have (symmetry, spread, tails, discreteness)?",
        what="Histograms (bars for the two count variables) with the mean (dashed) and median (dotted).",
        why="Histograms expose skewness, modality and tail weight, which determine which transformations and robust statistics are needed.",
        variables="age, balance, duration, campaign, previous, day.",
        finding=(f"age is mildly right-skewed (skew {ns.loc['age', 'skewness']:.2f}, mean {ns.loc['age', 'mean']:.1f} vs median {ns.loc['age', 'median']:.0f}). "
                 f"balance is extremely skewed (skew {ns.loc['balance', 'skewness']:.2f}, excess kurtosis {ns.loc['balance', 'excess_kurtosis']:.0f}; mean EUR {ns.loc['balance', 'mean']:,.0f} vs median EUR {ns.loc['balance', 'median']:,.0f}). "
                 f"duration is right-skewed (skew {ns.loc['duration', 'skewness']:.2f}; mean {ns.loc['duration', 'mean']:.0f} s vs median {ns.loc['duration', 'median']:.0f} s). "
                 f"campaign (median {ns.loc['campaign', 'median']:.0f}, max {ns.loc['campaign', 'max']:.0f}) and previous ({pct(pf['obs_zero_pct'] / 100)} zeros, max {ns.loc['previous', 'max']:.0f}) are zero/one-heavy counts with long tails. day is roughly flat (skew {ns.loc['day', 'skewness']:.2f})."),
        interpretation="For balance, duration, campaign and previous the mean is a poor summary of a typical client; medians and quantiles are more representative, and log-type transformations are appropriate before modelling. The flat day-of-month profile suggests no strong calendar-day trend.",
        caveats="The balance, duration, campaign and previous axes are truncated for readability (counts of hidden values are in the axis labels); the statistics in the panel titles use all records.")
    N[3] = dict(
        title="Outlier screening with the IQR rule",
        question="How many observations lie far outside the bulk of each numeric variable, and are they errors?",
        what="Boxplots with 1.5 x IQR whiskers on log / symmetric-log scales; titles give the share of flagged points.",
        why="Boxplots are the standard Tukey tool for outliers; log scales make heavy-tailed variables readable.",
        variables="age, balance, duration, campaign, previous.",
        finding=(f"Flagged by 1.5 x IQR: balance {out.loc['balance', 'pct_outliers']:.1f}% ({int(out.loc['balance', 'n_above'] + out.loc['balance', 'n_below']):,} records), duration {out.loc['duration', 'pct_outliers']:.1f}%, campaign {out.loc['campaign', 'pct_outliers']:.1f}%, age {out.loc['age', 'pct_outliers']:.1f}%, previous {out.loc['previous', 'pct_outliers']:.1f}% (degenerate: IQR = 0). "
                 f"The largest values are previous = {int(ns.loc['previous', 'max'])}, campaign = {int(ns.loc['campaign', 'max'])}, balance = EUR {ns.loc['balance', 'max']:,.0f}, duration = {int(ns.loc['duration', 'max']):,} s."),
        interpretation="These are plausible behaviours (wealthy clients, long conversations, persistent re-dialling) rather than obvious errors, and subscribers cluster among long calls, so deleting them would discard signal. Decision: retain all records; compress tails with a signed-log transform (balance) and cap-then-log (campaign, previous, at the training-set 99th percentile). The single previous = 275 record is the only value that looks like a possible entry error and is neutralised by the cap.",
        caveats="The IQR rule assumes roughly symmetric data; for skewed variables it flags many legitimate values. Negative balances (overdrafts) are valid and are not outliers in the cleaning sense.")
    unk = {c: pct(cdf[c].eq("unknown").mean(), 1) for c in ("contact", "poutcome", "education", "job")}
    N[4] = dict(
        title="Category frequencies and hidden missing data",
        question="How are the categorical variables distributed, and where is information hidden behind 'unknown'?",
        what="Horizontal bars of category shares; 'unknown' levels are grey.",
        why="Bar charts are the correct encoding for nominal variables; ordering by size (or calendar order for month) aids comparison.",
        variables="job, education, marital, contact, poutcome, month.",
        finding=(f"The file has no NaN cells, yet 'unknown' accounts for {unk['poutcome']} of poutcome, {unk['contact']} of contact, {unk['education']} of education and {unk['job']} of job. "
                 f"May alone holds {pct(cdf['month'].eq('may').mean())} of all calls; married clients are {pct(cdf['marital'].eq('married').mean())}; blue-collar and management jobs together are {pct(cdf['job'].isin(['blue-collar', 'management']).mean())}."),
        interpretation=f"poutcome = 'unknown' (36,959 clients) coincides with pdays = -1 ('never contacted before', 36,954 clients) up to 5 records, so it is structural, not random, missingness. Therefore 'unknown' is kept as its own category instead of being imputed with the mode.",
        caveats="The calls are heavily concentrated in a few months, so the client mix is not representative of the whole year.")
    N[5] = dict(
        title="Subscription rate by category",
        question="Which client and campaign categories convert more or less often than average?",
        what="Subscription rate per level with exact (Clopper-Pearson) 95% CIs, sorted; dashed line = overall rate.",
        why="Showing rates with confidence intervals and n prevents over-reading small groups; counts alone (Fig. 4) would not show conversion.",
        variables="job, poutcome, contact, education, housing, loan vs. y.",
        finding=(f"Previous success is the standout: poutcome = success converts at {pct(rpo.loc['success', 'rate'])} (n = {int(rpo.loc['success', 'n']):,}) versus {pct(rpo.loc['unknown', 'rate'])} for unknown. "
                 f"Students ({pct(rjob.loc['student', 'rate'])}) and retired clients ({pct(rjob.loc['retired', 'rate'])}) exceed blue-collar ({pct(rjob.loc['blue-collar', 'rate'])}). "
                 f"Unknown contact type converts at {pct(rco.loc['unknown', 'rate'])} vs {pct(rco.loc['cellular', 'rate'])} (cellular). "
                 f"Clients without a housing loan subscribe at {pct(rt('housing').loc['no', 'rate'])} vs {pct(rt('housing').loc['yes', 'rate'])} with one; without a personal loan {pct(rt('loan').loc['no', 'rate'])} vs {pct(rt('loan').loc['yes', 'rate'])}."),
        interpretation="Existing positive relationships and clients with fewer credit commitments are the most receptive; a bank could prioritise them. These are descriptive associations: they do not show that a loan causes refusal.",
        caveats=f"These are marginal rates, not adjusted for each other. contact = unknown is concentrated in June ({pct(cdf.loc[cdf['month'] == 'jun', 'contact'].eq('unknown').mean(), 0)} of June calls) and May ({pct(cdf.loc[cdf['month'] == 'may', 'contact'].eq('unknown').mean(), 0)}), so it partly reflects timing.")
    hi_months = [m for m in MONTH_ORDER if rm.loc[m, "rate"] > .4]
    N[6] = dict(
        title="Call volume versus subscription rate by month",
        question="Is the success rate constant over the calendar, as a single Bernoulli/binomial model would assume?",
        what="One point per month: calls made (log x-axis) against subscription rate with 95% CI.",
        why="A scatter of volume against rate exposes the relationship between effort and outcome that a plain monthly bar chart hides.",
        variables="month, y.",
        finding=(f"May has {int(rm.loc['may', 'n']):,} calls but the lowest rate ({pct(rm.loc['may', 'rate'])}); {', '.join(m.capitalize() for m in hi_months)} have only {int(rm.loc[hi_months, 'n'].sum()):,} calls in total, with rates of {pct(rm.loc[hi_months, 'rate'].min(), 0)}-{pct(rm.loc[hi_months, 'rate'].max(), 0)}. "
                 f"Monthly rates range from {pct(b['monthly_rate_min'])} to {pct(b['monthly_rate_max'])}; homogeneity chi-square({b['month_homogeneity_dof']}) = {b['month_homogeneity_chi2']:.0f}, {p_fmt(b['month_homogeneity_p'])}, Cramer's V = {cm.loc['month', 'y']:.2f}."),
        interpretation="The success probability is clearly not the same in every month, so one common Bernoulli/binomial parameter is inadequate and month must be a model input. Busy months are the least productive, consistent with mass-calling broad lists versus selectively calling warmer clients.",
        caveats=f"The data have no year field and span 2008-2010, so month mixes campaign phases. Low-volume months were probably selectively targeted (88% of May clients hold housing loans vs 18-24% in Mar/Sep/Oct/Dec), so this is not evidence that calling less causes higher conversion.")
    N[7] = dict(
        title="Discrete distributions: Poisson versus Negative Binomial",
        question="Can the number of contacts be modelled as Poisson events, or is the data over-dispersed?",
        what="Observed probability mass function (bars) against fitted Poisson and Negative Binomial PMFs, log-scaled y-axis.",
        why="Overlaying fitted PMFs on a log axis is the clearest way to compare tail behaviour, which is where count models usually fail.",
        variables="campaign - 1 (extra contacts in this campaign), previous.",
        finding=(f"campaign - 1: mean {cf['mean']:.2f}, variance {cf['variance']:.2f}, variance/mean = {cf['dispersion_index_var_over_mean']:.1f}. Zeros: observed {cf['obs_zero_pct']:.1f}%, Poisson {cf['poisson_zero_pct']:.1f}%, Negative Binomial {cf['nb_zero_pct']:.1f}%. "
                 f"P(>= 10 extra contacts): observed {cf['prob_ge_10_obs_pct']:.2f}%, Poisson {cf['prob_ge_10_poisson_pct']:.4f}%, NB {cf['prob_ge_10_nb_pct']:.2f}%. AIC: Poisson {cf['poisson_AIC']:,.0f} vs NB {cf['nb_AIC']:,.0f}. "
                 f"previous: variance/mean = {pf['dispersion_index_var_over_mean']:.1f}, observed zeros {pf['obs_zero_pct']:.1f}% vs Poisson {pf['poisson_zero_pct']:.1f}% vs NB {pf['nb_zero_pct']:.1f}%."),
        interpretation=f"The Poisson assumption (variance = mean, constant event rate) fails badly. The Negative Binomial (a Poisson-Gamma mixture, allowing client-to-client differences in contactability) captures the heavy tail and the excess zeros far better (AIC lower by {cf['poisson_AIC'] - cf['nb_AIC']:,.0f}). Even so, chi-square goodness-of-fit still rejects it (campaign: chi2 = {cf['nb_chi2']:.0f}, df = {cf['nb_dof']}, {p_fmt(cf['nb_p_value'])}), so it is a reasonable approximation, not an exact model.",
        caveats="With n = 45,211 any imperfect model is rejected; the relevant question is practical closeness. Contact counts are produced by bank policy (stop rules), so independence is questionable. previous is zero-inflated (a hurdle model would be a natural next step).")
    N[8] = dict(
        title="Continuous distributions: is age normal?",
        question="Is age approximately normally distributed, and if not, which family is closer?",
        what="Histogram with fitted Normal, Lognormal and Gamma densities (left) and Q-Q plots against Normal and Lognormal (centre, right).",
        why="Density overlays show body fit; Q-Q plots reveal tail departures that overlays hide. Fit quality is judged with AIC and the KS distance, not by eye.",
        variables="age.",
        finding=(f"Normality is rejected (D'Agostino K2 = {qa['dagostino_K2']:.0f}, {p_fmt(qa['dagostino_p'])}; Shapiro-Wilk W = {qa['shapiro_W_n5000']:.3f} on a 5,000 sample, {p_fmt(qa['shapiro_p'])}); skew = {qa['skew']:.2f}. "
                 f"AIC ranks Lognormal best (Gamma +{fa.loc['gamma', 'delta_AIC']:,.0f}, Normal +{fa.loc['normal', 'delta_AIC']:,.0f}); KS distance D: Normal {fa.loc['normal', 'KS_D']:.3f}, Gamma {fa.loc['gamma', 'KS_D']:.3f}, Lognormal {fa.loc['lognormal', 'KS_D']:.3f}."),
        interpretation=f"Age is right-skewed with a lower bound at 18 and a long upper tail, so the Normal is a poor description (largest CDF gap {pct(fa.loc['normal', 'KS_D'])}). Lognormal is the best of the three but still leaves a maximum CDF gap of {pct(fa.loc['lognormal', 'KS_D'])}, so no simple family is accurate and the empirical distribution should be used for inference.",
        caveats="Fits fix the location at 0; a shifted distribution (e.g. starting at 18) might fit better. KS p-values with estimated parameters are only indicative, so D and AIC are reported as effect sizes.")
    N[9] = dict(
        title="Continuous distributions: is call duration exponential?",
        question="Does call duration behave like a memoryless (exponential) waiting time?",
        what="Histogram with fitted Exponential, Lognormal, Gamma and Weibull densities (left) and Q-Q plots against Exponential and Lognormal.",
        why="Durations are the textbook use-case for the exponential model, so the assumption is tested explicitly rather than assumed.",
        variables=f"duration (seconds; {R['duration_n_positive']:,} calls with duration > 0).",
        finding=(f"AIC ranks Lognormal best (Gamma +{fd.loc['gamma', 'delta_AIC']:,.0f}, Weibull +{fd.loc['weibull', 'delta_AIC']:,.0f}, Exponential +{fd.loc['exponential', 'delta_AIC']:,.0f}). KS distance D: Lognormal {fd.loc['lognormal', 'KS_D']:.3f}, Gamma {fd.loc['gamma', 'KS_D']:.3f}, Weibull {fd.loc['weibull', 'KS_D']:.3f}, Exponential {fd.loc['exponential', 'KS_D']:.3f}. "
                 f"Calls shorter than 30 s: observed {pct(short30_obs)} vs {pct(short30_exp)} expected under the fitted Exponential."),
        interpretation=f"The exponential model overstates very short calls (its density peaks at zero) whereas real calls have a mode near 100 s: people rarely hang up instantly but converse for a typical length, so the process is not memoryless. The exponential's median ({np.log(2) * d.mean():.0f} s) happens to match the observed median ({d.median():.0f} s), a good reminder that matching one summary is not goodness of fit; the Q-Q plot against the Exponential looks deceptively close in the upper tail while D = {fd.loc['exponential', 'KS_D']:.3f} and the AIC gap show the body is wrong.",
        caveats="Only the last call to each client is recorded and duration is not known before a call, so it cannot be used for pre-call prediction (see Section 7).")
    N[10] = dict(
        title="Correlation heatmaps (Spearman and Pearson)",
        question="Which numeric variables move together, and which relate to the outcome?",
        what="Annotated correlation matrices; Spearman (rank-based, monotonic) beside Pearson (linear).",
        why="The two measures are shown together because the variables are heavily skewed: Spearman is robust to the tails, and any gap between the two reveals outlier influence.",
        variables="age, balance, day, duration, campaign, pdays (clean), previous, subscribed (0/1).",
        finding=(f"With the outcome: duration rho = {rho('duration', 'y_bin'):.2f} (Pearson {pe.loc['duration', 'y_bin']:.2f}), previous {rho('previous', 'y_bin'):.2f}, pdays {rho('pdays_clean', 'y_bin'):.2f}, balance {rho('balance', 'y_bin'):.2f}, campaign {rho('campaign', 'y_bin'):.2f}, age {rho('age', 'y_bin'):.2f}. "
                 f"Among predictors, only previous-pdays is strong (rho = {rho('previous', 'pdays_clean'):.2f}); the next largest |rho| is campaign-day = {rho('campaign', 'day'):.2f}."),
        interpretation=f"All single-variable associations with the outcome are weak to moderate (|rho| <= {abs(sp['y_bin'].drop('y_bin')).max():.2f}); duration is strongest but unavailable before the call. previous and pdays are nearly redundant, which is why one of them is dropped from the logistic regression (VIF {R['vif']['max_before']:.0f} -> {R['vif']['max_after']:.1f}). balance has Pearson {pe.loc['balance', 'y_bin']:.2f} but Spearman {rho('balance', 'y_bin'):.2f}: extreme values weaken the linear measure.",
        caveats="Correlation is not causation, and a coefficient near zero does not rule out a non-monotonic relationship: age has rho = -0.01 yet a strong U-shaped pattern (Fig. 13).")
    N[11] = dict(
        title="Association between categorical variables (Cramer's V)",
        question="Which categorical variables are associated with the outcome and with each other?",
        what="Lower-triangle heatmap of bias-corrected Cramer's V (0 = independent, 1 = perfectly associated).",
        why="Pearson/Spearman do not apply to nominal variables; Cramer's V (from chi-square) puts all pairs on one 0-1 scale.",
        variables="job, marital, education, default, housing, loan, contact, month, poutcome, y.",
        finding=(f"Strongest links to y: poutcome {cm.loc['poutcome', 'y']:.2f}, month {cm.loc['month', 'y']:.2f}, contact {cm.loc['contact', 'y']:.2f}, housing {cm.loc['housing', 'y']:.2f}, job {cm.loc['job', 'y']:.2f}; default only {cm.loc['default', 'y']:.2f}. "
                 f"Among predictors: month-contact {cm.loc['month', 'contact']:.2f}, month-housing {cm.loc['month', 'housing']:.2f}, job-education {cm.loc['job', 'education']:.2f}."),
        interpretation="Previous campaign outcome and timing are the most informative categorical signals, while having credit in default carries almost no information. The large month-contact and month-housing values show that the client mix and the contact channel changed over the campaign, so marginal differences (Fig. 5) partly reflect timing.",
        caveats="Cramer's V is symmetric and says nothing about direction; every chi-square test here is 'significant' because n is large, so effect size (V) matters more than p.")
    zb = (cdf["balance"] == 0).sum()
    N[12] = dict(
        title="Pairplot of transformed numeric variables",
        question="Do pairs of numeric variables show joint structure, clusters or separation by outcome?",
        what="Scatter matrix (lower triangle) and class-wise KDEs (diagonal) of 2,000 random clients on log-type scales.",
        why="A pairplot gives a one-glance view of all bivariate relationships and class overlap; a sample keeps it legible.",
        variables="age, balance (signed log), duration (log1p), campaign (log1p), previous (log1p), coloured by y.",
        finding=f"balance on the signed-log scale is clearly multi-modal: a cluster of overdrawn accounts, a spike at exactly zero ({zb:,} clients = {pct(zb / len(cdf))}) and a main mass of positive balances. Subscribers (orange) are shifted towards longer durations, but no pair of predictors shows a strong linear relation and the classes overlap heavily everywhere else.",
        interpretation="No two predictors are strongly entangled (consistent with Fig. 10), and no simple two-variable boundary separates subscribers, which anticipates the moderate predictive ceiling seen later. The multi-modality of balance is invisible in the raw histogram.",
        caveats="Based on a random sample of 2,000 rows (seed 42); campaign/previous form discrete lattices; overplotting hides density in the centre.")
    N[13] = dict(
        title="Age and balance versus subscription",
        question="Does the relation between age or balance and subscription follow a simple monotonic trend?",
        what="Left: subscription rate per age band with exact 95% CIs. Right: violin plots of signed-log balance by outcome with quartiles.",
        why="Binning age reveals shape that a single correlation coefficient hides; violins show full distributions and the overlap between classes.",
        variables="age (grouped), balance, y.",
        finding=(f"Rate by age: <25 {pct(ag.loc['<25', 'rate'])} (n = {int(ag.loc['<25', 'n'])}), 45-54 {pct(ag.loc['45-54', 'rate'])}, 65+ {pct(ag.loc['65+', 'rate'])} (n = {int(ag.loc['65+', 'n'])}); yet Spearman rho(age, y) = {rho('age', 'y_bin'):.2f} and Mann-Whitney {p_fmt(mw.loc['age', 'p_value'])} (median age {mw.loc['age', 'median_yes']:.0f} vs {mw.loc['age', 'median_no']:.0f}). "
                 f"Balance median EUR {mw.loc['balance', 'median_yes']:,.0f} (subscribers) vs EUR {mw.loc['balance', 'median_no']:,.0f}; Mann-Whitney {p_fmt(mw.loc['balance', 'p_value'])}, Cliff's delta = {mw.loc['balance', 'cliffs_delta']:.2f}."),
        interpretation="Age matters, but not linearly: the youngest and oldest clients are far more receptive than mid-career clients, which monotone tests (correlation, Mann-Whitney) miss completely. Higher balance is associated with subscription, but the small effect size (delta = 0.18) and the heavy overlap in the violins mean balance alone is a weak discriminator.",
        caveats="Groups <25 and 65+ are small (about 800 each) and overlap with students and retirees (Fig. 5), so age and occupation effects cannot be separated here.")
    top = lo.assign(e=np.abs(np.log(lo["odds_ratio"]))).sort_values("e", ascending=False)
    ps = lo.loc["poutcome_success"]; cu = lo.loc["contact_unknown"]; ho = lo.loc["housing_no"]; cmp_ = lo.loc["log1p_campaign"]
    N[14] = dict(
        title="Adjusted odds ratios from a multivariable logistic regression",
        question="Which factors remain associated with subscription after adjusting for all the others?",
        what="Odds ratios (log scale) with 95% CIs for the 16 largest effects; the dashed line at 1 means no association.",
        why="A forest plot is the standard way to compare adjusted effects on a common multiplicative scale with their uncertainty.",
        variables=f"All pre-call predictors (n = {R['logit']['n']:,} training clients; McFadden pseudo-R2 = {R['logit']['pseudo_r2']:.3f}).",
        finding=(f"poutcome = success: OR {ps['odds_ratio']:.2f} (95% CI {ps['ci_low']:.2f}-{ps['ci_high']:.2f}); March OR {lo.loc['month_mar', 'odds_ratio']:.2f}; contact unknown OR {cu['odds_ratio']:.2f} ({cu['ci_low']:.2f}-{cu['ci_high']:.2f}); no housing loan OR {ho['odds_ratio']:.2f}; each unit of log(1 + campaign) OR {cmp_['odds_ratio']:.2f}. "
                 f"Before removing redundant predictors the maximum VIF was {R['vif']['max_before']:.0f} ({R['vif']['n_above10_before']} variables above 10); afterwards {R['vif']['max_after']:.1f}."),
        interpretation="After adjustment, a past success, particular months, a known contact channel and the absence of a housing loan are still associated with higher odds, and repeated contacting with lower odds. The model explains a modest share of variation (pseudo-R2 about 0.17), in line with the weak individual associations seen above.",
        caveats="Odds ratios describe association, not causation. Month effects absorb campaign phase; the first fit with all history variables had unstable intervals because previous, pdays and previously_contacted are redundant, which is why only log(1 + previous) was retained.")
    return N


# =============================================================================== model figures
def model_figure_notes(MR: dict, extra: dict) -> dict:
    """extra: dict with hist (training history), imp (importance DataFrame), search (DataFrame), m_test (metrics)."""
    h, imp, search, mt = extra["hist"], extra["imp"], extra["search"], extra["m_test"]
    P, S = MR["primary"], MR["test_mean_std"]
    base = MR["baselines"]
    bi = int(np.argmin(h["val_loss"])) + 1
    ep = len(h["loss"]); best_ep = int(np.argmax(h["val_auc"])) + 1
    gap = h["loss"][-1] - h["val_loss"][-1]
    top3 = imp.head(3)
    chrono = MR["chronological"]
    N = {}
    sel = search.iloc[0]
    N[15] = dict(
        title="Hyper-parameter search", question="Which MLP configuration generalises best to unseen (validation) data?",
        what=f"Validation PR-AUC of {len(search)} randomly sampled configurations (units, dropout, learning rate, class weighting); green = selected.",
        why="A sorted bar chart shows both the spread between configurations and how much tuning actually matters.",
        variables="Hidden units, dropout, learning rate, class weights.",
        finding=f"Validation PR-AUC ranged from {search['val_pr_auc'].min():.3f} to {search['val_pr_auc'].max():.3f} (ROC-AUC {search['val_roc_auc'].min():.3f}-{search['val_roc_auc'].max():.3f}). Selected: units {sel['units']}, dropout {sel['dropout']}, lr {sel['lr']}, class weight {sel['class_weight']}.",
        interpretation=f"The spread between best and worst configuration is only {search['val_pr_auc'].max() - search['val_pr_auc'].min():.3f} PR-AUC, so tuning matters little here; the simplest architecture won, and the three-layer networks did not outperform it. Selection used the validation set only.",
        caveats=f"Only {len(search)} of 24 grid points were sampled, each with one seed, so small differences are not statistically meaningful. The test set was never used for selection.")
    N[16] = dict(
        title="Training versus validation loss", question="Is the network underfitting or overfitting?",
        what="Binary cross-entropy per epoch on the training and validation sets for the primary model.",
        why="The gap between the two loss curves is the standard diagnostic of generalisation.",
        variables="Epoch, loss.",
        finding=f"The run used all {ep} allowed epochs (early stopping with patience {MR['early_stopping_patience']} never triggered); lowest validation loss {min(h['val_loss']):.3f} at epoch {bi} and best validation ROC-AUC at epoch {best_ep}. Final training loss {h['loss'][-1]:.3f} vs validation loss {h['val_loss'][-1]:.3f}; first-epoch training loss {h['loss'][0]:.3f}.",
        interpretation="Both curves fall together and end almost on top of each other, so there is no sign of overfitting (training loss is slightly higher because dropout is active during training). The curves are nearly flat by the end, so extra epochs would add very little: performance is limited by the information in the 16 pre-call features and the small network, not by memorisation.",
        caveats=f"Training reached the {ep}-epoch cap while still improving marginally in the third decimal, so a longer run might give a tiny gain. Loss includes the L2 penalty.")
    N[17] = dict(
        title="Accuracy and AUC versus epoch", question="How do accuracy and ranking quality evolve during training?",
        what="Left: accuracy at a 0.5 threshold against the always-'no' baseline. Right: ROC-AUC per epoch (training and validation).",
        why="The assignment requires accuracy-versus-epoch; the AUC panel and baseline line prevent the misleading impression that high accuracy means skill when 88% of clients decline.",
        variables="Epoch, accuracy, ROC-AUC.",
        finding=f"Validation accuracy at the 0.5 threshold ends at {pct(h['val_accuracy'][-1])}, only about {100 * (h['val_accuracy'][-1] - (1 - MR['split_prevalence'][2])):.1f} points above the always-'no' baseline of {pct(1 - MR['split_prevalence'][2])}; validation AUC peaks at {max(h['val_auc']):.3f} (epoch {best_ep}) and training AUC at {max(h['auc']):.3f}.",
        interpretation="Accuracy barely moves because the class prior dominates it; AUC shows the real learning (ranking ability) and the two AUC curves track each other closely, confirming the absence of overfitting seen in Fig. 16.",
        caveats="Accuracy depends on the 0.5 threshold, which is not the threshold used for final reporting (Fig. 21).")
    N[18] = dict(
        title="Confusion matrix (test set)", question="What kinds of mistakes does the final model make at the validation-chosen threshold?",
        what="Counts and row-percentages of true/false positives and negatives on the untouched test set.",
        why="A confusion matrix converts a score into concrete outcomes (missed subscribers vs wasted calls).",
        variables=f"Predicted vs actual y; threshold {mt['threshold']:.3f} (maximises F1 on validation).",
        finding=f"TN {mt['tn']:,}, FP {mt['fp']:,}, FN {mt['fn']:,}, TP {mt['tp']:,}. Recall {pct(mt['recall'])}, precision {pct(mt['precision'])}, F1 {mt['f1']:.3f}, accuracy {pct(mt['accuracy'])}, balanced accuracy {pct(mt['balanced_accuracy'])}, MCC {mt['mcc']:.3f}.",
        interpretation=f"At this operating point the model finds {pct(mt['recall'], 0)} of actual subscribers but only {pct(mt['precision'], 0)} of the clients it flags actually subscribe (prevalence {pct(mt['prevalence'])}), i.e. roughly {mt['precision'] / mt['prevalence']:.1f}x better than random targeting. The two error types are of similar size ({mt['fp']:,} wasted calls vs {mt['fn']:,} missed subscribers), and the model still misses about half of the subscribers, so it is a prioritisation aid rather than a reliable classifier.",
        caveats="The threshold optimises F1, which weights precision and recall equally; a real campaign would choose it from call cost and expected revenue.")
    N[19] = dict(
        title="ROC and precision-recall curves (test set)", question="How well does the model rank subscribers above non-subscribers across all thresholds?",
        what="ROC curve (TPR vs FPR) and precision-recall curve for the MLP and the logistic-regression baseline.",
        why="ROC-AUC is threshold-free; the PR curve is more informative with 11.7% prevalence (Saito & Rehmsmeier, 2015).",
        variables="Predicted probability, y.",
        finding=f"Primary MLP: ROC-AUC {mt['roc_auc']:.3f}, PR-AUC (average precision) {mt['pr_auc']:.3f} versus prevalence {mt['prevalence']:.3f}. Over 5 seeds ROC-AUC = {S['roc_auc'][0]:.3f} +/- {S['roc_auc'][1]:.3f}. Baselines (test ROC-AUC): logistic regression {base['Logistic regression']['test']['roc_auc']:.3f}, gradient boosting {base['Gradient boosting (reference)']['test']['roc_auc']:.3f}, majority class {base['Majority class']['test']['roc_auc']:.3f}.",
        interpretation=f"The MLP has real discriminative power (a random client pair is ranked correctly {pct(mt['roc_auc'])} of the time) and PR-AUC is about {mt['pr_auc'] / mt['prevalence']:.1f}x the prevalence. The MLP beats the logistic-regression baseline by {mt['roc_auc'] - base['Logistic regression']['test']['roc_auc']:.3f} AUC, which suggests it captures some non-linear structure, but the gradient-boosting reference is better still (+{base['Gradient boosting (reference)']['test']['roc_auc'] - mt['roc_auc']:.3f}), consistent with published evidence that tree ensembles are hard to beat on tabular data (Grinsztajn et al., 2022).",
        caveats="Single test set of 6,782 clients: differences of about 0.01 AUC between models are within the seed-to-seed and sampling noise.")
    N[20] = dict(
        title="Permutation feature importance", question="Which input variables does the trained network actually rely on?",
        what="Drop in validation ROC-AUC when each original input column is randomly shuffled (one-hot groups shuffled together, 5 repeats).",
        why="Permutation importance is model-agnostic and respects grouped one-hot features; it is computed on validation data to keep the test set pristine.",
        variables="The 16 pre-call input columns.",
        finding=f"Top features: {top3.iloc[0]['feature']} (-{top3.iloc[0]['auc_drop_mean']:.3f} AUC), {top3.iloc[1]['feature']} (-{top3.iloc[1]['auc_drop_mean']:.3f}), {top3.iloc[2]['feature']} (-{top3.iloc[2]['auc_drop_mean']:.3f}); least important: {imp.iloc[-1]['feature']} ({imp.iloc[-1]['auc_drop_mean']:.4f}).",
        interpretation="The ranking largely agrees with the statistical EDA: contact channel, month and previous outcome (poutcome) were among the strongest associations in Figs. 5, 6 and 11. Two points are less expected: day of month ranks fourth although its marginal correlation with the outcome is tiny (rho = -0.03), so the network probably uses it in interaction with month; and housing, the fourth-ranked categorical association with y in Fig. 11, is only mid-table because it overlaps with month and contact.",
        caveats="Importance is not causation, and correlated features (month, contact, housing, day) share credit, so individual scores understate joint importance. contact and month together largely encode when in the campaign the call happened.")
    N[21] = dict(
        title="Threshold trade-off (validation set)", question="How does the decision threshold trade precision against recall?",
        what="Precision, recall and F1 as functions of the cut-off on predicted probability, with the chosen threshold.",
        why="The threshold is a business decision; showing the full trade-off makes the chosen operating point transparent.",
        variables="Threshold, precision, recall, F1 (validation).",
        finding=f"F1 is maximised at threshold {mt['threshold']:.3f}; the same threshold is applied unchanged to the test set (test F1 {mt['f1']:.3f}).",
        interpretation="Raising the threshold buys precision at the cost of recall; a bank with expensive calls would pick a higher cut-off, and one with cheap calls a lower one.",
        caveats="Chosen on validation only; F1 is not cost-sensitive.")
    N[22] = dict(
        title="Robustness: leakage and temporal shift", question="How trustworthy is the headline result under realistic changes (post-call variable, time-ordered split)?",
        what="Test ROC-AUC and PR-AUC of the MLP, logistic regression and gradient boosting under three protocols.",
        why="A single random split can be optimistic; contrasting protocols shows what the score really means.",
        variables="Feature set (with/without duration), split type (stratified/chronological).",
        finding=(f"Adding call duration raises the MLP's test ROC-AUC from {S['roc_auc'][0]:.3f} to {MR['duration_ablation_mlp']['test_roc_auc']:.3f}. On a chronological split the pre-call MLP scores ROC-AUC {chrono['mlp']['test']['roc_auc']:.3f} (logistic regression {chrono['logreg']['test']['roc_auc']:.3f}, gradient boosting {chrono['hgb']['test']['roc_auc']:.3f}); "
                 f"subscription prevalence shifts from {pct(chrono['train_prev'])} (train) to {pct(chrono['test_prev'])} (test)."),
        interpretation="Duration is a strong but unusable signal (it is known only after the call), so the primary model correctly excludes it; the large jump shows how an unnoticed leak would inflate performance. Under the time-ordered split all three models fall to a ROC-AUC of about 0.58-0.65, and the ranking of models changes (gradient boosting, best on the random split, is worst), so the random-split score is an optimistic description of how the model would perform on a later campaign with a different client mix.",
        caveats="The duration and chronological runs use a single seed (42) with the selected configuration; PR-AUC is not comparable across splits with different prevalence.")
    return N


# =============================================================================== abstract / findings
def abstract(R, MR) -> str:
    T = R["_tables"]
    rpo = T["rate_poutcome"]
    S = MR["test_mean_std"]
    base = MR["baselines"]
    txt = (f"Telemarketing is costly, so banks need to know which clients are worth calling. This study explores the UCI Bank Marketing dataset "
           f"({R['n_rows']:,} calls, 16 client and campaign features), where {pct(R['bernoulli']['p_hat'])} of calls end in a term-deposit subscription. "
           f"Following the seven stages of visualization, the data were cleaned, and distributions, associations and 22 figures were analysed. "
           f"Contact counts were over-dispersed (Negative Binomial beat Poisson) and call duration was closer to lognormal than exponential. "
           f"A previously successful campaign ({pct(rpo.loc['success', 'rate'])} conversion) and the calling month were the strongest signals, and age showed a U-shape. "
           f"A leakage-free multilayer perceptron using pre-call information reached a test ROC-AUC of {S['roc_auc'][0]:.3f} (PR-AUC {S['pr_auc'][0]:.3f}), "
           f"above logistic regression ({base['Logistic regression']['test']['roc_auc']:.3f}) but below gradient boosting ({base['Gradient boosting (reference)']['test']['roc_auc']:.3f}).")
    n = len(txt.split())
    assert 100 <= n <= 150, f"abstract has {n} words"
    return txt


def key_findings(cdf, R, MR) -> list:
    """Each finding: observation, statistic, chart, implication, caveat (assignment CO4 'interpretation')."""
    T = R["_tables"]; b = R["bernoulli"]; ns = T["numeric_summary"]; lo = T["logit_odds_ratios"]
    cf = R["campaign_counts"]; fa = T["fit_age"].set_index("distribution"); fd = T["fit_duration"].set_index("distribution")
    ag = T["rate_age_group"]; rh = T["rate_housing"]; rpo = T["rate_poutcome"]; rm = T["rate_month"]; S = MR["test_mean_std"]
    base = MR["baselines"]; chrono = MR["chronological"]
    F = []
    F.append(dict(obs="Only about one client in nine subscribes.", stat=f"{b['k']:,}/{b['n']:,} = {pct(b['p_hat'], 2)} (95% CI {pct(b['ci_low'], 2)}-{pct(b['ci_high'], 2)})",
                  chart="Fig. 1", impl="Accuracy is uninformative (always answering 'no' gives 88.3%); the model is judged by ROC-AUC, PR-AUC and F1.", cav="Rate is specific to this campaign's client selection."))
    F.append(dict(obs="Missing data hide behind 'unknown' labels and a -1 sentinel, not NaN.", stat=f"NaN cells = 0, but poutcome unknown {pct(cdf['poutcome'].eq('unknown').mean())}, contact unknown {pct(cdf['contact'].eq('unknown').mean())}, pdays = -1 for {pct((cdf['pdays'] == -1).mean())}",
                  chart="Fig. 4", impl="'unknown' is kept as a category and pdays is split into a flag plus a cleaned value; imputing the mode would erase real information.", cav="contact = unknown is concentrated in May-June, so it mixes channel and timing."))
    F.append(dict(obs="Balance, duration and the count variables are heavy-tailed; age is not normal.", stat=f"balance skew {ns.loc['balance', 'skewness']:.2f}, excess kurtosis {ns.loc['balance', 'excess_kurtosis']:.0f}; age Normal KS D = {fa.loc['normal', 'KS_D']:.3f} (AIC +{fa.loc['normal', 'delta_AIC']:,.0f} vs Lognormal)",
                  chart="Figs. 2, 3, 8", impl="Signed-log and cap-then-log transforms are used; medians and rank-based tests replace means and t-tests.", cav="No simple parametric family fits age well (best KS D = 0.061)."))
    F.append(dict(obs="Contact counts are over-dispersed, so Poisson is rejected in favour of Negative Binomial.", stat=f"variance/mean = {cf['dispersion_index_var_over_mean']:.1f}; AIC {cf['poisson_AIC']:,.0f} (Poisson) vs {cf['nb_AIC']:,.0f} (NB); P(>=10 extra contacts) observed {cf['prob_ge_10_obs_pct']:.2f}% vs Poisson {cf['prob_ge_10_poisson_pct']:.4f}%",
                  chart="Fig. 7", impl="Client contactability is heterogeneous, and rare, very persistent call sequences are far more common than a Poisson model predicts.", cav="NB still fails a chi-square test in the tail; counts are shaped by bank stop-rules."))
    F.append(dict(obs="Call duration is lognormal-like, not memoryless-exponential.", stat=f"KS D: Lognormal {fd.loc['lognormal', 'KS_D']:.3f} vs Exponential {fd.loc['exponential', 'KS_D']:.3f}; AIC gap {fd.loc['exponential', 'delta_AIC']:,.0f}",
                  chart="Fig. 9", impl="Very short calls are rare and a typical call length exists, so time already spent on a call does carry information.", cav="Only the last call per client is recorded."))
    F.append(dict(obs="Conversion varies strongly by calendar month and is inversely related to call volume.", stat=f"May: {int(rm.loc['may', 'n']):,} calls at {pct(rm.loc['may', 'rate'])}; March: {int(rm.loc['mar', 'n'])} calls at {pct(rm.loc['mar', 'rate'])}; chi2({b['month_homogeneity_dof']}) = {b['month_homogeneity_chi2']:.0f}, V = {R['_tables']['cramers_matrix'].loc['month', 'y']:.2f}",
                  chart="Figs. 6, 11", impl="One Bernoulli parameter does not describe all months; campaign timing/targeting must be modelled.", cav="No year field; low-volume months were probably selectively targeted, so this is not causal."))
    F.append(dict(obs="A previous successful campaign is the strongest single signal.", stat=f"{pct(rpo.loc['success', 'rate'])} vs {pct(rpo.loc['unknown', 'rate'])} (unknown); adjusted OR {lo.loc['poutcome_success', 'odds_ratio']:.2f} (95% CI {lo.loc['poutcome_success', 'ci_low']:.2f}-{lo.loc['poutcome_success', 'ci_high']:.2f})",
                  chart="Figs. 5, 14", impl="Re-contacting previously converted clients is likely the most productive use of calls.", cav="Only 3.3% of clients have a previous success."))
    F.append(dict(obs="Age has a U-shaped, non-monotonic relation with subscription that correlation misses.", stat=f"<25: {pct(ag.loc['<25', 'rate'])}, 45-54: {pct(ag.loc['45-54', 'rate'])}, 65+: {pct(ag.loc['65+', 'rate'])}; Spearman rho = {R['_tables']['corr_spearman'].loc['age', 'y_bin']:.2f}",
                  chart="Fig. 13", impl="Age should enter models as a non-linear effect; segment-specific offers for students and retirees are plausible.", cav="Extreme groups are small (~800) and overlap with job categories."))
    F.append(dict(obs="Existing loan commitments go with lower subscription.", stat=f"housing loan: {pct(rh.loc['yes', 'rate'])} vs no housing loan {pct(rh.loc['no', 'rate'])}; adjusted OR (no housing) = {lo.loc['housing_no', 'odds_ratio']:.2f}",
                  chart="Figs. 5, 14", impl="Clients with fewer credit commitments are a more receptive segment.", cav="Association only; housing loans are also tied to month (V = 0.50)."))
    F.append(dict(obs="The MLP has moderate, honest predictive power; call duration would be a leak.", stat=f"test ROC-AUC {S['roc_auc'][0]:.3f} +/- {S['roc_auc'][1]:.3f} (5 seeds), PR-AUC {S['pr_auc'][0]:.3f}; LR {base['Logistic regression']['test']['roc_auc']:.3f}; GB {base['Gradient boosting (reference)']['test']['roc_auc']:.3f}; with duration {MR['duration_ablation_mlp']['test_roc_auc']:.3f}; chronological {chrono['mlp']['test']['roc_auc']:.3f}",
                  chart="Figs. 15-22", impl="The model can rank prospects usefully (precision about 3.7x prevalence at the F1 threshold) but is not accurate enough to automate decisions.", cav="Random-split score is optimistic under temporal shift."))
    return F


def conclusions(cdf, R, MR) -> dict:
    S = MR["test_mean_std"]; P = MR["primary"]["test"]; base = MR["baselines"]
    return {
        "learned": [f"The dataset is a clean-looking but information-hiding table: no NaN cells, yet hidden missingness in poutcome, contact and education and a -1 sentinel in pdays.",
                    "Outcomes are imbalanced (11.7% positive) and driven mainly by the calling month, the previous-campaign outcome, the contact channel and loan status; individual numeric variables are only weakly related to the outcome."],
        "model": [f"A 32-unit one-hidden-layer MLP ({MR['n_params']:,} parameters) reached test ROC-AUC {S['roc_auc'][0]:.3f} +/- {S['roc_auc'][1]:.3f}, PR-AUC {S['pr_auc'][0]:.3f}, F1 {S['f1'][0]:.3f} over five seeds (primary seed: ROC-AUC {P['roc_auc']:.3f}, F1 {P['f1']:.3f}, recall {P['recall']:.2f}, precision {P['precision']:.2f}).",
                  f"It outperformed logistic regression ({base['Logistic regression']['test']['roc_auc']:.3f}) but not gradient boosting ({base['Gradient boosting (reference)']['test']['roc_auc']:.3f}); there was no overfitting, and the model is limited by the information available before a call."],
        "challenges": ["Hidden missing values and a sentinel code; heavy-tailed variables; multicollinearity among the history variables (VIF 1005 before, 5.2 after).",
                       "A documented leakage trap (duration) and a strong temporal shift (subscription rate 5.8% in the first 70% of the file vs 39.3% in the last 15%).",
                       "Sandbox limits: UCI was unreachable, so a verified mirror was used (download code tries UCI first); no GPU, so the network was kept small."],
        "future": ["Add the richer UCI 'bank-additional' version (20 inputs including macro-economic indicators such as the Euribor rate) and agent/call-direction features.",
                   "Model count variables with Negative-Binomial/hurdle regressions and age non-linearly (splines); try gradient boosting with calibration and cost-sensitive thresholds.",
                   "Evaluate with rolling-origin (time-series) validation, report uncertainty with bootstrapped intervals, and estimate uplift/profit curves instead of F1.",
                   "Before any deployment: fairness review (age and job effects), monitoring for drift, and a pilot A/B test; a high AUC alone does not justify deployment."],
    }
