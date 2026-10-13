"""Stage 1 (Acquire): download, verify and load the Bank Marketing dataset."""
import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from .config import (CATEGORICAL, EXPECTED_SHAPE, MIRROR_CSV, NUMERIC, RAW_CSV, TARGET,
                     UCI_ZIP)


def _fetch(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (EDA assignment)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _csv_from_uci_zip(blob: bytes) -> bytes:
    """UCI wraps the data in nested zips; search recursively for bank-full.csv."""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for name in z.namelist():
            if name.endswith("bank-full.csv"):
                return z.read(name)
        for name in z.namelist():
            if name.endswith(".zip"):
                try:
                    return _csv_from_uci_zip(z.read(name))
                except FileNotFoundError:
                    continue
    raise FileNotFoundError("bank-full.csv not found inside archive")


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def download_dataset(force: bool = False, dest: Path = RAW_CSV, verbose: bool = True) -> Path:
    """Download bank-full.csv to `dest`. Tries the official UCI archive first, then a mirror.

    Returns the local path. Raises RuntimeError with manual instructions if both sources fail.
    """
    dest = Path(dest)
    if dest.exists() and not force:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    errors = []
    sources = (("UCI archive", lambda: _csv_from_uci_zip(_fetch(UCI_ZIP))),
               ("GitHub mirror", lambda: _fetch(MIRROR_CSV)))
    for label, fn in sources:
        try:
            dest.write_bytes(fn())
            validate(load_raw(dest))  # fail early if the file is not what we expect
            if verbose:
                print(f"Downloaded dataset from {label}: {dest}")
            return dest
        except Exception as e:  # noqa: BLE001 - try the fallback on any failure
            errors.append(f"{label}: {e!r}")
            dest.unlink(missing_ok=True)
    raise RuntimeError(
        "Could not download the dataset automatically.\n" + "\n".join(errors) +
        "\nManual fallback: download 'bank-full.csv' from "
        "https://archive.ics.uci.edu/dataset/222/bank+marketing and place it at " + str(dest))


def load_raw(path: Path = RAW_CSV) -> pd.DataFrame:
    """Load the semicolon-separated CSV exactly as published (no cleaning)."""
    return pd.read_csv(path, sep=";")


def validate(df: pd.DataFrame) -> None:
    """Sanity checks that the file is the documented Bank Marketing dataset."""
    if df.shape != EXPECTED_SHAPE:
        raise ValueError(f"Unexpected shape {df.shape}, expected {EXPECTED_SHAPE}")
    expected = set(NUMERIC + CATEGORICAL + [TARGET])
    if set(df.columns) != expected:
        raise ValueError(f"Unexpected columns: {set(df.columns) ^ expected}")
    if set(df[TARGET].unique()) != {"yes", "no"}:
        raise ValueError("Target column must contain only 'yes'/'no'")


def get_data() -> pd.DataFrame:
    """Ensure the file exists, load and validate it."""
    df = load_raw(download_dataset())
    validate(df)
    return df


if __name__ == "__main__":
    p = download_dataset()
    d = load_raw(p)
    validate(d)
    print(d.shape, "sha256:", sha256(p))
