# Care Transition Efficiency & Placement Outcome Analytics
## A Process Efficiency Analysis of the HHS Unaccompanied Alien Children Program

**Author:** Mahak Fahad  
**Institution:** Chennai Institute of Technology, CSE Batch 2029  
**Internship:** Unified Mentor — U.S. Department of Health & Human Services UAC Program Analytics  
**Date:** November 2026  

---

## Abstract

This study applies a process-efficiency lens to the Unaccompanied Alien Children (UAC) care pipeline operated by the U.S. Department of Health and Human Services (HHS) Office of Refugee Resettlement. Using 720 daily reports from January 2023 to December 2025, we derive five key performance indicators (KPIs) measuring how efficiently children move from CBP apprehension through HHS care to sponsor placement. We find: a mean Transfer Efficiency Ratio of 69.1%; a mean Discharge Effectiveness Index of 2.37% — systematically constrained by population scale; a Pipeline Throughput exceeding 100% in peak periods; two significant discharge disruption events in early 2025; and a weekday-versus-weekend gap that we trace to the reporting schedule rather than to operations. HHS care population peaked at 11,516 children in December 2023, then declined 78% to 2,484 by December 2025. The analysis identifies actionable bottlenecks and provides a 90-day discharge forecast with capacity gap modeling.

---

## 1. Introduction

The UAC program operates a multi-stage humanitarian pipeline. From apprehension by Customs and Border Protection (CBP), through transfer to HHS Office of Refugee Resettlement (ORR) shelters, through care and case management, to discharge and reunification with a vetted sponsor — each stage creates measurable flow. Conventional reporting focuses on headcount (children in custody) rather than process efficiency (how fast and reliably children move through the pipeline).

This paper reframes the question. We do not ask "how many children are in care?" — public dashboards already answer that. We ask: **How efficiently does the system move children through care?** Where do delays concentrate? Are outcomes improving or deteriorating? What discharge rate is required to meet a target clearance timeline?

---

## 2. Dataset Description

| Attribute | Value |
|-----------|-------|
| Source | HHS ORR public reporting |
| Total rows in source | 1,170 |
| Valid daily reports | 720 |
| Date range | January 12, 2023 – December 21, 2025 |
| Reporting frequency | Business days (weekday-dominant) |

**Columns:**
- `Date` — reporting date
- `Children apprehended and placed in CBP custody` — daily CBP intake
- `Children in CBP custody` — CBP active load
- `Children transferred out of CBP custody` — flow to HHS
- `Children in HHS Care` — active HHS population
- `Children discharged from HHS Care` — successful sponsor placements

**Data quality note:** 450 rows were null-padded (trailing blank rows in the source file). These were removed. No imputation was performed on valid rows; all ratio metrics were computed only where denominators were non-zero.

---

## 3. Methodology

### 3.1 Derived KPIs

Five KPIs are computed for each report from the raw columns: three flow ratios and two rolling indicators.

| KPI | Formula | Interpretation |
|-----|---------|----------------|
| Transfer Efficiency Ratio (TER) | `Transferred ÷ CBP Custody` | Speed of CBP → HHS handoff |
| Discharge Effectiveness Index (DEI) | `Discharged ÷ HHS Care` | Daily placement throughput relative to population |
| Pipeline Throughput Rate (PTR) | `(Transferred + Discharged) ÷ (Apprehended + Transferred)` | Net system movement |
| Backlog Accumulation Rate (BAR) | Change in the 7-report rolling mean of HHS Care, per report | Delay severity: positive = backlog growing, negative = clearing |
| Outcome Stability Score (OSS) | `100 × max(0, 1 − σ/μ)` of DEI over the last 30 reports (σ/μ = coefficient of variation) | Placement consistency: 100 = perfectly steady, 0 = spread as large as the mean |

### 3.2 Stagnation Detection

Stagnation is defined as a run of consecutive reports in which the Discharge Effectiveness Index falls below 40% of its 30-day rolling median, for at least 5 consecutive reports. We report both **report count** (number of data rows) and **calendar days** (inclusive date span) to avoid conflating reporting frequency with elapsed time.

### 3.3 Sudden Drop Detection

Sudden drops are periods where daily discharges fall below 50% of the prior 30-day rolling mean, sustained for at least 5 consecutive reports.

### 3.4 Capacity Gap Modeling

Given current HHS population *P* and a target clearance horizon *T* days, the required daily discharge rate is *R = P/T*. The capacity gap is *R − D̄* where *D̄* is the recent 30-day average discharge rate.

### 3.5 Statistical Comparisons

Regime comparisons use the Mann-Whitney U test (non-parametric, appropriate for non-normal distributions). The significance threshold is α = 0.05. Results degrade gracefully when either window has fewer than 10 observations.

---

## 4. Results

### 4.1 Population Trajectory

HHS care population followed a pronounced surge-and-decline pattern:

