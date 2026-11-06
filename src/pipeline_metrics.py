"""
pipeline_metrics.py
───────────────────
Core process metrics for the UAC Care Transition pipeline.

All functions accept a tidy DataFrame whose column names are the short aliases
produced by load_data() in data_io.py:
    Date, Apprehended, CBPCustody, Transferred, HHSCare, Discharged
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ── short column aliases used internally ─────────────────────────────────────

COL_DATE        = "Date"
COL_APPREH      = "Apprehended"
COL_CBP         = "CBPCustody"
COL_TRANSFER    = "Transferred"
COL_HHS         = "HHSCare"
COL_DISCHARGE   = "Discharged"


# ── derived ratio metrics ─────────────────────────────────────────────────────

def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Return *df* with three ratio columns added (never mutate the original)."""
    out = df.copy()

    # guard against zero denominators
    cbp   = out[COL_CBP].replace(0, np.nan)
    hhs   = out[COL_HHS].replace(0, np.nan)
    total_entries = out[COL_APPREH] + out[COL_TRANSFER]
    total_exits   = out[COL_TRANSFER] + out[COL_DISCHARGE]

    out["TransferEfficiency"]    = out[COL_TRANSFER]  / cbp
    out["DischargeEffectiveness"] = out[COL_DISCHARGE] / hhs
    out["PipelineThroughput"]    = total_exits / total_entries.replace(0, np.nan)

    return out


# ── stagnation detector ───────────────────────────────────────────────────────

def stagnation_periods(
    df: pd.DataFrame,
    metric: str = "DischargeEffectiveness",
    min_reports: int = 7,
    lookback: int = 60,
    fraction: float = 0.4,
) -> pd.DataFrame:
    """
    Find runs of consecutive reports where *metric* is below
    *fraction* × its rolling-lookback median.

    Returns a DataFrame with columns:
        Start, End, Reports, CalendarDays, MeanMetric

    'Reports' is the count of rows in the run; 'CalendarDays' is the
    inclusive calendar span (End − Start + 1 day).  There is deliberately
    no ambiguous 'Days' column.
    """
    s = df[metric].copy()
    rolling_med = s.rolling(lookback, min_periods=max(1, lookback // 4)).median()
    threshold   = rolling_med * fraction
    below       = s < threshold

    records = []
    in_run  = False
    start_i = None

    for i, flag in enumerate(below):
        if flag and not in_run:
            in_run  = True
            start_i = i
        elif not flag and in_run:
            end_i = i - 1
            _add_run(df, records, metric, start_i, end_i, min_reports)
            in_run = False

    if in_run:
        _add_run(df, records, metric, start_i, len(df) - 1, min_reports)

    if not records:
        return pd.DataFrame(columns=["Start", "End", "Reports", "CalendarDays", "MeanMetric"])

    return pd.DataFrame(records).reset_index(drop=True)


def _add_run(df, records, metric, start_i, end_i, min_reports):
    n_reports = end_i - start_i + 1
    if n_reports < min_reports:
        return
    start_date = df[COL_DATE].iat[start_i]
    end_date   = df[COL_DATE].iat[end_i]
    calendar_days = (end_date - start_date).days + 1
    mean_val   = df[metric].iloc[start_i : end_i + 1].mean()
    records.append(
        dict(
            Start=start_date,
            End=end_date,
            Reports=n_reports,
            CalendarDays=calendar_days,
            MeanMetric=round(mean_val, 4),
        )
    )


# ── sudden discharge drop detector ───────────────────────────────────────────

def sudden_drops(
    df: pd.DataFrame,
    col: str = COL_DISCHARGE,
    window: int = 30,
    threshold: float = 0.5,
    min_duration: int = 10,
) -> pd.DataFrame:
    """
    Detect periods where *col* falls to below *threshold* of its prior
    rolling mean and stays there for at least *min_duration* consecutive reports.

    Returns columns: Start, End, Reports, CalendarDays, DropFraction
    """
    s = df[col].copy()
    rolling_mean = s.rolling(window, min_periods=max(1, window // 3)).mean().shift(1)
    low = s < threshold * rolling_mean

    records = []
    in_drop = False
    start_i = None

    for i, flag in enumerate(low):
        if flag and not in_drop:
            in_drop = True
            start_i = i
        elif not flag and in_drop:
            end_i = i - 1
            _add_drop(df, records, col, start_i, end_i, min_duration, rolling_mean)
            in_drop = False

    if in_drop:
        _add_drop(df, records, col, start_i, len(df) - 1, min_duration, rolling_mean)

    if not records:
        return pd.DataFrame(columns=["Start", "End", "Reports", "CalendarDays", "DropFraction"])

    return pd.DataFrame(records).reset_index(drop=True)


def _add_drop(df, records, col, start_i, end_i, min_duration, rolling_mean):
    n = end_i - start_i + 1
    if n < min_duration:
        return
    start_date = df[COL_DATE].iat[start_i]
    end_date   = df[COL_DATE].iat[end_i]
    actual     = df[col].iloc[start_i : end_i + 1].mean()
    baseline   = rolling_mean.iloc[start_i : end_i + 1].mean()
    fraction   = actual / baseline if (baseline and not np.isnan(baseline)) else np.nan
    records.append(
        dict(
            Start=start_date,
            End=end_date,
            Reports=n,
            CalendarDays=(end_date - start_date).days + 1,
            DropFraction=round(fraction, 3) if not np.isnan(fraction) else None,
        )
    )


# ── conservation check (mass balance) ────────────────────────────────────────

def conservation_check(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each *consecutive* day pair, check the CBP stock balance:
        CBP[t] ≈ CBP[t-1] + Apprehended[t] − Transferred[t]

    Residual is set to NaN whenever the gap between two dates exceeds one day.
    Returns the input DataFrame with a 'ConservationResidual' column added.
    """
    out = df.copy().reset_index(drop=True)
    residuals = [np.nan]  # first row has no predecessor

    for i in range(1, len(out)):
        gap = (out[COL_DATE].iat[i] - out[COL_DATE].iat[i - 1]).days
        if gap != 1:
            residuals.append(np.nan)
        else:
            expected = (
                out[COL_CBP].iat[i - 1]
                + out[COL_APPREH].iat[i]
                - out[COL_TRANSFER].iat[i]
            )
            residuals.append(out[COL_CBP].iat[i] - expected)

    out["ConservationResidual"] = residuals
    return out


# ── backlog accumulation ──────────────────────────────────────────────────────

def backlog_rate(df: pd.DataFrame, window: int = 7) -> pd.Series:
    """
    Rolling *window*-day net accumulation in HHS care:
        rolling_mean(HHSCare) change per day.

    Positive = growing backlog; negative = clearing.
    """
    return df[COL_HHS].rolling(window, min_periods=1).mean().diff()
