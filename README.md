# Care Transition Efficiency & Placement Outcome Analytics

**Unified Mentor Internship · HHS Unaccompanied Alien Children (UAC) Program**

A Streamlit analytics dashboard that reframes the HHS UAC dataset from capacity monitoring to **process efficiency and outcome evaluation** — measuring how effectively children move through the care pipeline from CBP apprehension through HHS care to sponsor placement.

---

## Live Demo

> Deploy link added after Streamlit Cloud deployment.

---

## Project Structure

```
.
├── app.py                              # Streamlit entry point
├── src/
│   ├── __init__.py
│   ├── data_io.py                      # CSV loader (content-keyed cache)
│   ├── pipeline_metrics.py             # Stagnation, drops, conservation, backlog
│   ├── forecast.py                     # Capacity gap + linear discharge forecast
│   └── stats_evidence.py               # Mann-Whitney regime comparisons
├── test_pipeline.py                    # 7 known-answer tests
├── conftest.py
├── requirements.txt
├── requirements-dev.txt
└── HHS_Unaccompanied_Alien_Children_Program.csv
```

---

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app auto-detects the first `.csv` in its directory. To swap the dataset, upload a new file through the sidebar — the content-keyed cache ensures stale data is never shown.

---

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest test_pipeline.py -v
```

All 7 tests cover:
- Stagnation detection returning **calendar days** (not report counts as a proxy)
- Conservation residuals skipped across non-consecutive date gaps
- Capacity gap arithmetic
- Sudden drop onset detection
- Regime comparison degrading gracefully (no `nan` in UI text) when data is sparse

---

## Key Metrics

| KPI | Formula |
|-----|---------|
| Transfer Efficiency Ratio | `Transferred ÷ CBP Custody` |
| Discharge Effectiveness Index | `Discharged ÷ HHS Care` |
| Pipeline Throughput | `Total exits ÷ Total entries` |
| Backlog Accumulation Rate | `7-day rolling ΔHHSCare` |
| Outcome Stability Score | `100 × (1 − σ/μ)` of DischargeEffectiveness over 30 reports (0–100) |

---

## User Controls (sidebar)

- **Date range** selection: every KPI, chart and alert recalculates for the chosen window
- **Ratio metric toggles**: show or hide Transfer Efficiency, Discharge Effectiveness and Pipeline Throughput one at a time
- **Threshold-based alerts**: set minimums for the three ratios and a maximum for backlog growth. A red banner under the KPIs lists every breach on the latest report, and the charts draw the threshold lines and mark the reports that cross them in red

---

## Dashboard Tabs

1. **Pipeline Flow** — population curves, inflow/outflow bars, backlog rate
2. **Transfer & Discharge** — one panel per ratio, with an alert threshold line and the breaching reports marked, plus the 90-day discharge forecast, capacity gap alert
3. **Bottleneck Detection** — stagnation periods (calendar-day corrected), sudden drop events, weekday vs weekend analysis
4. **Outcome Trends** — month-over-month placement table, outcome stability volatility and the 0–100 Outcome Stability Score
5. **Statistics** — regime comparison (Mann-Whitney U, violin plots), distribution summary
6. **Data** — filtered preview + CSV download

---

## Dataset

`HHS_Unaccompanied_Alien_Children_Program.csv` — 720 daily reports from January 2023 to December 2025, sourced from HHS Office of Refugee Resettlement public data.

Columns:
- `Date` — reporting date
- `Children apprehended and placed in CBP custody*` — daily intake
- `Children in CBP custody` — active CBP load
- `Children transferred out of CBP custody` — flow to HHS
- `Children in HHS Care` — active HHS population
- `Children discharged from HHS Care` — successful sponsor placements

---

## Author

Mahak Fahad · Chennai Institute of Technology · [linkedin.com/in/mahakf](https://linkedin.com/in/mahakf)

Unified Mentor Internship · U.S. Department of Health & Human Services UAC Program Analytics
