"""
Care Transition Efficiency & Placement Outcome Analytics
HHS Unaccompanied Alien Children (UAC) Program — Streamlit Dashboard

Unified Mentor Internship | Mahak Fahad | 2026
"""

from __future__ import annotations

import pathlib
import io

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats

from src.data_io import load_data
from src.pipeline_metrics import (
    add_derived_metrics,
    stagnation_periods,
    sudden_drops,
    backlog_rate,
    outcome_stability_score,
)
from src.forecast import capacity_gap, linear_forecast
from src.stats_evidence import compare_periods, weekday_vs_weekend

# ── page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="UAC Care Transition Analytics",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── styling ───────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    .metric-card {background:#f0f4ff;border-radius:8px;padding:16px;margin:4px 0;}
    .alert-red   {background:#fff0f0;border-left:4px solid #d9534f;padding:12px;border-radius:4px;}
    .alert-green {background:#f0fff4;border-left:4px solid #28a745;padding:12px;border-radius:4px;}
    .alert-amber {background:#fffbea;border-left:4px solid #f0ad4e;padding:12px;border-radius:4px;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ── data loading ──────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _load(raw: bytes) -> pd.DataFrame:
    df = load_data(raw)
    return add_derived_metrics(df)


def find_default_csv() -> pathlib.Path | None:
    here = pathlib.Path(__file__).parent
    for p in here.rglob("*.csv"):
        return p
    return None


# ── sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Controls")
    uploaded = st.file_uploader("Upload dataset CSV", type=["csv"])

    default_path = find_default_csv()
    if uploaded:
        raw_bytes = uploaded.read()
    elif default_path:
        raw_bytes = default_path.read_bytes()
        st.info(f"Using default: `{default_path.name}`")
    else:
        st.error("No CSV found. Upload one above.")
        st.stop()

    df_full = _load(raw_bytes)

    min_date = df_full["Date"].min().date()
    max_date = df_full["Date"].max().date()

    date_range = st.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        d0, d1 = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    else:
        d0, d1 = pd.Timestamp(min_date), pd.Timestamp(max_date)

    df = df_full[(df_full["Date"] >= d0) & (df_full["Date"] <= d1)].copy()

    st.markdown("---")
    st.markdown("**Ratio metrics**")
    show_te = st.toggle("Transfer Efficiency (Transfers ÷ CBP Custody)", value=True)
    show_de = st.toggle("Discharge Effectiveness (Discharges ÷ HHS Care)", value=True)
    show_pt = st.toggle("Pipeline Throughput (Exits ÷ Entries)", value=True)
    show_forecast = st.toggle("Show discharge forecast", value=True)
    clearance_target = st.slider("Clearance target (days)", 10, 180, 30)

    st.markdown("---")
    st.markdown("**Alert thresholds**")
    thr_te = st.slider("Min Transfer Efficiency (%)", 0, 150, 50, step=5) / 100
    thr_de = st.slider("Min Discharge Effectiveness (%)", 0.0, 7.0, 1.0, step=0.1) / 100
    thr_pt = st.slider("Min Pipeline Throughput (%)", 0, 300, 100, step=10) / 100
    thr_bl = st.slider("Max backlog growth (children/day, 7-day avg)", 0, 200, 25, step=5)

    st.markdown("---")
    st.caption(f"**Records:** {len(df):,}  |  **Range:** {d0.date()} → {d1.date()}")


# ── header ────────────────────────────────────────────────────────────────────

st.title("🏥 UAC Care Transition Efficiency & Placement Outcome Analytics")
st.caption(
    "U.S. Department of Health and Human Services · HHS Unaccompanied Alien Children Program"
)

if len(df) < 10:
    st.warning("Too few records in the selected date range. Broaden the filter.")
    st.stop()

# ── KPI strip ─────────────────────────────────────────────────────────────────

latest = df.iloc[-1]
prior  = df.iloc[-8] if len(df) >= 8 else df.iloc[0]

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "HHS Population (latest)",
        f"{int(latest['HHSCare']):,}",
        delta=f"{int(latest['HHSCare'] - prior['HHSCare']):+,} vs 7d ago",
    )
with col2:
    te = latest["TransferEfficiency"]
    st.metric(
        "Transfer Efficiency",
        f"{te:.1%}" if not np.isnan(te) else "N/A",
        help="Transfers ÷ CBP Custody on the latest report date",
    )
with col3:
    de = latest["DischargeEffectiveness"]
    st.metric(
        "Discharge Effectiveness",
        f"{de:.1%}" if not np.isnan(de) else "N/A",
        help="Discharges ÷ HHS Care on the latest report date",
    )
with col4:
    pt = latest["PipelineThroughput"]
    st.metric(
        "Pipeline Throughput",
        f"{pt:.1%}" if not np.isnan(pt) else "N/A",
        help="Total exits ÷ Total entries",
    )
with col5:
    cg = capacity_gap(df, target_clearance_days=clearance_target)
    pct = cg["percent_increase_needed"]
    pct_str = f"{pct:+.0f}%" if not np.isinf(pct) else "∞"
    st.metric(
        f"Discharge Gap ({clearance_target}d target)",
        pct_str,
        help=f"Need {cg['required_daily_discharge']:.0f}/day; current {cg['current_daily_discharge']:.0f}/day",
    )

bl_series = backlog_rate(df)
stab_series = outcome_stability_score(df)
bl_latest = bl_series.iloc[-1]
stab_latest = stab_series.iloc[-1]

k1, k2, k3 = st.columns([1, 1, 3])
with k1:
    st.metric(
        "Backlog Accumulation Rate",
        f"{bl_latest:+.1f}/day" if not np.isnan(bl_latest) else "N/A",
        help="Change in the 7-day average HHS population per report. "
             "Positive = backlog growing, negative = clearing.",
    )
with k2:
    st.metric(
        "Outcome Stability Score",
        f"{stab_latest:.0f} / 100" if not np.isnan(stab_latest) else "N/A",
        help="100 × (1 − coefficient of variation) of Discharge Effectiveness over the "
             "last 30 reports. Higher = more consistent placements.",
    )
with k3:
    checks = [
        ("Transfer Efficiency", latest["TransferEfficiency"], thr_te, "below", f"{thr_te:.0%}", "{:.1%}"),
        ("Discharge Effectiveness", latest["DischargeEffectiveness"], thr_de, "below", f"{thr_de:.1%}", "{:.2%}"),
        ("Pipeline Throughput", latest["PipelineThroughput"], thr_pt, "below", f"{thr_pt:.0%}", "{:.0%}"),
        ("Backlog growth", bl_latest, thr_bl, "above", f"{thr_bl:+.0f}/day", "{:+.1f}/day"),
    ]
    breaches = []
    for name, val, thr, direction, thr_txt, fmt in checks:
        if np.isnan(val):
            continue
        if (direction == "below" and val < thr) or (direction == "above" and val > thr):
            breaches.append(f"<b>{name}</b> is {fmt.format(val)} ({direction} the {thr_txt} threshold)")
    if breaches:
        st.markdown(
            f'<div class="alert-red">🚨 <b>{len(breaches)} threshold alert(s)</b> on the latest report '
            f'({latest["Date"].date()}):<br>' + "<br>".join(breaches) + "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="alert-green">✅ All metrics are within your alert thresholds on the latest '
            f'report ({latest["Date"].date()}).</div>',
            unsafe_allow_html=True,
        )

st.markdown("---")

# ── tabs ──────────────────────────────────────────────────────────────────────

tabs = st.tabs(
    [
        "📊 Pipeline Flow",
        "⚡ Transfer & Discharge",
        "🔍 Bottleneck Detection",
        "📈 Outcome Trends",
        "📐 Statistics",
        "📋 Data",
    ]
)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Pipeline Flow
# ══════════════════════════════════════════════════════════════════════════════

with tabs[0]:
    st.subheader("Care Pipeline Population Over Time")

    fig = go.Figure()
    for col, name, color, fill in [
        ("CBPCustody", "CBP Custody", "#e45756", "rgba(228,87,86,0.13)"),
        ("HHSCare",    "HHS Care",    "#4c78a8", "rgba(76,120,168,0.13)"),
    ]:
        fig.add_trace(
            go.Scatter(
                x=df["Date"], y=df[col], name=name,
                line=dict(color=color, width=2),
                fill="tozeroy", fillcolor=fill,
            )
        )
    fig.update_layout(
        hovermode="x unified",
        yaxis_title="Children in care",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Daily Inflows vs Outflows")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=df["Date"], y=df["Apprehended"], name="Apprehended", marker_color="#e45756"))
        fig2.add_trace(go.Bar(x=df["Date"], y=df["Transferred"], name="Transferred to HHS", marker_color="#f58518"))
        fig2.add_trace(go.Bar(x=df["Date"], y=df["Discharged"],  name="Discharged",  marker_color="#54a24b"))
        fig2.update_layout(barmode="group", hovermode="x unified", height=320, yaxis_title="Children / day")
        st.plotly_chart(fig2, use_container_width=True)

    with c2:
        st.subheader("7-Day Rolling HHS Backlog Rate")
        bl = bl_series
        fig3 = go.Figure()
        fig3.add_trace(
            go.Bar(
                x=df["Date"], y=bl,
                marker_color=["#d9534f" if v > 0 else "#28a745" for v in bl.fillna(0)],
                name="Net HHS change (7d avg)",
            )
        )
        fig3.add_hline(y=0, line_dash="dot", line_color="grey")
        fig3.add_hline(y=thr_bl, line_dash="dash", line_color="#d9534f",
                       annotation_text=f"Alert: +{thr_bl}/day", annotation_position="top left")
        fig3.update_layout(height=320, yaxis_title="Net daily change")
        st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Transfer & Discharge
# ══════════════════════════════════════════════════════════════════════════════

with tabs[1]:
    st.subheader("Transfer Efficiency & Discharge Effectiveness Over Time")

    selected = [
        m for m, on in [
            (("TransferEfficiency",     "Transfer Efficiency",     "#4c78a8", thr_te), show_te),
            (("DischargeEffectiveness", "Discharge Effectiveness", "#54a24b", thr_de), show_de),
            (("PipelineThroughput",     "Pipeline Throughput",     "#f58518", thr_pt), show_pt),
        ] if on
    ]
    if selected:
        # Each ratio lives on a very different scale (DE ≈ 2%, TE ≈ 70%, PT ≈ 160%),
        # so each gets its own panel and its own threshold line.
        for metric, name, color, thr in selected:
            s = df[metric]
            below = s < thr
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Date"], y=s, name=name, line=dict(color=color, width=2)))
            fig.add_trace(
                go.Scatter(x=df.loc[below, "Date"], y=s[below], mode="markers",
                           marker=dict(color="#d9534f", size=6), name="Below threshold")
            )
            fig.add_hline(y=thr, line_dash="dash", line_color="#d9534f",
                          annotation_text=f"Alert threshold {thr:.1%}", annotation_position="top left")
            fig.update_layout(title=f"{name} — {int(below.sum())} of {len(s)} reports below threshold",
                              hovermode="x unified", yaxis_tickformat=".1%", height=300,
                              legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Turn on at least one ratio metric in the sidebar.")

    if show_forecast:
        st.subheader(f"Discharge Forecast (Next 90 Days) · {clearance_target}-Day Clearance Target")
        fc_df = linear_forecast(df, "Discharged", horizon_days=90)

        fig_fc = go.Figure()
        fig_fc.add_trace(
            go.Scatter(x=df["Date"], y=df["Discharged"], name="Actual discharges",
                       line=dict(color="#54a24b", width=2))
        )
        fig_fc.add_trace(
            go.Scatter(
                x=pd.concat([fc_df["Date"], fc_df["Date"][::-1]]),
                y=pd.concat([fc_df["Upper95"], fc_df["Lower95"][::-1]]),
                fill="toself", fillcolor="rgba(76,120,168,0.15)",
                line=dict(color="rgba(255,255,255,0)"),
                name="95% CI",
            )
        )
        fig_fc.add_trace(
            go.Scatter(x=fc_df["Date"], y=fc_df["Forecast"], name="Forecast",
                       line=dict(color="#4c78a8", width=2, dash="dash"))
        )
        cg = capacity_gap(df, target_clearance_days=clearance_target)
        fig_fc.add_hline(
            y=cg["required_daily_discharge"],
            line_dash="dot", line_color="#d9534f",
            annotation_text=f"Required: {cg['required_daily_discharge']:.0f}/day",
            annotation_position="top right",
        )
        fig_fc.update_layout(hovermode="x unified", height=360, yaxis_title="Discharges / day",
                             legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig_fc, use_container_width=True)

        pct = cg["percent_increase_needed"]
        if np.isinf(pct) or pct > 50:
            st.markdown(
                f'<div class="alert-red">⚠️ To clear the HHS backlog of <b>{cg["current_hhs_population"]:,.0f}</b> children '
                f'within <b>{clearance_target} days</b>, daily discharges must rise from '
                f'<b>{cg["current_daily_discharge"]:.0f}</b> to <b>{cg["required_daily_discharge"]:.0f}</b> '
                f'(+{pct:.0f}% increase required).</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="alert-green">✅ Current discharge rate is within reach of the {clearance_target}-day clearance '
                f'target (+{pct:.0f}% needed).</div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Bottleneck Detection
# ══════════════════════════════════════════════════════════════════════════════

with tabs[2]:
    st.subheader("Stagnation Periods (Low Discharge Effectiveness)")

    stag = stagnation_periods(df, min_reports=5, lookback=30, fraction=0.4)

    if stag.empty:
        st.markdown('<div class="alert-green">✅ No stagnation periods detected in the selected window.</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="alert-red">⚠️ <b>{len(stag)}</b> stagnation period(s) detected where discharge '
            f'effectiveness collapsed below 40% of the rolling baseline.</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(
            stag.rename(columns={"MeanMetric": "Mean Discharge Effectiveness"}),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")
    st.subheader("Sudden Discharge Drops")

    drops = sudden_drops(df, min_duration=5)

    if drops.empty:
        st.markdown('<div class="alert-green">✅ No sudden discharge drops detected.</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="alert-amber">⚠️ <b>{len(drops)}</b> sudden drop event(s) where discharges fell '
            f'below 50% of the prior 30-day rolling mean.</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(drops, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Weekly Pattern Analysis (Weekday vs Weekend)")

    result = weekday_vs_weekend(df, "DischargeEffectiveness")
    if result.valid:
        st.info(result.sentence())
    else:
        st.warning(result.sentence())
    dow_counts = df["Date"].dt.day_name().value_counts()
    st.caption(
        "Caution: reports are not filed evenly across the week "
        f"({', '.join(f'{d}: {n}' for d, n in dow_counts.items())}). "
        "Sunday reports likely cover several days, so this gap probably comes from the "
        "reporting schedule, not from how operations perform."
    )

    fig_box = px.box(
        df.assign(DayType=df["Date"].dt.dayofweek.map(lambda d: "Weekday" if d < 5 else "Weekend")),
        x="DayType",
        y="DischargeEffectiveness",
        color="DayType",
        color_discrete_map={"Weekday": "#4c78a8", "Weekend": "#e45756"},
        title="Discharge Effectiveness: Weekday vs Weekend",
    )
    fig_box.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Outcome Trends
# ══════════════════════════════════════════════════════════════════════════════

with tabs[3]:
    st.subheader("Month-over-Month Placement Trends")

    monthly = (
        df.set_index("Date")
        .resample("ME")[["Apprehended", "Transferred", "Discharged", "HHSCare"]]
        .mean()
        .reset_index()
    )
    monthly["YearMonth"] = monthly["Date"].dt.strftime("%b %Y")

    fig_m = go.Figure()
    for col, name, color in [
        ("Apprehended", "Avg Daily Apprehensions", "#e45756"),
        ("Discharged",  "Avg Daily Discharges",    "#54a24b"),
        ("Transferred", "Avg Daily Transfers",     "#f58518"),
    ]:
        fig_m.add_trace(
            go.Scatter(x=monthly["YearMonth"], y=monthly[col], name=name,
                       mode="lines+markers", line=dict(color=color, width=2))
        )
    fig_m.update_layout(hovermode="x unified", height=380,
                        yaxis_title="Children / day (monthly avg)",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig_m, use_container_width=True)

    st.markdown("---")
    st.subheader("Monthly Summary Table")
    monthly_disp = monthly.copy()
    monthly_disp = monthly_disp.rename(columns={
        "YearMonth": "Month",
        "Apprehended": "Avg Apprehensions/day",
        "Transferred":  "Avg Transfers/day",
        "Discharged":   "Avg Discharges/day",
        "HHSCare":      "Avg HHS Population",
    }).drop(columns=["Date"])
    for col in monthly_disp.columns[1:]:
        monthly_disp[col] = monthly_disp[col].round(1)
    st.dataframe(monthly_disp, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Outcome Stability — Rolling Std Dev of Discharge Effectiveness")

    roll_std = df["DischargeEffectiveness"].rolling(30, min_periods=5).std()
    fig_std = go.Figure()
    fig_std.add_trace(
        go.Scatter(x=df["Date"], y=roll_std, name="30-day rolling σ",
                   line=dict(color="#e45756", width=2), fill="tozeroy",
                   fillcolor="rgba(228,87,86,0.15)")
    )
    fig_std.update_layout(height=300, yaxis_title="Standard deviation",
                          hovermode="x unified")
    st.plotly_chart(fig_std, use_container_width=True)
    st.caption("Higher values = less consistent placement outcomes.")

    st.subheader("Outcome Stability Score (0–100, 30-report window)")
    fig_ss = go.Figure()
    fig_ss.add_trace(go.Scatter(x=df["Date"], y=stab_series, name="Stability score",
                                line=dict(color="#4c78a8", width=2)))
    fig_ss.update_layout(height=300, yaxis_title="Score", yaxis_range=[0, 100],
                         hovermode="x unified")
    st.plotly_chart(fig_ss, use_container_width=True)
    st.caption("100 × (1 − coefficient of variation). Higher = more consistent placements.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Statistics
# ══════════════════════════════════════════════════════════════════════════════

with tabs[4]:
    st.subheader("Regime Comparison — Before vs After a Split Date")

    split = st.date_input(
        "Split date",
        value=df["Date"].iloc[len(df) // 2].date(),
        min_value=df["Date"].min().date(),
        max_value=df["Date"].max().date(),
        key="split_date",
    )
    split_ts = pd.Timestamp(split)

    metric_choice = st.selectbox(
        "Metric",
        ["DischargeEffectiveness", "TransferEfficiency", "PipelineThroughput"],
    )

    result = compare_periods(df, metric_choice, split_ts)

    if result.valid:
        icon = "🔴" if result.significant else "🟢"
        st.success(f"{icon} {result.sentence()}")

        fig_v = go.Figure()
        for label, grp, color in [
            ("Before", df[df["Date"] < split_ts][metric_choice].dropna(), "#4c78a8"),
            ("After",  df[df["Date"] >= split_ts][metric_choice].dropna(), "#e45756"),
        ]:
            fig_v.add_trace(go.Violin(y=grp, name=label, fillcolor=color,
                                      line_color=color, opacity=0.7, box_visible=True,
                                      meanline_visible=True))
        fig_v.update_layout(height=350, yaxis_title=metric_choice,
                            violinmode="overlay", showlegend=True)
        st.plotly_chart(fig_v, use_container_width=True)
    else:
        st.warning(result.sentence())

    st.markdown("---")
    st.subheader("Distribution Summary")

    desc = (
        df[["TransferEfficiency", "DischargeEffectiveness", "PipelineThroughput"]]
        .describe()
        .round(4)
    )
    st.dataframe(desc, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — Raw Data
# ══════════════════════════════════════════════════════════════════════════════

with tabs[5]:
    st.subheader("Dataset Preview")
    st.dataframe(
        df.assign(Date=df["Date"].dt.strftime("%Y-%m-%d")),
        use_container_width=True,
        height=450,
    )

    csv_bytes = df.to_csv(index=False).encode()
    st.download_button(
        label="⬇️ Download filtered CSV",
        data=csv_bytes,
        file_name="uac_filtered.csv",
        mime="text/csv",
    )
    st.caption(f"Showing {len(df):,} records from {d0.date()} to {d1.date()}.")

# ── footer ────────────────────────────────────────────────────────────────────

st.markdown("---")
st.caption(
    "Care Transition Efficiency & Placement Outcome Analytics · "
    "Unified Mentor Internship · HHS UAC Program Dataset · "
    "Built with Streamlit + Plotly"
)
