"""Step 4: model building - baselines, hyper-parameter search, final multi-seed training,
robustness experiments and permutation importance. Everything is saved to outputs/.

Usage:
    python -m src.train            # full experiment (~15-25 min on a single CPU core)
    python -m src.train --quick    # smoke test only (2 configs, 3 epochs) -> outputs/smoke/
"""
import argparse
import itertools
import json
import platform
import random
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from .config import MODEL_DIR, OUT, RES_DIR, SEED, TAB_DIR
from .data_loader import get_data
from .evaluate import best_f1_threshold, compute_metrics, permutation_importance
from .model import build_mlp, set_reproducible
from .preprocessing import clean, model_columns, prepare_matrices, split_data

import tensorflow as tf  # noqa: E402  (after .model so env flags are set first)
from tensorflow import keras  # noqa: E402

GRID = {"units": [(32,), (64, 32), (128, 64, 32)], "dropout": [0.2, 0.4], "lr": [1e-3, 3e-4],
        "class_weight": [None, "balanced"]}
BATCH, MAX_EPOCHS, PATIENCE = 256, 40, 6


def _cw(y, mode):
    if mode != "balanced":
        return None
    n, n1 = len(y), int(y.sum())
    return {0: n / (2 * (n - n1)), 1: n / (2 * n1)}


def train_mlp(cfg, Xtr, ytr, Xva, yva, seed, max_epochs=MAX_EPOCHS):
    """Train one MLP with early stopping on validation ROC-AUC; returns (model, history dict)."""
    set_reproducible(seed)
    m = build_mlp(Xtr.shape[1], cfg["units"], cfg["dropout"], 1e-4, cfg["lr"])
    es = keras.callbacks.EarlyStopping(monitor="val_auc", mode="max", patience=PATIENCE, restore_best_weights=True)
    h = m.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=max_epochs, batch_size=BATCH, verbose=0, shuffle=True,
              callbacks=[es], class_weight=_cw(ytr, cfg["class_weight"]))
    return m, {k: [float(v) for v in vs] for k, vs in h.history.items()}


def predict(m, X):
    return m.predict(X, batch_size=2048, verbose=0).ravel()


def _eval_scores(pva, pte, yva, yte):
    thr = best_f1_threshold(yva, pva)
    return {"val": compute_metrics(yva, pva, thr), "test": compute_metrics(yte, pte, thr)}


def run_baselines(Xtr, ytr, Xva, yva, Xte, yte):
    out = {}
    base = np.full(len(yva), ytr.mean()); out["Majority class"] = _eval_scores(base, np.full(len(yte), ytr.mean()), yva, yte)
    lr = LogisticRegression(max_iter=2000).fit(Xtr, ytr)
    out["Logistic regression"] = _eval_scores(lr.predict_proba(Xva)[:, 1], lr.predict_proba(Xte)[:, 1], yva, yte)
    hgb = HistGradientBoostingClassifier(random_state=SEED).fit(Xtr, ytr)
    out["Gradient boosting (reference)"] = _eval_scores(hgb.predict_proba(Xva)[:, 1], hgb.predict_proba(Xte)[:, 1], yva, yte)
    return out


def _cached(path, fn):
    """Resumable runs: reuse a completed step's JSON result if it exists, otherwise compute and save."""
    if path.exists():
        return json.loads(path.read_text())
    val = fn()
    path.write_text(json.dumps(val, default=float))
    return val


