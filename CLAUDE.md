# Project context for Claude Code

Unified Mentor internship project: **Care Transition Efficiency & Placement Outcome Analytics** (HHS UAC program dataset).

## State (Nov 6, 2026)
- Dashboard (`app.py`) + analysis modules in `src/` were rebuilt from scratch: the original code was lost, and only the tests, requirements and CSV survived.
- `pytest test_pipeline.py` → 7/7 pass. App smoke-tested headless (`streamlit.testing.v1.AppTest`), including narrow date ranges.
- `research_paper.md` and `executive_summary.md` are written; every number in them was recomputed from the CSV.
- Not yet done: GitHub push, Streamlit Cloud deploy, two submission videos (the user records those).

## Submission form needs (all https:// URLs)
GitHub repo · research paper link · deployed Streamlit link · project explanation video · internship feedback video.

## Facts to keep straight
- 720 valid reports, 2023-01-12 → 2025-12-21. Trailing blank rows in the CSV are dropped on load.
- Stagnation event: 2025-03-12 → 03-31, **14 reports / 20 calendar days**. Always report both counts, never just "days".
- Discharge gap (Dec 2025): ~9/day current; 30-day clearance needs 82.8/day (+823%); 90-day needs 27.6/day (+208%).
- The weekday vs weekend gap comes from the reporting schedule: no Saturday reports, 2 on Friday, 130 on Sunday. Don't present it as an operational finding.
- Numbers from the older chat session (9.6→72.0, +647%, 107-day event, 385-day forecast) are obsolete. Don't reuse them.

## Deploy notes
- Streamlit Cloud: main file `app.py`, **Python 3.12** (the numpy 1.26.4 / pandas 2.2.2 pins have no 3.13 wheels).
- After deploy, add the live URL to the README's "Live Demo" section.

## Rules
- Never add Claude as co-author in commits (no Co-Authored-By / Claude-Session trailers, no "Generated with Claude Code").
- The churn project is separate and not in this repo; it waits on the real churn CSV.
