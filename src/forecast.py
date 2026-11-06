"""
forecast.py
───────────
Simple forward-looking capacity and throughput projections.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import TypedDict


class CapacityGap(TypedDict):
    current_hhs_population:    float
    target_clearance_days:     int
    required_daily_discharge:  float
    current_daily_discharge:   float
    gap:                       float
    percent_increase_needed:   float


def capacity_gap(df: pd.DataFrame, target_clearance_days: int = 30) -> CapacityGap:
    """
    Given the current HHS population and recent discharge rate, compute
    how many additional daily discharges are required to clear the backlog
    within *target_clearance_days*.

    Parameters
    ----------
    df : DataFrame with 'HHSCare' and 'Discharged' columns (short aliases).
    target_clearance_days : desired days to drain current HHS population to zero.

    Returns
    -------
    CapacityGap TypedDict.
    """
    current_pop = float(df["HHSCare"].iloc[-1])
    # Use the last 30 available rows as a stable baseline
    tail = df["Discharged"].dropna().tail(30)
    current_rate = float(tail.mean()) if len(tail) > 0 else 0.0

    required = current_pop / target_clearance_days if target_clearance_days > 0 else np.inf
    gap      = required - current_rate
    pct_inc  = (gap / current_rate * 100) if current_rate > 0 else np.inf

    return CapacityGap(
        current_hhs_population=current_pop,
        target_clearance_days=target_clearance_days,
        required_daily_discharge=round(required, 2),
        current_daily_discharge=round(current_rate, 2),
        gap=round(gap, 2),
        percent_increase_needed=round(pct_inc, 2),
    )


def linear_forecast(
    df: pd.DataFrame,
    col: str,
    horizon_days: int = 90,
) -> pd.DataFrame:
    """
    Fit a simple OLS trend on *col* and project *horizon_days* forward.

    Returns a DataFrame with columns: Date, Forecast, Lower95, Upper95.
    """
    sub = df[["Date", col]].dropna().copy()
    sub = sub.sort_values("Date").reset_index(drop=True)

    x = np.arange(len(sub), dtype=float)
    y = sub[col].values.astype(float)

    # OLS
    xm, ym = x.mean(), y.mean()
    b1 = np.dot(x - xm, y - ym) / np.dot(x - xm, x - xm)
    b0 = ym - b1 * xm

    # residual std for prediction interval
    y_hat  = b0 + b1 * x
    resid  = y - y_hat
    se     = resid.std(ddof=2)
    t_crit = 1.96   # normal approximation

    last_date = sub["Date"].iloc[-1]
    future_x  = np.arange(len(sub), len(sub) + horizon_days, dtype=float)
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon_days)

    forecast_vals = b0 + b1 * future_x
    lower = forecast_vals - t_crit * se
    upper = forecast_vals + t_crit * se

    return pd.DataFrame(
        {
            "Date":     future_dates,
            "Forecast": np.round(forecast_vals, 1),
            "Lower95":  np.round(lower, 1),
            "Upper95":  np.round(upper, 1),
        }
    )