def run_experiments(quick: bool = False):
    t0 = time.time()
    out_dir = OUT / "smoke" if quick else OUT
    (out_dir / "models").mkdir(parents=True, exist_ok=True)
    (out_dir / "results").mkdir(parents=True, exist_ok=True)
    mdl_dir, res_dir = out_dir / "models", out_dir / "results"
    cache = res_dir / "_cache"; cache.mkdir(exist_ok=True)

    raw = get_data(); cdf = clean(raw)
    tr, va, te = split_data(cdf, "stratified")
    Xtr, Xva, Xte, ytr, yva, yte, pre, names = prepare_matrices(tr, va, te, include_duration=False)
    assert Xtr.shape[1] == len(names)
    print(f"Matrices: train {Xtr.shape}, val {Xva.shape}, test {Xte.shape}; {len(names)} model inputs", flush=True)

    # ---------------- hyper-parameter search (validation only; test set untouched) ----------------
    combos = [dict(zip(GRID, v)) for v in itertools.product(*GRID.values())]
    n_cfg = 2 if quick else 12
    cfgs = random.Random(SEED).sample(combos, n_cfg)
    max_ep = 3 if quick else MAX_EPOCHS
    rows = []
    for i, cfg in enumerate(cfgs):
        def _one(cfg=cfg, i=i):
            ts = time.time()
            m, h = train_mlp(cfg, Xtr, ytr, Xva, yva, SEED, max_ep)
            mv = compute_metrics(yva, predict(m, Xva), 0.5)
            return {"config_id": i, "units": str(cfg["units"]), "dropout": cfg["dropout"], "lr": cfg["lr"],
                    "class_weight": cfg["class_weight"] or "none", "epochs_run": len(h["loss"]),
                    "best_epoch": int(np.argmax(h["val_auc"])) + 1, "val_roc_auc": mv["roc_auc"],
                    "val_pr_auc": mv["pr_auc"], "seconds": round(time.time() - ts, 1)}
        rows.append(_cached(cache / f"search_{i}.json", _one))
        print(f"[search {i + 1}/{n_cfg}] {cfg} -> val ROC-AUC {rows[-1]['val_roc_auc']:.4f}  PR-AUC {rows[-1]['val_pr_auc']:.4f}", flush=True)
    search = pd.DataFrame(rows).sort_values("val_pr_auc", ascending=False).reset_index(drop=True)
    best_id = int(search.loc[0, "config_id"]); best_cfg = cfgs[best_id]
    search.to_csv(res_dir / "hparam_search.csv", index=False)
    print("Selected:", best_cfg, flush=True)

    # ---------------- final model: 5 seeds, same config ----------------
    seeds = [SEED] if quick else [42, 43, 44, 45, 46]
    finals = []
    for sd in seeds:
        def _fin(sd=sd):
            m, h = train_mlp(best_cfg, Xtr, ytr, Xva, yva, sd, max_ep)
            pva, pte = predict(m, Xva), predict(m, Xte)
            sc = _eval_scores(pva, pte, yva, yte); sc.update(seed=sd, epochs_run=len(h["loss"]), best_epoch=int(np.argmax(h["val_auc"])) + 1)
            if sd == SEED:  # keep the primary model's artefacts
                m.save(mdl_dir / "mlp_primary.keras")
                (res_dir / "history_primary.json").write_text(json.dumps(h))
                np.savez(res_dir / "predictions_primary.npz", p_val=pva, p_test=pte, y_val=yva, y_test=yte)
            return sc
        sc = _cached(cache / f"final_{sd}.json", _fin); finals.append(sc)
        print(f"[final seed {sd}] test ROC-AUC {sc['test']['roc_auc']:.4f} PR-AUC {sc['test']['pr_auc']:.4f} F1 {sc['test']['f1']:.4f}", flush=True)
    m = keras.models.load_model(mdl_dir / "mlp_primary.keras"); joblib.dump(pre, mdl_dir / "preprocessor.joblib")
    n_params = int(m.count_params())
    arch = []
    m.summary(print_fn=lambda s: arch.append(s))

    # ---------------- baselines (same pre-processed data) ----------------
    baselines = _cached(cache / "baselines.json", lambda: run_baselines(Xtr, ytr, Xva, yva, Xte, yte))
    np_lr = LogisticRegression(max_iter=2000).fit(Xtr, ytr)
    np.save(res_dir / "p_test_logreg.npy", np_lr.predict_proba(Xte)[:, 1])

    # ---------------- permutation importance (validation set; original input columns) ----------------
    cols = model_columns(False)
    fn = lambda d: m.predict(pre.transform(d[cols]).astype("float32"), batch_size=4096, verbose=0).ravel()  # noqa: E731
    imp, base_auc = permutation_importance(fn, va[cols], yva, cols, n_repeats=2 if quick else 5)
    imp.to_csv(res_dir / "permutation_importance.csv", index=False)

    # ---------------- robustness experiments ----------------
    rob = []
    def add(setting, model, s):
        rob.append({"setting": setting, "model": model, "test_roc_auc": s["test"]["roc_auc"], "test_pr_auc": s["test"]["pr_auc"],
                    "test_f1": s["test"]["f1"], "test_prevalence": s["test"]["prevalence"]})
    arr = lambda key: float(np.mean([f["test"][key] for f in finals]))  # noqa: E731
    rob.append({"setting": "Pre-call features\n(primary, stratified)", "model": "MLP", "test_roc_auc": arr("roc_auc"),
                "test_pr_auc": arr("pr_auc"), "test_f1": arr("f1"), "test_prevalence": float(yte.mean())})
    for k, lab in (("Logistic regression", "Logistic regression"), ("Gradient boosting (reference)", "Gradient boosting")):
        add("Pre-call features\n(primary, stratified)", lab, baselines[k])
    def _dur():
        Xtr2, Xva2, Xte2, ytr2, yva2, yte2, _, _n = prepare_matrices(tr, va, te, include_duration=True)
        m2, _h = train_mlp(best_cfg, Xtr2, ytr2, Xva2, yva2, SEED, max_ep)
        return {"mlp": _eval_scores(predict(m2, Xva2), predict(m2, Xte2), yva2, yte2),
                "base": run_baselines(Xtr2, ytr2, Xva2, yva2, Xte2, yte2)}
    d2 = _cached(cache / "duration.json", _dur); b2 = d2["base"]
    add("+ call duration\n(not known pre-call)", "MLP", d2["mlp"])
    add("+ call duration\n(not known pre-call)", "Logistic regression", b2["Logistic regression"])
    add("+ call duration\n(not known pre-call)", "Gradient boosting", b2["Gradient boosting (reference)"])
    ctr, cva, cte = split_data(cdf, "chronological")
    def _chr():
        Xtr3, Xva3, Xte3, ytr3, yva3, yte3, _, _n = prepare_matrices(ctr, cva, cte, include_duration=False)
        m3, _h = train_mlp(best_cfg, Xtr3, ytr3, Xva3, yva3, SEED, max_ep)
        return {"mlp": _eval_scores(predict(m3, Xva3), predict(m3, Xte3), yva3, yte3),
                "base": run_baselines(Xtr3, ytr3, Xva3, yva3, Xte3, yte3),
                "prev": [float(ytr3.mean()), float(yva3.mean()), float(yte3.mean())]}
    c3 = _cached(cache / "chrono.json", _chr); s3, b3 = c3["mlp"], c3["base"]
    add("Pre-call features,\nchronological split", "MLP", s3)
    add("Pre-call features,\nchronological split", "Logistic regression", b3["Logistic regression"])
    add("Pre-call features,\nchronological split", "Gradient boosting", b3["Gradient boosting (reference)"])
    robustness = pd.DataFrame(rob); robustness.to_csv(res_dir / "robustness.csv", index=False)
    chrono = {"train_prev": c3["prev"][0], "val_prev": c3["prev"][1], "test_prev": c3["prev"][2],
              "mlp": s3, "logreg": b3["Logistic regression"], "hgb": b3["Gradient boosting (reference)"]}

    results = {
        "best_config": {**best_cfg, "units": list(best_cfg["units"])}, "n_params": n_params,
        "n_inputs": int(Xtr.shape[1]), "input_names": names, "split_sizes": [len(tr), len(va), len(te)],
        "split_prevalence": [float(ytr.mean()), float(yva.mean()), float(yte.mean())],
        "batch_size": BATCH, "max_epochs": max_ep, "early_stopping_patience": PATIENCE, "l2": 1e-4,
        "optimizer": "Adam", "loss": "binary cross-entropy", "n_search_configs": n_cfg,
        "primary": {"seed": SEED, **finals[[f["seed"] for f in finals].index(SEED)]},
        "seeds": [f["seed"] for f in finals],
        "test_mean_std": {k: [float(np.mean([f["test"][k] for f in finals])), float(np.std([f["test"][k] for f in finals]))]
                          for k in ("roc_auc", "pr_auc", "f1", "precision", "recall", "accuracy", "balanced_accuracy", "mcc", "brier")},
        "all_seed_runs": finals, "baselines": baselines, "baselines_with_duration": b2,
        "duration_ablation_mlp": rob[3], "chronological": chrono, "permutation_base_auc": base_auc,
        "architecture_summary": arch, "quick_smoke_test": quick,
        "environment": {"python": platform.python_version(), "tensorflow": tf.__version__, "platform": platform.platform(),
                        "cpu_count": __import__("os").cpu_count(), "gpu": [d.name for d in tf.config.list_physical_devices("GPU")]},
        "runtime_seconds": round(time.time() - t0, 1),
    }
    (res_dir / "model_results.json").write_text(json.dumps(results, indent=2, default=float))
    print(f"Done in {results['runtime_seconds']} s. Saved to {res_dir}", flush=True)
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="smoke test only (NOT a full training run)")
    run_experiments(ap.parse_args().quick)
