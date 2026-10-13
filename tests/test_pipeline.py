"""Automated tests for data, preprocessing, leakage, statistics, model and metrics.

Run:  pytest -q
"""
import json

import numpy as np
import pandas as pd
import pytest

from src import config
from src.data_loader import download_dataset, get_data, load_raw, validate
from src.eda import (count_distribution_fit, cramers_v, iqr_outliers, continuous_fits, rate_table)
from src.evaluate import best_f1_threshold, compute_metrics
from src.preprocessing import (Winsorizer, clean, model_columns, prepare_matrices, signed_log1p,
                               split_data)


@pytest.fixture(scope="module")
def raw():
    return get_data()


@pytest.fixture(scope="module")
def cdf(raw):
    return clean(raw)


# ------------------------------------------------------------------ data loading / structure
def test_dataset_downloaded_and_valid(raw):
    assert config.RAW_CSV.exists()
    assert raw.shape == (45211, 17)
    validate(raw)


def test_at_least_15_features(raw):
    assert raw.shape[1] - 1 >= 15, "assignment requires >= 15 features"


def test_expected_columns(raw):
    assert set(raw.columns) == set(config.NUMERIC + config.CATEGORICAL + [config.TARGET])


def test_no_nan_and_no_duplicates(raw):
    assert raw.isna().sum().sum() == 0
    assert raw.duplicated().sum() == 0


def test_validate_rejects_wrong_shape(raw):
    with pytest.raises(ValueError):
        validate(raw.iloc[:100])


def test_download_is_idempotent():
    assert download_dataset() == config.RAW_CSV  # file exists -> no network call


# ------------------------------------------------------------------ cleaning
def test_clean_target_and_sentinel(raw, cdf):
    assert set(cdf["y_bin"].unique()) == {0, 1}
    assert cdf["y_bin"].sum() == (raw["y"] == "yes").sum()
    assert (cdf["pdays_clean"] >= 0).all()
    assert ((cdf["pdays"] == -1) == (cdf["previously_contacted"] == 0)).all()
    assert len(cdf) == len(raw)  # nothing silently dropped


def test_unknown_kept_as_category(cdf):
    assert "unknown" in set(cdf["poutcome"]) and (cdf["contact"] == "unknown").sum() > 0


# ------------------------------------------------------------------ splits
def test_stratified_split_sizes_and_disjoint(cdf):
    tr, va, te = split_data(cdf, "stratified")
    assert len(tr) + len(va) + len(te) == len(cdf)
    assert not (set(tr.index) & set(va.index)) and not (set(tr.index) & set(te.index)) and not (set(va.index) & set(te.index))
    for part, frac in ((tr, .70), (va, .15), (te, .15)):
        assert abs(len(part) / len(cdf) - frac) < .005
        assert abs(part["y_bin"].mean() - cdf["y_bin"].mean()) < .005  # stratification works


def test_split_is_reproducible(cdf):
    a = split_data(cdf, "stratified")[2].index
    b = split_data(cdf, "stratified")[2].index
    assert (a == b).all()


def test_chronological_split_order(cdf):
    tr, va, te = split_data(cdf, "chronological")
    assert tr.index.max() < va.index.min() <= va.index.max() < te.index.min()


# ------------------------------------------------------------------ leakage
def test_target_and_duration_not_in_model_inputs():
    cols = model_columns(include_duration=False)
    assert "y" not in cols and "y_bin" not in cols and "duration" not in cols and "pdays" not in cols


def test_preprocessor_fit_on_train_only(cdf):
    tr, va, te = split_data(cdf, "stratified")
    Xtr, Xva, Xte, ytr, yva, yte, pre, names = prepare_matrices(tr, va, te)
    i = names.index("age")
    assert abs(Xtr[:, i].mean()) < 1e-3 and abs(Xtr[:, i].std() - 1) < 1e-2            # fitted on train
    scaler = pre.named_transformers_["plain"]
    assert scaler.mean_[0] == pytest.approx(tr["age"].mean())                           # train statistics
    assert scaler.mean_[0] != pytest.approx(cdf["age"].mean(), abs=1e-9)                # not full-data statistics
    assert abs(Xva[:, i].mean()) > 1e-6                                                 # val is NOT re-centred


def test_preprocessing_shapes_and_no_nan(cdf):
    tr, va, te = split_data(cdf, "stratified")
    Xtr, Xva, Xte, ytr, yva, yte, pre, names = prepare_matrices(tr, va, te)
    assert Xtr.shape == (len(tr), len(names)) and Xva.shape == (len(va), len(names)) and Xte.shape == (len(te), len(names))
    assert not np.isnan(Xtr).any() and not np.isnan(Xva).any() and not np.isnan(Xte).any()
    assert len(ytr) == len(tr) and set(np.unique(ytr)) == {0, 1}


def test_unseen_category_does_not_crash(cdf):
    tr, va, te = split_data(cdf, "stratified")
    *_, pre, names = prepare_matrices(tr, va, te)
    weird = va.head(5).copy()
    weird["job"] = "astronaut"
    assert pre.transform(weird[model_columns()]).shape == (5, len(names))


def test_winsorizer_uses_training_quantile():
    w = Winsorizer(.9).fit(np.arange(100).reshape(-1, 1))
    assert w.transform(np.array([[500.0]]))[0, 0] == pytest.approx(np.quantile(np.arange(100), .9))


