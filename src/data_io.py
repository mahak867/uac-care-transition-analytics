"""
data_io.py
──────────
Loads and normalises the HHS UAC CSV into a tidy DataFrame with
short column aliases.  The cache is keyed on the file's bytes so
swapping the CSV always gives fresh data.
"""

from __future__ import annotations

import hashlib
import io
import pathlib

import pandas as pd

# ── canonical column aliases ───────────────────────────────────────────────────

RENAME = {
    "Date":                                           "Date",
    "Children apprehended and placed in CBP custody*": "Apprehended",
    "Children in CBP custody":                         "CBPCustody",
    "Children transferred out of CBP custody":         "Transferred",
    "Children in HHS Care":                            "HHSCare",
    "Children discharged from HHS Care":               "Discharged",
}

_CACHE: dict[str, pd.DataFrame] = {}


def _file_hash(raw: bytes) -> str:
    return hashlib.md5(raw, usedforsecurity=False).hexdigest()


def load_data(source: str | pathlib.Path | bytes | io.BytesIO) -> pd.DataFrame:
    """
    Load the UAC CSV from a file path, raw bytes, or a BytesIO object.
    Returns a cleaned, sorted DataFrame with short column aliases.
    The cache is keyed on the file content, so replacing the file always
    produces fresh data.
    """
    # Normalise to bytes for hashing
    if isinstance(source, (str, pathlib.Path)):
        raw = pathlib.Path(source).read_bytes()
    elif isinstance(source, io.BytesIO):
        raw = source.getvalue()
    else:
        raw = bytes(source)

    key = _file_hash(raw)
    if key in _CACHE:
        return _CACHE[key]

    df = pd.read_csv(io.BytesIO(raw))

    # strip whitespace from column names
    df.columns = [c.strip() for c in df.columns]

    # rename to short aliases; drop any columns not in the map
    keep = {k: v for k, v in RENAME.items() if k in df.columns}
    df = df[list(keep.keys())].rename(columns=keep)

    # parse date
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    # parse numeric columns (may contain commas e.g. "2,484")
    for col in ["Apprehended", "CBPCustody", "Transferred", "HHSCare", "Discharged"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.strip()
                .pipe(pd.to_numeric, errors="coerce")
            )

    df = df.sort_values("Date").reset_index(drop=True)

    _CACHE[key] = df
    return df
