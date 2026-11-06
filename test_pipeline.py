"""
Known-answer tests for the pipeline metrics, on small hand-built daily series.

Run:  pip install -r requirements-dev.txt && pytest
"""

import numpy as np
import pandas as pd
import pytest

from src import forecast as fc
from src import pipeline_metrics as pm
from src import stats_evidence as se


def series(dates, **cols):
    df = pd.DataFrame({"Date": pd.to_datetime(dates), **cols})
    return df


# ── reports are not days ─────────────────────────────────────────────────────

def test_stagnation_reports_the_calendar_span_as_well_as_the_report_count():
    # 60 baseline reports with healthy discharge effectiveness, then 8 reports that
    # collapse, filed on every other calendar day, so 8 reports span 15 calendar days.
    base_dates = pd.date_range("2024-01-01", periods=60, freq="D")
    stall_dates = pd.date_range("2024-03-05", periods=8, freq="2D")
    dates = list(base_dates) + list(stall_dates)
    eff = [0.03] * 60 + [0.001] * 8
    df = series(dates, DischargeEffectiveness=eff)
    runs = pm.stagnation_periods(df, min_reports=5, lookback=30, fraction=0.5)
    assert len(runs) == 1
    assert runs.loc[0, "Reports"] == 8
    assert runs.loc[0, "CalendarDays"] == 15
    assert "Days" not in runs.columns, "the ambiguous 'Days' column must not come back"


def test_stagnation_ignores_runs_shorter_than_the_minimum():
    dates = pd.date_range("2024-01-01", periods=70, freq="D")
    eff = [0.03] * 66 + [0.001] * 4
    runs = pm.stagnation_periods(series(dates, DischargeEffectiveness=eff), min_reports=5, lookback=30)
    assert runs.empty


# ── conservation is only checked across consecutive days ─────────────────────

def test_conservation_residual_only_on_consecutive_day_pairs():
    df = series(
        ["2025-01-01", "2025-01-02", "2025-01-05"],     # second gap is 3 days
        Apprehended=[0, 10, 10], Transferred=[0, 4, 4], CBPCustody=[100, 108, 200],
    )
    out = pm.conservation_check(df)
    assert out.loc[1, "ConservationResidual"] == pytest.approx(108 - (100 + 10 - 4))
    assert np.isnan(out.loc[2, "ConservationResidual"]), "a 3-day gap must not be compared as if it were one day"


# ── capacity gap arithmetic ──────────────────────────────────────────────────

def test_capacity_gap_arithmetic():
    dates = pd.date_range("2025-01-01", periods=20, freq="D")
    df = series(dates, HHSCare=[1000] * 20, Discharged=[10] * 20)
    gap = fc.capacity_gap(df, target_clearance_days=20)
    assert gap["required_daily_discharge"] == pytest.approx(50.0)
    assert gap["current_daily_discharge"] == pytest.approx(10.0)
    assert gap["percent_increase_needed"] == pytest.approx(400.0)


# ── sudden drops date an onset ───────────────────────────────────────────────

def test_sudden_drop_detector_finds_one_onset():
    dates = pd.date_range("2025-01-01", periods=80, freq="D")
    discharged = [100] * 50 + [20] * 30
    df = series(dates, Discharged=discharged)
    drops = pm.sudden_drops(df)
    assert len(drops) == 1
    assert drops.loc[0, "Start"] >= pd.Timestamp("2025-02-19")   # not before the level actually falls
    assert drops.loc[0, "Start"] <= pd.Timestamp("2025-02-25")


# ── statistics degrade rather than print nan ─────────────────────────────────

def test_regime_comparison_with_no_data_after_the_split_says_so():
    dates = pd.date_range("2024-01-01", periods=40, freq="D")
    df = series(dates, DischargeEffectiveness=np.linspace(0.02, 0.03, 40))
    t = se.compare_periods(df, "DischargeEffectiveness", "2025-01-01", "before", "after")
    assert t.valid is False and t.significant is False
    assert "not enough reports" in t.sentence()
    assert "nan" not in t.sentence().lower()


def test_regime_comparison_detects_a_real_shift():
    dates = pd.date_range("2024-11-01", periods=120, freq="D")
    rng = np.random.default_rng(1)
    eff = np.r_[rng.normal(0.03, 0.003, 61), rng.normal(0.006, 0.002, 59)]
    t = se.compare_periods(series(dates, DischargeEffectiveness=eff), "DischargeEffectiveness", "2025-01-01", "before", "after")
    assert t.valid and t.significant and t.median_b < t.median_a


# ── outcome stability score ──────────────────────────────────────────────────

def test_outcome_stability_score_is_100_for_constant_and_lower_for_volatile_outcomes():
    dates = pd.date_range("2024-01-01", periods=40, freq="D")
    steady = series(dates, DischargeEffectiveness=[0.03] * 40)
    volatile = series(dates, DischargeEffectiveness=[0.01, 0.05] * 20)

    assert pm.outcome_stability_score(steady).iloc[-1] == pytest.approx(100.0)
    v = pm.outcome_stability_score(volatile).iloc[-1]
    assert 0 <= v < 50          # std ≈ 0.02, mean 0.03 → CV ≈ 0.68 → score ≈ 32
