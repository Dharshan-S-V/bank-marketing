"""Model evaluation: metrics, threshold selection, permutation importance and result figures."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
                             brier_score_loss, confusion_matrix, f1_score, matthews_corrcoef,
                             precision_recall_curve, precision_score, recall_score, roc_auc_score,
                             roc_curve)

from .config import FIG_DIR
from .visualizations import C_ACC, C_GREY, C_NO, C_YES, _save


# ---------------------------------------------------------------------------- metrics
def best_f1_threshold(y_true, p) -> float:
    """Threshold maximising F1 on the VALIDATION set (never tuned on the test set)."""
    prec, rec, thr = precision_recall_curve(y_true, p)
    f1 = 2 * prec[:-1] * rec[:-1] / np.clip(prec[:-1] + rec[:-1], 1e-12, None)
    return float(thr[int(np.argmax(f1))])


def compute_metrics(y_true, p, thr: float) -> dict:
    yhat = (np.asarray(p) >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, yhat).ravel()
    return {"threshold": thr, "accuracy": accuracy_score(y_true, yhat),
            "balanced_accuracy": balanced_accuracy_score(y_true, yhat),
            "precision": precision_score(y_true, yhat, zero_division=0),
            "recall": recall_score(y_true, yhat), "f1": f1_score(y_true, yhat),
            "mcc": matthews_corrcoef(y_true, yhat), "roc_auc": roc_auc_score(y_true, p),
            "pr_auc": average_precision_score(y_true, p), "brier": brier_score_loss(y_true, p),
            "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
            "prevalence": float(np.mean(y_true))}


def permutation_importance(predict_fn, X_df: pd.DataFrame, y, columns, n_repeats=5, seed=42):
    """Drop in ROC-AUC when one ORIGINAL input column is shuffled (one-hot groups move together)."""
    rng = np.random.default_rng(seed)
    base = roc_auc_score(y, predict_fn(X_df))
    rows = []
    for c in columns:
        drops = []
        for _ in range(n_repeats):
            Xp = X_df.copy()
            Xp[c] = rng.permutation(Xp[c].values)
            drops.append(base - roc_auc_score(y, predict_fn(Xp)))
        rows.append({"feature": c, "auc_drop_mean": float(np.mean(drops)), "auc_drop_std": float(np.std(drops))})
    return pd.DataFrame(rows).sort_values("auc_drop_mean", ascending=False).reset_index(drop=True), base


# ---------------------------------------------------------------------------- figures
def fig15_hparam_search(search: pd.DataFrame, best_idx: int):
    s = search.sort_values("val_pr_auc").reset_index(drop=True)
    labels = [f"{r.units} | do={r.dropout} | lr={r.lr} | cw={r.class_weight}" for r in s.itertuples()]
    fig, ax = plt.subplots(figsize=(10, 0.42 * len(s) + 1.6))
    colors = [C_ACC if r.config_id == best_idx else C_NO for r in s.itertuples()]
    ax.barh(range(len(s)), s["val_pr_auc"], color=colors)
    for i, (a, b) in enumerate(zip(s["val_pr_auc"], s["val_roc_auc"])):
        ax.text(a + .002, i, f"PR-AUC {a:.3f} | ROC-AUC {b:.3f}", va="center", fontsize=8)
    ax.set_yticks(range(len(s))); ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(s["val_pr_auc"].min() * .9, s["val_pr_auc"].max() * 1.12)
    ax.set_xlabel("Validation PR-AUC (selection criterion)")
    ax.set_title("Fig. 15  Hyper-parameter search (validation set only; green = selected)")
    ax.grid(axis="y", visible=False)
    return _save(fig, "fig15_hparam_search")


def fig16_loss_curves(hist):
    ep = np.arange(1, len(hist["loss"]) + 1)
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(ep, hist["loss"], color=C_NO, lw=2, label="Training loss")
    ax.plot(ep, hist["val_loss"], color=C_YES, lw=2, label="Validation loss")
    b = int(np.argmin(hist["val_loss"])) + 1
    ax.axvline(b, color=C_GREY, ls=":", label=f"lowest val. loss (epoch {b})")
    ax.set_xlabel("Epoch"); ax.set_ylabel("Binary cross-entropy (+ L2 penalty)")
    ax.set_title("Fig. 16  Training vs. validation loss"); ax.legend()
    return _save(fig, "fig16_loss_curves")


def fig17_accuracy_curves(hist, majority_acc):
    ep = np.arange(1, len(hist["accuracy"]) + 1)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    axes[0].plot(ep, np.array(hist["accuracy"]) * 100, color=C_NO, lw=2, label="Training")
    axes[0].plot(ep, np.array(hist["val_accuracy"]) * 100, color=C_YES, lw=2, label="Validation")
    axes[0].axhline(majority_acc * 100, color="k", ls="--", lw=1.2, label=f"always-'no' baseline {majority_acc * 100:.1f}%")
    axes[0].set_xlabel("Epoch"); axes[0].set_ylabel("Accuracy at 0.5 threshold (%)"); axes[0].set_title("Accuracy"); axes[0].legend()
    axes[1].plot(ep, hist["auc"], color=C_NO, lw=2, label="Training")
    axes[1].plot(ep, hist["val_auc"], color=C_YES, lw=2, label="Validation")
    axes[1].set_xlabel("Epoch"); axes[1].set_ylabel("ROC-AUC"); axes[1].set_title("ROC-AUC (threshold-free)"); axes[1].legend()
    fig.suptitle("Fig. 17  Accuracy and AUC versus epoch (accuracy alone is misleading at 11.7% prevalence)", fontweight="bold", y=1.02)
    fig.tight_layout()
    return _save(fig, "fig17_accuracy_auc_curves")


def fig18_confusion(m):
    cm = np.array([[m["tn"], m["fp"]], [m["fn"], m["tp"]]])
    pct = cm / cm.sum(axis=1, keepdims=True) * 100
    fig, ax = plt.subplots(figsize=(5.8, 5))
    ax.imshow(pct, cmap="Blues", vmin=0, vmax=100)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{cm[i, j]:,}\n({pct[i, j]:.1f}% of row)", ha="center", va="center",
                    color="white" if pct[i, j] > 55 else "black", fontsize=11)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Predicted: no", "Predicted: yes"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["Actual: no", "Actual: yes"]); ax.grid(False)
    ax.set_title(f"Fig. 18  Confusion matrix on the TEST set\n(threshold {m['threshold']:.3f} chosen on validation)")
    return _save(fig, "fig18_confusion_matrix")


def fig19_roc_pr(y, curves: dict):
    """curves: name -> (probabilities, colour)."""
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5))
    for name, (p, col) in curves.items():
        fpr, tpr, _ = roc_curve(y, p)
        axes[0].plot(fpr, tpr, color=col, lw=2, label=f"{name} (AUC = {roc_auc_score(y, p):.3f})")
        pr, rc, _ = precision_recall_curve(y, p)
        axes[1].plot(rc, pr, color=col, lw=2, label=f"{name} (AP = {average_precision_score(y, p):.3f})")
    axes[0].plot([0, 1], [0, 1], "k--", lw=1, label="chance (AUC = 0.5)")
    axes[0].set_xlabel("False-positive rate"); axes[0].set_ylabel("True-positive rate (recall)"); axes[0].set_title("ROC curve"); axes[0].legend(loc="lower right")
    axes[1].axhline(np.mean(y), color="k", ls="--", lw=1, label=f"prevalence = {np.mean(y):.3f}")
    axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision"); axes[1].set_title("Precision-recall curve"); axes[1].legend(loc="upper right")
    axes[1].set_ylim(0, 1.02)
    fig.suptitle("Fig. 19  ROC and precision-recall curves on the TEST set", fontweight="bold", y=1.02)
    fig.tight_layout()
    return _save(fig, "fig19_roc_pr_curves")


def fig20_permutation_importance(imp: pd.DataFrame, base_auc: float):
    d = imp.sort_values("auc_drop_mean")
    fig, ax = plt.subplots(figsize=(8, 5.6))
    ax.barh(d["feature"], d["auc_drop_mean"], xerr=d["auc_drop_std"], color=C_ACC, ecolor="k", capsize=2)
    ax.set_xlabel(f"Drop in validation ROC-AUC when the feature is shuffled (baseline AUC = {base_auc:.3f})")
    ax.set_title("Fig. 20  Permutation feature importance of the MLP (5 repeats)")
    ax.grid(axis="y", visible=False)
    return _save(fig, "fig20_permutation_importance")


def fig21_threshold_tradeoff(y_val, p_val, thr):
    prec, rec, th = precision_recall_curve(y_val, p_val)
    f1 = 2 * prec[:-1] * rec[:-1] / np.clip(prec[:-1] + rec[:-1], 1e-12, None)
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(th, prec[:-1], color=C_NO, lw=2, label="Precision"); ax.plot(th, rec[:-1], color=C_YES, lw=2, label="Recall")
    ax.plot(th, f1, color=C_ACC, lw=2, label="F1")
    ax.axvline(thr, color="k", ls=":", label=f"chosen threshold {thr:.3f}")
    ax.set_xlabel("Decision threshold on P(subscribe)"); ax.set_ylabel("Score (validation set)")
    ax.set_title("Fig. 21  Precision / recall / F1 versus decision threshold"); ax.legend()
    return _save(fig, "fig21_threshold_tradeoff")


def fig22_robustness(rows: pd.DataFrame):
    """rows: columns setting, model, test_roc_auc, test_pr_auc."""
    settings = list(dict.fromkeys(rows["setting"]))
    models = list(dict.fromkeys(rows["model"]))
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    w = .8 / len(models)
    cols = [C_YES, C_NO, C_ACC, "#8172B3"]  # same colours as Fig. 19 (MLP orange, logistic blue)
    for ax, metric, lab in zip(axes, ["test_roc_auc", "test_pr_auc"], ["Test ROC-AUC", "Test PR-AUC"]):
        for i, m in enumerate(models):
            vals = [rows[(rows.setting == s) & (rows.model == m)][metric].mean() for s in settings]
            bars = ax.bar(np.arange(len(settings)) + i * w, vals, w, label=m, color=cols[i % 4])
            for b, v in zip(bars, vals):
                ax.text(b.get_x() + b.get_width() / 2, v + .005, f"{v:.3f}", ha="center", fontsize=8)
        ax.set_xticks(np.arange(len(settings)) + w * (len(models) - 1) / 2); ax.set_xticklabels(settings, fontsize=9)
        ax.set_ylabel(lab); ax.legend(fontsize=8.5, loc="upper left")
        ax.set_ylim(0, 1.08 if "roc" in metric else max(rows[metric].max() * 1.2, .5)); ax.grid(axis="x", visible=False)
    fig.suptitle("Fig. 22  Robustness: the MLP and baselines under different feature sets and split protocols",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    return _save(fig, "fig22_robustness")


# ---------------------------------------------------------------------------- driver
def make_model_figures(res_dir=None):
    """Regenerate every model-evaluation figure from the artifacts saved by `src.train`."""
    import json

    from .config import RES_DIR
    res_dir = res_dir or RES_DIR
    R = json.loads((res_dir / "model_results.json").read_text())
    search = pd.read_csv(res_dir / "hparam_search.csv")
    hist = json.loads((res_dir / "history_primary.json").read_text())
    z = np.load(res_dir / "predictions_primary.npz")
    imp = pd.read_csv(res_dir / "permutation_importance.csv")
    rob = pd.read_csv(res_dir / "robustness.csv")
    p_lr = np.load(res_dir / "p_test_logreg.npy")
    thr = R["primary"]["val"]["threshold"]
    m_test = compute_metrics(z["y_test"], z["p_test"], thr)
    figs = {15: fig15_hparam_search(search, int(search.loc[0, "config_id"])),
            16: fig16_loss_curves(hist), 17: fig17_accuracy_curves(hist, 1 - R["split_prevalence"][2]),
            18: fig18_confusion(m_test),
            19: fig19_roc_pr(z["y_test"], {"MLP (primary, seed 42)": (z["p_test"], C_YES), "Logistic regression": (p_lr, C_NO)}),
            20: fig20_permutation_importance(imp, R["permutation_base_auc"]),
            21: fig21_threshold_tradeoff(z["y_val"], z["p_val"], thr), 22: fig22_robustness(rob)}
    return figs, m_test
