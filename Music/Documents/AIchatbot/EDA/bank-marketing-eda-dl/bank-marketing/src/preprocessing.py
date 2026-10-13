"""Stage 3 (Filter): cleaning, feature construction, leakage-safe preprocessing and splitting."""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from .config import CATEGORICAL, MODEL_BINARY, SEED, TARGET


# ---------------------------------------------------------------------------------------
# Deterministic cleaning (no statistics are learned here, so it cannot leak across splits)
# ---------------------------------------------------------------------------------------
def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise text, encode the target and make the pdays sentinel explicit.

    * 'unknown' categories are KEPT as their own level: they are informative (e.g. contact =
      'unknown' is strongly associated with the outcome) and are not random missingness.
    * pdays == -1 is a sentinel meaning "never contacted before", not a real duration, so it is
      split into a binary flag + a cleaned numeric column (0 where not contacted).
    """
    out = df.copy()
    for c in CATEGORICAL + [TARGET]:
        out[c] = out[c].astype(str).str.strip().str.lower()
    out["y_bin"] = (out[TARGET] == "yes").astype(int)
    out["previously_contacted"] = (out["pdays"] != -1).astype(int)
    out["pdays_clean"] = out["pdays"].where(out["pdays"] != -1, 0)
    return out


# ---------------------------------------------------------------------------------------
# Learned transformers (fit on TRAIN ONLY)
# ---------------------------------------------------------------------------------------
def signed_log1p(x):
    """Symmetric log transform: keeps negative balances (valid overdrafts) usable."""
    x = np.asarray(x, dtype=float)
    return np.sign(x) * np.log1p(np.abs(x))


class Winsorizer(BaseEstimator, TransformerMixin):
    """Cap values at an upper quantile learned from the training data."""

    def __init__(self, upper_q: float = 0.99):
        self.upper_q = upper_q

    def fit(self, X, y=None):
        self.upper_ = np.quantile(np.asarray(X, dtype=float), self.upper_q, axis=0)
        self.n_features_in_ = np.asarray(X).shape[1]
        return self

    def transform(self, X):
        return np.minimum(np.asarray(X, dtype=float), self.upper_)

    def get_feature_names_out(self, input_features=None):
        return np.asarray(input_features)


def build_preprocessor(extra_log_capped=None) -> ColumnTransformer:
    """ColumnTransformer used by the neural network and the baselines.

    age, day            -> StandardScaler
    balance             -> signed log1p -> StandardScaler   (heavy tails, negatives allowed)
    campaign, previous  -> cap at train 99th pct -> log1p -> StandardScaler   (count outliers)
    pdays_clean         -> log1p -> StandardScaler
    categorical         -> OneHotEncoder(handle_unknown='ignore')
    binary flag         -> passthrough
    """
    log_capped = ["campaign", "previous"] + list(extra_log_capped or [])
    capped = Pipeline([("cap", Winsorizer(0.99)),
                       ("log", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
                       ("sc", StandardScaler())])
    slog = Pipeline([("log", FunctionTransformer(signed_log1p, feature_names_out="one-to-one")),
                     ("sc", StandardScaler())])
    plog = Pipeline([("log", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
                     ("sc", StandardScaler())])
    return ColumnTransformer([
        ("plain", StandardScaler(), ["age", "day"]),
        ("slog", slog, ["balance"]),
        ("capped", capped, log_capped),
        ("pdays", plog, ["pdays_clean"]),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
        ("bin", "passthrough", MODEL_BINARY),
    ], verbose_feature_names_out=False)


def model_columns(include_duration: bool = False):
    cols = ["age", "balance", "day", "campaign", "pdays_clean", "previous"]
    cols += CATEGORICAL + MODEL_BINARY
    if include_duration:
        cols = cols + ["duration"]
    return cols


# ---------------------------------------------------------------------------------------
# Splitting
# ---------------------------------------------------------------------------------------
def split_data(df: pd.DataFrame, kind: str = "stratified", seed: int = SEED,
               val_frac: float = 0.15, test_frac: float = 0.15):
    """Return (train, val, test) DataFrames.

    kind='stratified'    : random 70/15/15 split stratified on the target (primary protocol).
    kind='chronological' : the UCI file is ordered by date (May 2008 - Nov 2010); first 70 % ->
                           train, next 15 % -> validation, last 15 % -> test (robustness check).
    """
    if kind == "stratified":
        trainval, test = train_test_split(df, test_size=test_frac, stratify=df["y_bin"],
                                          random_state=seed)
        rel_val = val_frac / (1 - test_frac)
        train, val = train_test_split(trainval, test_size=rel_val, stratify=trainval["y_bin"],
                                      random_state=seed)
    elif kind == "chronological":
        n = len(df)
        i_val, i_test = int(n * (1 - val_frac - test_frac)), int(n * (1 - test_frac))
        train, val, test = df.iloc[:i_val], df.iloc[i_val:i_test], df.iloc[i_test:]
    else:
        raise ValueError(kind)
    return train.copy(), val.copy(), test.copy()


def prepare_matrices(train, val, test, include_duration: bool = False):
    """Fit the preprocessor on TRAIN only, then transform train / val / test."""
    cols = model_columns(include_duration)
    pre = build_preprocessor(extra_log_capped=["duration"] if include_duration else None)
    Xtr = pre.fit_transform(train[cols])
    Xva, Xte = pre.transform(val[cols]), pre.transform(test[cols])
    names = list(pre.get_feature_names_out())
    return (Xtr.astype("float32"), Xva.astype("float32"), Xte.astype("float32"),
            train["y_bin"].values, val["y_bin"].values, test["y_bin"].values, pre, names)