| Period | Avg HHS Population | Avg Daily Discharges |
|--------|--------------------|----------------------|
| Jan 2023 | 7,370 | 232.0 |
| Peak: Dec 2023 | **11,069** | 358.1 |
| Jan 2024 | 8,851 | 295.3 |
| Jan 2025 | 4,991 | 151.4 |
| Mar 2025 | 2,165 | 14.0 |
| Dec 2025 | 2,445 | 9.6 |

The population peaked at **11,516 children on December 20, 2023** — the highest single-day count in the dataset. By December 2025, the population had fallen 78% to 2,484. This decline reflects both sustained discharge operations and a dramatic reduction in new apprehensions (from ~130/day in late 2023 to ~8/day in late 2025).

### 4.2 Efficiency Metrics Summary

| Metric | Mean | Median | Min | Max |
|--------|------|--------|-----|-----|
| Transfer Efficiency Ratio | 0.691 | 0.704 | 0.0 | 2.30 |
| Discharge Effectiveness Index | 0.0237 | 0.0263 | 0.0 | 0.0664 |
| Pipeline Throughput Rate | 1.641 | 1.312 | 0.458 | 16.0 |

**Transfer Efficiency:** A mean of 69.1% indicates that on a typical day, roughly 69% of CBP-held children were transferred to HHS. Values above 100% (possible when transfers clear a backlog) are mathematically valid and occurred during surge-clearance operations.

**Discharge Effectiveness:** The 2.37% mean reflects the structural relationship between daily discharges (~173 children/day during peak operations) and a population of 6,000–11,000. This metric is most useful for detecting *changes* in placement efficiency, not for absolute benchmarking.

**Pipeline Throughput:** The mean of 164% means exits outnumbered entries on a typical report, driven by high discharge volumes. Because transfers count as both an exit from CBP and an entry to HHS, this ratio is best read as a trend indicator, not as a literal net flow.

| Metric | Mean | Median | Min | Max |
|--------|------|--------|-----|-----|
| Backlog Accumulation Rate (children/report) | −5.7 | +3.1 | −383.6 | +278.0 |
| Outcome Stability Score (0–100) | 69.7 | 75.5 | 6.5 | 83.5 |

**Backlog Accumulation:** The backlog grew on 54.3% of reports, but the mean is negative (−5.7) because the clearing phases were much steeper than the growth phases. By year, the average was +20.6 in 2023 (accumulation), −18.7 in 2024 and −17.2 in 2025 (clearing). The largest single-report growth was +278.0 (January 22, 2023); the steepest clearance was −383.6 (January 15, 2024). On the latest report (December 21, 2025) the rate was +6.4, meaning slight re-accumulation.

**Outcome Stability:** Placement consistency held steady through 2023 (average 77.2) and 2024 (77.1), then fell to 54.9 in 2025. The lowest score, 6.5, came on April 13, 2025, just after the March 2025 stagnation event (Section 4.4). The latest score is 52.9. In other words, discharges in 2025 were both lower and less predictable.

### 4.3 Regime Shift: Pre- vs Post-July 2024

A Mann-Whitney U test splitting the dataset at the median date (July 5, 2024) finds:

> Median Discharge Effectiveness *after* July 2024 (0.0086) is **significantly lower** than *before* (0.0315) — p < 0.0001, n = 360/360.

This confirms a structural shift in placement performance in the second half of the dataset, coinciding with declining intake volumes and reduced system pressure.

### 4.4 Stagnation Events

One stagnation period was detected under the full dataset:

| Event | Start | End | Reports | Calendar Days | Mean DEI |
|-------|-------|-----|---------|---------------|----------|
| 1 | 2025-03-12 | 2025-03-31 | 14 | 20 | 0.0026 |

During this 20-calendar-day window, daily discharges averaged just 0.26% of the HHS population — well below the 1.0–3.0% range typical of healthy operations. This corresponds to the period of minimum system activity in the dataset (March 2025 average: 14.0 discharges/day against 2,165 HHS population).

### 4.5 Sudden Discharge Drop Events

| Event | Start | End | Reports | Calendar Days | Drop Fraction |
|-------|-------|-----|---------|---------------|---------------|
| 1 | 2025-02-17 | 2025-03-04 | 12 | 16 | 0.243 |
| 2 | 2025-03-06 | 2025-03-31 | 18 | 26 | 0.237 |

Both events represent discharges falling to approximately **24% of their prior 30-day mean** — a severe reduction. The two events together span February 17 to March 31, 2025, suggesting a sustained disruption rather than two independent episodes.

### 4.6 Weekday vs Weekend Performance

A Mann-Whitney U test on Discharge Effectiveness by day type finds:

> Median weekend effectiveness (0.0352) is **significantly higher** than weekday (0.0254) — p < 0.0001, n = 590 weekday / 130 weekend reports.

