"""
stats_evidence.py
─────────────────
Statistical regime-comparison utilities.

Keeps statistical claims out of the app UI and makes them testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class RegimeComparison:
    """Result of a two-sample regime comparison."""
    valid:       bool
    significant: bool
    median_a:    float | None = None
    median_b:    float | None = None
    p_value:     float | None = None
    n_a:         int   = 0
    n_b:         int   = 0
    label_a:     str   = "before"
    label_b:     str   = "after"
    _reason:     str   = field(default="", repr=False)

    def sentence(self) -> str:
        """Return a plain-language sentence safe to show in a UI (never 'nan')."""
        if not self.valid:
            return self._reason

        direction = "higher" if self.median_b > self.median_a else "lower"
        sig_word  = "significantly" if self.significant else "slightly"

        return (
            f"Median {self.label_b} ({self.median_b:.4f}) is {sig_word} {direction} "
            f"than median {self.label_a} ({self.median_a:.4f}) "
            f"(p = {self.p_value:.4f}, n={self.n_a}/{self.n_b})."
        )


def compare_periods(
    df: pd.DataFrame,
    metric: str,
    split_date: str | pd.Timestamp,
    label_a: str = "before",
    label_b: str = "after",
    min_n: int = 10,
    alpha: float = 0.05,
) -> RegimeComparison:
    """
    Split *df[metric]* at *split_date* and run a Mann-Whitney U test.

    Returns a RegimeComparison. If either window has fewer than *min_n*
    non-null observations, returns a valid=False result whose .sentence()
    says there are not enough reports, never 'nan'.
    """
    split = pd.Timestamp(split_date)
    a = df.loc[df["Date"] <  split, metric].dropna()
    b = df.loc[df["Date"] >= split, metric].dropna()

    if len(a) < min_n or len(b) < min_n:
        return RegimeComparison(
            valid=False,
            significant=False,
            n_a=len(a),
            n_b=len(b),
            label_a=label_a,
            label_b=label_b,
            _reason=(
                f"not enough reports to compare: "
                f"{len(a)} {label_a}, {len(b)} {label_b} "
                f"(need at least {min_n} each)."
            ),
        )

    stat, p = stats.mannwhitneyu(a, b, alternative="two-sided")

    return RegimeComparison(
        valid=True,
        significant=bool(p < alpha),
        median_a=float(np.median(a)),
        median_b=float(np.median(b)),
        p_value=float(p),
        n_a=len(a),
        n_b=len(b),
        label_a=label_a,
        label_b=label_b,
    )


def weekday_vs_weekend(
    df: pd.DataFrame,
    metric: str,
    alpha: float = 0.05,
) -> RegimeComparison:
    """Compare metric on weekdays (Mon–Fri) vs weekends (Sat–Sun)."""
    is_weekend = df["Date"].dt.dayofweek >= 5
    a = df.loc[~is_weekend, metric].dropna()   # weekday
    b = df.loc[ is_weekend, metric].dropna()   # weekend

    if len(a) < 5 or len(b) < 5:
        return RegimeComparison(
            valid=False, significant=False,
            n_a=len(a), n_b=len(b),
            label_a="weekday", label_b="weekend",
            _reason="not enough reports to compare weekday vs weekend.",
        )

    stat, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    return RegimeComparison(
        valid=True,
        significant=bool(p < alpha),
        median_a=float(np.median(a)),
        median_b=float(np.median(b)),
        p_value=float(p),
        n_a=len(a),
        n_b=len(b),
        label_a="weekday",
        label_b="weekend",
    )
