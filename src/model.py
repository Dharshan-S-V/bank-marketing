"""Deep-learning model: a regularised Multi-Layer Perceptron (MLP) for tabular binary classification.

Why an MLP? The data are tabular (numeric + one-hot categorical), so there is no spatial or
sequential structure for a CNN / RNN / Transformer to exploit. An MLP is the natural, defensible
deep-learning choice, and it is compared against classical baselines in `train.py`.
"""
import os

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")  # bit-for-bit reproducibility on CPU

import tensorflow as tf  # noqa: E402
from tensorflow import keras  # noqa: E402
from tensorflow.keras import layers, regularizers  # noqa: E402


def set_reproducible(seed: int) -> None:
    """Seed Python, NumPy and TensorFlow and request deterministic kernels."""
    keras.utils.set_random_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:  # noqa: BLE001 - older TF builds
        pass


def build_mlp(input_dim: int, units=(64, 32), dropout: float = 0.3, l2: float = 1e-4,
              lr: float = 1e-3) -> keras.Model:
    """Dense(ReLU) -> Dropout blocks followed by a single sigmoid unit (P(subscribe))."""
    inp = keras.Input(shape=(input_dim,), name="features")
    x = inp
    for i, u in enumerate(units):
        x = layers.Dense(u, activation="relu", kernel_regularizer=regularizers.l2(l2),
                         kernel_initializer="he_normal", name=f"dense_{i + 1}")(x)
        x = layers.Dropout(dropout, name=f"dropout_{i + 1}")(x)
    out = layers.Dense(1, activation="sigmoid", name="p_subscribe")(x)
    model = keras.Model(inp, out, name="bank_mlp")
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=lr),
                  loss=keras.losses.BinaryCrossentropy(),
                  metrics=["accuracy", keras.metrics.AUC(name="auc")])
    return model
