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
import plotly.io as pio
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

# One color per pipeline entity, kept identical in every chart. Validated for
# colour-blind separation on the sets that appear together (dataviz skill
# validator): {CBP, HHS} and {apprehended, transferred, discharged}.
C = {
    "hhs":         "#2a78d6",  # blue   — HHS care population / single-series charts
    "cbp":         "#eb6834",  # orange — CBP custody & apprehensions (intake side)
    "discharged":  "#1baf7a",  # aqua   — discharges to sponsors
    "transferred": "#6250d6",  # violet — CBP → HHS transfers, pipeline throughput
    "growing":     "#e34948",  # diverging pole: backlog growing
    "clearing":    "#2a78d6",  # diverging pole: backlog clearing
    "critical":    "#d03b3b",  # status — threshold lines & breaches only
    "good":        "#0ca30c",
    "warning":     "#fab219",
    "ink":         "#0b0b0b",
    "ink2":        "#52514e",
    "muted":       "#898781",
    "grid":        "#e1e0d9",
    "axis":        "#c3c2b7",
    "surface":     "#fcfcfb",
}


def tint(hex_color: str, alpha: float = 0.12) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


_FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
pio.templates["uac"] = go.layout.Template(
    layout=dict(
        font=dict(family=_FONT, size=13, color=C["ink2"]),
        title=dict(font=dict(size=15, color=C["ink"]), x=0, xanchor="left"),
        colorway=[C["hhs"], C["cbp"], C["discharged"], C["transferred"]],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=24, t=56, b=40),
        xaxis=dict(showgrid=False, linecolor=C["axis"], ticks="outside",
                   tickcolor=C["axis"], tickfont=dict(color=C["muted"])),
        yaxis=dict(gridcolor=C["grid"], gridwidth=1, zeroline=False,
                   linecolor=C["axis"], tickfont=dict(color=C["muted"])),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    font=dict(color=C["ink2"]), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=C["grid"],
                        font=dict(family=_FONT, color=C["ink"])),
        bargap=0.15,
    ),
    data=dict(
        bar=[go.Bar(marker=dict(line=dict(width=0)))],
        scatter=[go.Scatter(line=dict(width=2))],
    ),
)
pio.templates.default = "plotly_white+uac"

st.markdown(
    f"""
    <style>
    .block-container {{padding-top: 3.5rem; max-width: 1400px;}}
    h1, h2, h3 {{letter-spacing: -0.01em; color: {C["ink"]};}}
    [data-testid="stMainBlockContainer"] h3 {{font-size: 18px; font-weight: 600; padding: 18px 0 6px;}}

    /* hero */
    .hero {{padding: 4px 0 18px; border-bottom: 1px solid {C["grid"]}; margin-bottom: 20px;}}
    .hero .eyebrow {{font-size: 12px; font-weight: 600; letter-spacing: .08em;
                    text-transform: uppercase; color: {C["hhs"]}; margin-bottom: 6px;}}
    .hero h1 {{font-size: 30px; line-height: 1.15; margin: 0 0 6px; padding: 0;}}
    .hero p {{color: {C["ink2"]}; margin: 0; font-size: 15px;}}
    .pipeline {{display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-top:14px;
               font-size:13px; color:{C["ink2"]};}}
    .pipeline .stage {{display:inline-flex; align-items:center; gap:6px; padding:4px 10px;
                      border:1px solid {C["grid"]}; border-radius:999px; background:#fff;}}
    .pipeline .dot {{width:8px; height:8px; border-radius:50%;}}
    .pipeline .arrow {{color:{C["muted"]};}}

    /* KPI cards */
    [data-testid="stMetric"] {{
        background: {C["surface"]}; border: 1px solid rgba(11,11,11,0.08);
        border-radius: 12px; padding: 14px 16px; height: 100%;
        transition: border-color .15s ease, box-shadow .15s ease;
    }}
    [data-testid="stMetric"]:hover {{border-color: rgba(11,11,11,0.16);
        box-shadow: 0 1px 2px rgba(11,11,11,0.04), 0 4px 12px rgba(11,11,11,0.04);}}
    [data-testid="stMetricLabel"] p {{font-size: 13px; color: {C["ink2"]}; font-weight: 500;}}
    [data-testid="stMetricValue"] {{font-size: 26px; font-weight: 600; color: {C["ink"]};}}
    .section-label {{font-size: 12px; font-weight: 600; letter-spacing: .08em;
                    text-transform: uppercase; color: {C["muted"]}; margin: 6px 0 8px;}}

    /* alerts: status colour + icon + label, never colour alone */
    .alert {{display:flex; gap:10px; align-items:flex-start; padding:12px 14px;
            border-radius:10px; border:1px solid; font-size:14px; line-height:1.5;
            color:{C["ink"]}; margin: 4px 0 12px;}}
    .alert .ic {{flex:none; width:20px; height:20px; border-radius:50%; color:#fff;
                display:flex; align-items:center; justify-content:center;
                font-size:12px; font-weight:700; margin-top:1px;}}
    .alert-red   {{background:{tint(C["critical"], .06)}; border-color:{tint(C["critical"], .35)};}}
    .alert-red .ic {{background:{C["critical"]};}}
    .alert-green {{background:{tint(C["good"], .06)}; border-color:{tint(C["good"], .35)};}}
    .alert-green .ic {{background:{C["good"]};}}
    .alert-amber {{background:{tint(C["warning"], .10)}; border-color:{tint(C["warning"], .55)};}}
    .alert-amber .ic {{background:{C["warning"]}; color:{C["ink"]};}}

    /* tabs */
    .stTabs [data-baseweb="tab-list"] {{gap: 4px; border-bottom: 1px solid {C["grid"]};}}
    .stTabs [data-baseweb="tab"] {{padding: 10px 14px; font-weight: 500;}}

    /* sidebar */
    [data-testid="stSidebar"] {{border-right: 1px solid {C["grid"]};}}
    [data-testid="stSidebar"] h1 {{font-size: 20px;}}

    [data-testid="stPlotlyChart"] {{background:{C["surface"]}; border:1px solid rgba(11,11,11,0.06);
        border-radius:12px; padding:8px 8px 4px;}}

    @media (prefers-reduced-motion: reduce) {{ * {{transition: none !important;}} }}
    </style>
    """,
    unsafe_allow_html=True,
)