def test_signed_log_handles_negatives():
    out = signed_log1p([-100, 0, 100])
    assert out[0] == pytest.approx(-out[2]) and out[1] == 0


# ------------------------------------------------------------------ statistics
def test_iqr_outliers_detects_planted_outlier():
    df = pd.DataFrame({"x": list(range(1, 51)) + [1000]})
    assert iqr_outliers(df, ["x"]).loc[0, "n_above"] == 1


def test_cramers_v_extremes():
    a = pd.Series(np.random.default_rng(0).integers(0, 3, 5000))
    b = pd.Series(np.random.default_rng(1).integers(0, 3, 5000))
    assert cramers_v(a, a) > .95 and cramers_v(a, b) < .05


def test_count_fit_recovers_poisson():
    x = np.random.default_rng(0).poisson(2.0, 20000)
    f = count_distribution_fit(x, "synthetic")
    assert abs(f["poisson_lambda"] - 2.0) < .05 and .9 < f["dispersion_index_var_over_mean"] < 1.1


def test_count_fit_detects_overdispersion():
    x = np.random.default_rng(0).negative_binomial(1, .3, 20000)
    f = count_distribution_fit(x, "synthetic")
    assert f["nb_AIC"] < f["poisson_AIC"] and f["dispersion_index_var_over_mean"] > 2


def test_continuous_fit_prefers_true_family():
    x = np.random.default_rng(0).lognormal(5, .8, 20000)
    t = continuous_fits(x, ["normal", "lognormal", "gamma"])
    assert t.loc[0, "distribution"] == "lognormal"


def test_rate_table_ci_contains_rate(cdf):
    t = rate_table(cdf, "poutcome")
    assert ((t["ci_low"] <= t["rate"]) & (t["rate"] <= t["ci_high"])).all() and t["n"].sum() == len(cdf)


# ------------------------------------------------------------------ metrics
def test_metrics_perfect_and_known_confusion():
    y = np.array([0, 0, 1, 1])
    m = compute_metrics(y, np.array([.1, .2, .8, .9]), .5)
    assert m["f1"] == 1 and m["roc_auc"] == 1 and (m["tn"], m["fp"], m["fn"], m["tp"]) == (2, 0, 0, 2)
    m = compute_metrics(y, np.array([.6, .2, .8, .4]), .5)
    assert (m["tn"], m["fp"], m["fn"], m["tp"]) == (1, 1, 1, 1) and m["accuracy"] == .5


def test_threshold_in_range():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 500); p = np.clip(y * .3 + rng.random(500) * .7, 0, 1)
    assert 0 <= best_f1_threshold(y, p) <= 1


# ------------------------------------------------------------------ model
def test_model_dimensions_and_probability_output():
    pytest.importorskip("tensorflow")
    from src.model import build_mlp
    m = build_mlp(51, (16, 8), .2, 1e-4, 1e-3)
    assert m.input_shape == (None, 51) and m.output_shape == (None, 1)
    p = m.predict(np.random.default_rng(0).normal(size=(10, 51)).astype("float32"), verbose=0)
    assert ((p >= 0) & (p <= 1)).all()


def test_tiny_training_run_executes(cdf):
    """Smoke test ONLY (a few epochs on a subset) - not a substitute for the full experiment."""
    pytest.importorskip("tensorflow")
    from src.train import train_mlp
    tr, va, te = split_data(cdf.sample(6000, random_state=0), "stratified")
    Xtr, Xva, Xte, ytr, yva, yte, *_ = prepare_matrices(tr, va, te)
    cfg = {"units": (8,), "dropout": .1, "lr": 1e-3, "class_weight": None}
    m, h = train_mlp(cfg, Xtr, ytr, Xva, yva, seed=0, max_epochs=2)
    assert len(h["loss"]) >= 1 and np.isfinite(h["loss"]).all()


# ------------------------------------------------------------------ saved results (full run)
RES = config.RES_DIR / "model_results.json"


@pytest.mark.skipif(not RES.exists(), reason="full experiment not run yet")
def test_saved_metrics_match_recomputation():
    R = json.loads(RES.read_text())
    z = np.load(config.RES_DIR / "predictions_primary.npz")
    thr = R["primary"]["val"]["threshold"]
    m = compute_metrics(z["y_test"], z["p_test"], thr)
    for k in ("roc_auc", "pr_auc", "f1", "accuracy"):
        assert m[k] == pytest.approx(R["primary"]["test"][k], abs=1e-9)
    assert R["split_sizes"][2] == len(z["y_test"])
    assert not R["quick_smoke_test"], "results file must come from the full run, not the smoke test"


@pytest.mark.skipif(not RES.exists(), reason="full experiment not run yet")
def test_test_set_threshold_chosen_on_validation_only():
    R = json.loads(RES.read_text())
    z = np.load(config.RES_DIR / "predictions_primary.npz")
    assert best_f1_threshold(z["y_val"], z["p_val"]) == pytest.approx(R["primary"]["val"]["threshold"])


# ------------------------------------------------------------------ figures
def test_a_figure_is_generated(cdf, tmp_path, monkeypatch):
    from src import visualizations as v
    monkeypatch.setattr(v, "FIG_DIR", tmp_path)
    p = v.fig01_class_balance(cdf)
    assert p.exists() and p.stat().st_size > 5000
