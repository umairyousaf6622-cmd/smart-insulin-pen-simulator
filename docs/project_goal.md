# Project Goal & Definition of Done

## Goal
Learn how medical-device engineering works by building one small piece honestly:
an interactive, visual simulator that explains how an insulin pen works and
fails, with a machine-learning layer that recognizes bad injections.
Documented publicly over 30 days. Software-only: no hardware is involved.

## Core question
How do needle gauge, insulin viscosity (temperature), push speed, and friction
determine injection force, and can a model learn to recognize a faulty
injection (too fast, early release, blocked needle, short hold) from those
signals, and explain why?

## Non-goals
- Not a medical device; no clinical claims; no dosing guidance.
- Not validated on real pens or real patients. Results describe the simulation only.
- No hardware or physical testing.

## How I stay credible without hardware
- Every parameter has a citation or is labelled "assumption".
- The simulator is checked against analytical solutions (e.g. Hagen-Poiseuille,
  conservation of volume) with unit tests.
- Predicted forces are compared with published values from the literature.
- Models are tested for robustness (noise, unseen users, unseen needle gauges).

## Definition of Done

### Minimum viable (Day 14)
- [ ] Physics model with sourced parameters and unit tests
- [ ] 6 fault classes, simulated users, user-level train/test split
- [ ] Model benchmark with honest metrics (cross-validation, cost-aware)
- [ ] README with limitations section

### Full version (Day 30)
- [ ] Interactive Streamlit app: sliders, animated pen cross-section, live graphs, fault explorer
- [ ] Explainability panel (SHAP) showing why the model flagged an injection
- [ ] Dose-regression model plus harder faults (partial blockage, air bubble)
- [ ] Literature comparison and robustness report
- [ ] FMEA / risk table, CI passing, tests, model card
- [ ] Optional: CAD and buckling calculation (software only)
- [ ] 4 Substack articles, 13+ LinkedIn videos, 3-minute demo video

## Success measures (personal)
- Can explain every equation and design choice in an interview
- Repo is reproducible from a clean `pip install`
- Every claim in the README is backed by a test, a citation, or an "assumption" label