def alert(kind: str, html: str) -> None:
    """Status banner: colour + icon + text. kind ∈ red | amber | green."""
    icon = {"red": "!", "amber": "!", "green": "✓"}[kind]
    st.markdown(f'<div class="alert alert-{kind}"><span class="ic">{icon}</span>'
                f'<div>{html}</div></div>', unsafe_allow_html=True)


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
    st.title("Controls")
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
    st.markdown('<div class="section-label">Ratio metrics</div>', unsafe_allow_html=True)
    show_te = st.toggle("Transfer Efficiency (Transfers ÷ CBP Custody)", value=True)
    show_de = st.toggle("Discharge Effectiveness (Discharges ÷ HHS Care)", value=True)
    show_pt = st.toggle("Pipeline Throughput (Exits ÷ Entries)", value=True)
    show_forecast = st.toggle("Show discharge forecast", value=True)
    clearance_target = st.slider("Clearance target (days)", 10, 180, 30)

    st.markdown("---")
    st.markdown('<div class="section-label">Alert thresholds</div>', unsafe_allow_html=True)
    thr_te = st.slider("Min Transfer Efficiency (%)", 0, 150, 50, step=5) / 100
    thr_de = st.slider("Min Discharge Effectiveness (%)", 0.0, 7.0, 1.0, step=0.1) / 100
    thr_pt = st.slider("Min Pipeline Throughput (%)", 0, 300, 100, step=10) / 100
    thr_bl = st.slider("Max backlog growth (children/day, 7-day avg)", 0, 200, 25, step=5)

    st.markdown("---")
    st.caption(f"**Records:** {len(df):,}  |  **Range:** {d0.date()} → {d1.date()}")


# ── header ────────────────────────────────────────────────────────────────────