**This gap is most likely a reporting artifact, not a real operational difference.** The dataset has 145–149 reports on each of Monday through Thursday, only 2 on Friday, and 130 on Sunday; there are no Saturday reports. The Sunday report therefore probably covers activity from Friday through Sunday, which would push its discharge count up. Without documentation of the reporting window, this result cannot be used to argue that weekend operations are more effective. The correct next step is to confirm the reporting convention with ORR before using day-of-week comparisons.

### 4.7 Capacity Gap Analysis (December 2025 Baseline)

| Target Clearance | Required Daily Discharge | Current Rate | Gap | Increase Needed |
|-----------------|--------------------------|--------------|-----|-----------------|
| 30 days | 82.8 / day | 8.97 / day | 73.8 / day | +823% |
| 90 days | 27.6 / day | 8.97 / day | 18.6 / day | +208% |

The 30-day clearance scenario is not operationally realistic given current system configuration. The 90-day scenario, while still demanding, corresponds to a discharge rate (27.6/day) that the system sustained routinely in mid-2024.

---

## 5. Discussion

### 5.1 System Phase Transitions

The UAC pipeline exhibited three distinct phases over the study period:

**Phase I — Surge (Jan 2023 – Dec 2023):** Rapid inflow growth pushed HHS population from ~7,370 to 11,516. Despite high volumes, discharge operations kept pace (avg 290 children/day in Dec 2023), maintaining Discharge Effectiveness at 2.5–3.5%.

**Phase II — Clearance (Jan 2024 – Jan 2025):** Intake volumes remained elevated (~150–225/day) while discharge operations continued to clear backlog. HHS population declined from 11,069 to 4,991. Transfer Efficiency improved.

**Phase III — Contraction (Feb 2025 – Dec 2025):** A sudden and sustained collapse in both intake (from 59.6/day in January to 7.7/day by December) and discharge activity (from 151 to 9.6/day). The system appears to have entered a low-activity steady state at ~2,200–2,500 HHS children.

### 5.2 Bottleneck Characteristics

The two sudden-drop events in February–March 2025 did not coincide with an increase in CBP intake (which was also declining), suggesting the disruption was discharge-side rather than intake-driven. Possible causes include staffing changes, policy shifts affecting sponsor vetting processes, or reporting methodology changes.

### 5.3 Operational Implications

1. **Discharge rate is the binding constraint** at all periods. Even during the December 2023 peak, achieving a 30-day clearance would have required doubling the discharge rate.

2. **Day-of-week comparisons are unreliable in this data** because the reporting schedule (no Friday or Saturday reports in practice; Sunday reports likely covering several days) distorts per-report figures. Any weekday analysis needs per-day data first.

3. **Calendar-day accuracy matters.** The stagnation event lasted 20 calendar days, not 14 (the report count). Process SLAs built on report counts will underestimate actual delays by 30% or more during periods of non-daily reporting.

---

## 6. Recommendations

**Immediate (0–30 days)**
- Investigate the February–March 2025 discharge disruption operationally; determine whether it reflects a policy change, staffing issue, or reporting artifact.
- Establish a discharge effectiveness threshold (suggested: DEI < 0.5% for 5+ consecutive reports) as a live operational alert.

**Short-term (30–90 days)**
- Review sponsor-vetting workflows to identify approval backlogs, particularly for the low-intake, low-discharge environment now prevailing.
- Analyze case age distribution within the current 2,484-child HHS population to prioritize longest-staying cases.

**Structural (90+ days)**
- Develop a formal discharge target SLA: a minimum daily discharge count tied to HHS population (e.g., 1.0% DEI floor).
- Publish the reporting window behind each daily figure (especially Sunday reports), so day-of-week analysis becomes reliable.
- Extend this analysis with case-level data (when available) to compute mean and median time-in-care per child, which is the most direct measure of reunification timeliness.

---

## 7. Conclusion

This study demonstrates that the UAC pipeline can be analyzed as a process efficiency system, not merely a capacity monitor. Five KPIs derived from public daily reports reveal phase transitions, bottleneck events, and discharge-side constraints that are invisible to aggregate headcount monitoring. The pipeline's binding constraint across all phases was discharge throughput — not intake volume. With the current HHS population at 2,484, the system is operating well below its demonstrated peak capacity; the challenge is now sustaining adequate discharge operations in a low-intake environment to serve the remaining population efficiently.

The Streamlit dashboard accompanying this paper operationalizes all findings in an interactive interface suitable for case management and policy teams.

---

## References

1. HHS Office of Refugee Resettlement. (2025). *Unaccompanied Children Program — Weekly Reporting Data*. U.S. Department of Health and Human Services.
2. Mann, H. B., & Whitney, D. R. (1947). On a test of whether one of two random variables is stochastically larger than the other. *Annals of Mathematical Statistics*, 18(1), 50–60.
3. U.S. Customs and Border Protection. (2024). *Southwest Land Border Encounters — Unaccompanied Children*. DHS.

---

*All figures in this paper are computed directly from the HHS UAC public dataset. No interpolation or imputation was applied to raw values.*