st.markdown(
    f"""
    <div class="hero">
      <div class="eyebrow">HHS · Unaccompanied Alien Children Program</div>
      <h1>Care Transition Efficiency &amp; Placement Outcomes</h1>
      <p>How efficiently children move from CBP custody through HHS care to a vetted sponsor.
         {len(df):,} reports · {d0:%b %d, %Y} – {d1:%b %d, %Y}</p>
      <div class="pipeline">
        <span class="stage"><span class="dot" style="background:{C["cbp"]}"></span>CBP custody</span>
        <span class="arrow">→</span>
        <span class="stage"><span class="dot" style="background:{C["transferred"]}"></span>Transfer to HHS</span>
        <span class="arrow">→</span>
        <span class="stage"><span class="dot" style="background:{C["hhs"]}"></span>HHS care</span>
        <span class="arrow">→</span>
        <span class="stage"><span class="dot" style="background:{C["discharged"]}"></span>Sponsor placement</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if len(df) < 10:
    st.warning("Too few records in the selected date range. Broaden the filter.")
    st.stop()

# ── KPI strip ─────────────────────────────────────────────────────────────────

latest = df.iloc[-1]
prior  = df.iloc[-8] if len(df) >= 8 else df.iloc[0]
bl_series = backlog_rate(df)
stab_series = outcome_stability_score(df)
bl_latest = bl_series.iloc[-1]
stab_latest = stab_series.iloc[-1]
cg = capacity_gap(df, target_clearance_days=clearance_target)


def _fmt(v, f):
    return "N/A" if v is None or np.isnan(v) else f.format(v)


st.markdown(f'<div class="section-label">Latest report · {latest["Date"]:%b %d, %Y}</div>',
            unsafe_allow_html=True)
c = st.columns(4)
with c[0]:
    st.metric("HHS Population", f"{int(latest['HHSCare']):,}",
              delta=f"{int(latest['HHSCare'] - prior['HHSCare']):+,} vs 7 reports ago",
              delta_color="inverse")
with c[1]:
    st.metric("Transfer Efficiency Ratio", _fmt(latest["TransferEfficiency"], "{:.1%}"),
              help="Transfers ÷ CBP Custody — speed of the CBP → HHS handoff")
with c[2]:
    st.metric("Discharge Effectiveness Index", _fmt(latest["DischargeEffectiveness"], "{:.2%}"),
              help="Discharges ÷ HHS Care — daily placement success")
with c[3]:
    st.metric("Pipeline Throughput", _fmt(latest["PipelineThroughput"], "{:.0%}"),
              help="Total exits ÷ Total entries — above 100% means the system is draining")

c = st.columns(4)
with c[0]:
    st.metric("Backlog Accumulation Rate", _fmt(bl_latest, "{:+.1f}/day"),
              help="Change in the 7-report average HHS population. "
                   "Positive = backlog growing, negative = clearing.")
with c[1]:
    st.metric("Outcome Stability Score", _fmt(stab_latest, "{:.0f} / 100"),
              help="100 × (1 − coefficient of variation) of Discharge Effectiveness over the "
                   "last 30 reports. Higher = more consistent placements.")
with c[2]:
    pct = cg["percent_increase_needed"]
    st.metric(f"Discharge Gap · {clearance_target}-day target",
              "∞" if np.isinf(pct) else f"{pct:+.0f}%",
              help=f"Need {cg['required_daily_discharge']:.1f}/day; "
                   f"current {cg['current_daily_discharge']:.1f}/day")
with c[3]:
    st.metric("Required discharges / day", f"{cg['required_daily_discharge']:.1f}",
              delta=f"current {cg['current_daily_discharge']:.1f}/day", delta_color="off")

checks = [
    ("Transfer Efficiency", latest["TransferEfficiency"], thr_te, "below", f"{thr_te:.0%}", "{:.1%}"),
    ("Discharge Effectiveness", latest["DischargeEffectiveness"], thr_de, "below", f"{thr_de:.1%}", "{:.2%}"),
    ("Pipeline Throughput", latest["PipelineThroughput"], thr_pt, "below", f"{thr_pt:.0%}", "{:.0%}"),
    ("Backlog growth", bl_latest, thr_bl, "above", f"{thr_bl:+.0f}/day", "{:+.1f}/day"),
]
breaches = [
    f"<b>{name}</b> is {fmt.format(val)} — {direction} the {thr_txt} threshold"
    for name, val, thr, direction, thr_txt, fmt in checks
    if not np.isnan(val) and ((direction == "below" and val < thr) or (direction == "above" and val > thr))
]
st.write("")
if breaches:
    alert("red", f"<b>{len(breaches)} threshold alert(s)</b> on the latest report<br>"
                 + "<br>".join(breaches))
else:
    alert("green", "All metrics are within your alert thresholds on the latest report.")

# ── tabs ──────────────────────────────────────────────────────────────────────

tabs = st.tabs(
    [
        "Pipeline Flow",
        "Transfer & Discharge",
        "Bottleneck Detection",
        "Outcome Trends",
        "Statistics",
        "Data",
    ]
)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Pipeline Flow
# ══════════════════════════════════════════════════════════════════════════════

with tabs[0]:
    st.subheader("Care Pipeline Population Over Time")

    fig = go.Figure()
    for col, name, color, fill in [
        ("CBPCustody", "CBP Custody", C["cbp"], tint(C["cbp"])),
        ("HHSCare",    "HHS Care",    C["hhs"], tint(C["hhs"])),
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
    st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Daily Inflows vs Outflows")
        fig2 = go.Figure()
        for col, name, color in [("Apprehended", "Apprehended", C["cbp"]),
                                 ("Transferred", "Transferred to HHS", C["transferred"]),
                                 ("Discharged",  "Discharged",  C["discharged"])]:
            fig2.add_trace(go.Scatter(x=df["Date"], y=df[col].rolling(7, min_periods=1).mean(),
                                      name=name, line=dict(color=color, width=2),
                                      hovertemplate="%{y:,.0f}/day"))
        fig2.update_layout(hovermode="x unified", height=340,
                           yaxis_title="Children / day (7-report avg)")
        st.plotly_chart(fig2, width="stretch")

    with c2:
        st.subheader("7-Day Rolling HHS Backlog Rate")
        bl = bl_series
        fig3 = go.Figure()
        fig3.add_trace(
            go.Bar(
                x=df["Date"], y=bl,
                marker_color=[C["growing"] if v > 0 else C["clearing"] for v in bl.fillna(0)],
                name="Net HHS change (7d avg)",
            )
        )
        fig3.add_hline(y=0, line_dash="dot", line_color="grey")
        fig3.add_hline(y=thr_bl, line_dash="dash", line_color=C["critical"],
                       annotation_text=f"Alert +{thr_bl}/day", annotation_position="top right")
        fig3.update_layout(height=320, yaxis_title="Net daily change")
        st.plotly_chart(fig3, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Transfer & Discharge
# ══════════════════════════════════════════════════════════════════════════════

with tabs[1]:
    st.subheader("Transfer Efficiency & Discharge Effectiveness Over Time")

    selected = [
        m for m, on in [
            (("TransferEfficiency",     "Transfer Efficiency",     C["hhs"], thr_te), show_te),
            (("DischargeEffectiveness", "Discharge Effectiveness", C["discharged"], thr_de), show_de),
            (("PipelineThroughput",     "Pipeline Throughput",     C["transferred"], thr_pt), show_pt),
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
                           marker=dict(color=C["critical"], size=8, symbol="x-thin", line=dict(width=2, color=C["critical"])), name="Below threshold")
            )
            fig.add_hline(y=thr, line_dash="dash", line_color=C["critical"],
                          annotation_text=f"Alert threshold {thr:.1%}", annotation_position="top left")
            fig.update_layout(title=f"{name} — {int(below.sum())} of {len(s)} reports below threshold",
                              hovermode="x unified", yaxis_tickformat=".0%", height=300,
                              legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig, width="stretch")
    else:
        st.info("Turn on at least one ratio metric in the sidebar.")

    if show_forecast:
        st.subheader(f"Discharge Forecast (Next 90 Days) · {clearance_target}-Day Clearance Target")
        fc_df = linear_forecast(df, "Discharged", horizon_days=90)
        # discharges cannot go negative — clip the projection and its band at zero
        fc_df[["Forecast", "Lower95", "Upper95"]] = fc_df[["Forecast", "Lower95", "Upper95"]].clip(lower=0)

        fig_fc = go.Figure()
        fig_fc.add_trace(
            go.Scatter(x=df["Date"], y=df["Discharged"], name="Actual discharges",
                       line=dict(color=C["discharged"], width=2))
        )
        fig_fc.add_trace(
            go.Scatter(
                x=pd.concat([fc_df["Date"], fc_df["Date"][::-1]]),
                y=pd.concat([fc_df["Upper95"], fc_df["Lower95"][::-1]]),
                fill="toself", fillcolor=tint(C["discharged"]),
                line=dict(color="rgba(255,255,255,0)"),
                name="95% CI",
            )
        )
        fig_fc.add_trace(
            go.Scatter(x=fc_df["Date"], y=fc_df["Forecast"], name="Forecast",
                       line=dict(color=C["discharged"], width=2, dash="dash"))
        )
        cg = capacity_gap(df, target_clearance_days=clearance_target)
        fig_fc.add_hline(
            y=cg["required_daily_discharge"],
            line_dash="dot", line_color=C["critical"],
            annotation_text=f"Required: {cg['required_daily_discharge']:.0f}/day",
            annotation_position="top left",
        )
        fig_fc.update_layout(hovermode="x unified", height=360, yaxis_title="Discharges / day",
                             legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig_fc, width="stretch")

        pct = cg["percent_increase_needed"]
        if np.isinf(pct) or pct > 50:
            alert("red", f'To clear the HHS backlog of <b>{cg["current_hhs_population"]:,.0f}</b> children '
                f'within <b>{clearance_target} days</b>, daily discharges must rise from '
                f'<b>{cg["current_daily_discharge"]:.0f}</b> to <b>{cg["required_daily_discharge"]:.0f}</b> '
                f'(+{pct:.0f}% increase required).')
        else:
            alert("green", f'Current discharge rate is within reach of the {clearance_target}-day clearance '
                f'target (+{pct:.0f}% needed).')


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Bottleneck Detection
# ══════════════════════════════════════════════════════════════════════════════

with tabs[2]:
    st.subheader("Stagnation Periods (Low Discharge Effectiveness)")

    stag = stagnation_periods(df, min_reports=5, lookback=30, fraction=0.4)

    if stag.empty:
        alert("green", 'No stagnation periods detected in the selected window.')
    else:
        alert("red", f'<b>{len(stag)}</b> stagnation period(s) detected where discharge '
            f'effectiveness collapsed below 40% of the rolling baseline.')
        st.dataframe(
            stag.rename(columns={"MeanMetric": "Mean Discharge Effectiveness"}),
            width="stretch",
            hide_index=True,
        )

    st.markdown("---")
    st.subheader("Sudden Discharge Drops")

    drops = sudden_drops(df, min_duration=5)

    if drops.empty:
        alert("green", 'No sudden discharge drops detected.')
    else:
        alert("amber", f'<b>{len(drops)}</b> sudden drop event(s) where discharges fell '
            f'below 50% of the prior 30-day rolling mean.')
        st.dataframe(drops, width="stretch", hide_index=True)

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
        color_discrete_map={"Weekday": C["hhs"], "Weekend": C["cbp"]},
        title="Discharge Effectiveness: Weekday vs Weekend",
    )
    fig_box.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig_box, width="stretch")


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
        ("Apprehended", "Avg Daily Apprehensions", C["cbp"]),
        ("Discharged",  "Avg Daily Discharges",    C["discharged"]),
        ("Transferred", "Avg Daily Transfers",     C["transferred"]),
    ]:
        fig_m.add_trace(
            go.Scatter(x=monthly["YearMonth"], y=monthly[col], name=name,
                       mode="lines+markers", line=dict(color=color, width=2))
        )
    fig_m.update_layout(hovermode="x unified", height=380,
                        yaxis_title="Children / day (monthly avg)",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig_m, width="stretch")

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
    st.dataframe(monthly_disp, width="stretch", hide_index=True)

    st.markdown("---")
    st.subheader("Outcome Stability — Rolling Std Dev of Discharge Effectiveness")

    roll_std = df["DischargeEffectiveness"].rolling(30, min_periods=5).std()
    fig_std = go.Figure()
    fig_std.add_trace(
        go.Scatter(x=df["Date"], y=roll_std, name="30-day rolling σ",
                   line=dict(color=C["hhs"], width=2), fill="tozeroy",
                   fillcolor=tint(C["hhs"]))
    )
    fig_std.update_layout(height=300, yaxis_title="Standard deviation",
                          hovermode="x unified")
    st.plotly_chart(fig_std, width="stretch")
    st.caption("Higher values = less consistent placement outcomes.")

    st.subheader("Outcome Stability Score (0–100, 30-report window)")
    fig_ss = go.Figure()
    fig_ss.add_trace(go.Scatter(x=df["Date"], y=stab_series, name="Stability score",
                                line=dict(color=C["hhs"], width=2)))
    fig_ss.update_layout(height=300, yaxis_title="Score", yaxis_range=[0, 100],
                         hovermode="x unified")
    st.plotly_chart(fig_ss, width="stretch")
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
        alert("amber" if result.significant else "green", result.sentence())

        fig_v = go.Figure()
        for label, grp, color in [
            ("Before", df[df["Date"] < split_ts][metric_choice].dropna(), C["hhs"]),
            ("After",  df[df["Date"] >= split_ts][metric_choice].dropna(), C["cbp"]),
        ]:
            fig_v.add_trace(go.Violin(y=grp, name=label, fillcolor=color,
                                      line_color=color, opacity=0.7, box_visible=True,
                                      meanline_visible=True))
        fig_v.update_layout(height=350, yaxis_title=metric_choice,
                            violinmode="overlay", showlegend=True)
        st.plotly_chart(fig_v, width="stretch")
    else:
        st.warning(result.sentence())

    st.markdown("---")
    st.subheader("Distribution Summary")

    desc = (
        df[["TransferEfficiency", "DischargeEffectiveness", "PipelineThroughput"]]
        .describe()
        .round(4)
    )
    st.dataframe(desc, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — Raw Data
# ══════════════════════════════════════════════════════════════════════════════

with tabs[5]:
    st.subheader("Dataset Preview")
    st.dataframe(
        df.assign(Date=df["Date"].dt.strftime("%Y-%m-%d")),
        width="stretch",
        height=450,
    )

    csv_bytes = df.to_csv(index=False).encode()
    st.download_button(
        label="Download filtered CSV",
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
