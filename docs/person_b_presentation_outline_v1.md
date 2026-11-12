# Person B Presentation Content Outline — Private Working Draft

**Status:** Private content outline, not a public slide deck. Aggregate figures below are candidates for review, not release approval. Exclude trip, shipment, lane, endpoint, precise-time, local-explanation, and other row-level detail.

## 1. Person B's role

- Build the saved XGBoost travel-ratio prediction workflow, split-conformal intervals, lane risk analysis, Prediction API, SHAP explainability, and structural-cascade illustration.
- Distinguish completed independent work from the pending A/B/C operational integration.

## 2. Prediction pipeline

- Request adapter validates caller-supplied precomputed, as-of directed-lane history.
- Feature builder applies the frozen ten-feature B02 contract.
- XGBoost predicts a residual; the API adds `lane_base` to obtain `pred_ratio`.
- The API can attach saved Method C bounds without recalibration.
- Do not show real endpoint identifiers or rows.

## 3. Prediction and aggregate evaluation

- Candidate aggregate result from the saved 4,394-leg held-out test export: model MAE/RMSE `0.653957` / `1.727803` in delay-ratio units.
- The B02 as-of history baseline on the same rows: `0.668606` / `1.737590`. Explain that this is distinct from B05's fixed training-only baseline comparison.
- Source: `experiments/day2/master_split/final_eval_master_split_v1.json`, `experiments/day2/master_split/final_model_card_master_split_v1.json`, and the saved-prediction error calculation documented in `docs/person_b_day1_day5_handoff.md`. This is a saved evaluation, not a retraining result. Obtain project/data-owner approval before presenting the figures.

## 4. Conformal interval interpretation

- Method C uses calibration residuals, route type, and distance bucket; fallback is group-specific when supported and global otherwise.
- Source: `experiments/day3/master_split_v2/final/interval_comparison_master_split_v2.csv`. Saved aggregate held-out empirical coverages: 46.15%, 77.63%, and 88.85% for nominal 50%, 80%, and 90% levels on 4,394 legs.
- Describe these as observed leg-level split-partition results. They are not online guarantees, lane-level guarantees, or confidence probabilities.
- Require owner approval before using these aggregate metrics in external slides.

## 5. Lane risk analysis

- A canonical 292-directed-lane table was recorded in the original checkout with baseline ratio, predicted ratio, representative interval endpoints, and relative multipliers; it is not included in this source-only worktree package.
- No validated discrete low/medium/high risk category or approved cost-multiplier interpretation is established by this outline. Do not invent one.
- Do not include the table, lane-specific rankings, or realized lane outcomes without data-owner approval.

## 6. Prediction API

- Current input contract requires precomputed as-of lane history; zero history uses the documented fit-only baseline.
- Fresh local test checkpoint: 8/8 API tests passed.
- API smoke demo command: `.\.venv\Scripts\python.exe models/person_b_prediction_demo.py`.
- State clearly that the demo's request is synthetic while it loads the saved real model and calibration artifacts.

## 7. Explainability

- Native XGBoost TreeSHAP is used because SHAP `TreeExplainer` could not parse the saved vector-valued XGBoost base score.
- Saved full-test validation reports a 4,394 × 11 contribution matrix and maximum additivity error `5.270703695714474e-07` against a `1e-6` tolerance. Contributions explain the residual prediction, not final `pred_ratio`.
- Global feature-importance results are aggregate candidates; share only after model/data-owner approval. No real local explanation or row contribution should appear in slides. SHAP values are not causal effects.
- Fresh local test checkpoint: 9/9 SHAP tests passed; the tests do not rerun the full-population analysis.

## 8. Synthetic demonstration

- API + interval + local native contribution: one hypothetical request using synthetic endpoint labels; show software flow, not accuracy or business impact.
- Structural cascade: the separate H1–H8 fixture in `models/person_b_demo.py`; label all node values synthetic.
- Commands:

```powershell
.\.venv\Scripts\python.exe models/person_b_prediction_demo.py
.\.venv\Scripts\python.exe models/person_b_demo.py
```

## 9. Limitations and dependencies

- B05 cell 15 remains unresolved; cell 14 is in-sample exploratory analysis and must not be called held-out evaluation.
- Raw source data is not available for a full source-data rebuild.
- Day 6 is not currently approved end-to-end integration. A must confirm the final duration-aware simulator interface; B must align its adapter only after that source is available; C must confirm the frozen plan and its hash/provenance. Exact plan-snapshot details stay in the private handoff and should not appear on slides; C confirmation remains pending.
- The original-checkout manifest records 40/40 scenarios × strategies under 5,395 legs / 14 demand days, 40-day simulator horizon, and static 14-day closure; 19 runs are recovery-censored. This is historical, configuration-specific evidence, not current branch or team approval. The earlier 7-day/120-day/3-day configuration is distinct and cannot be combined with it.
- Row-level predictions, outcomes, intervals, SHAP contributions, lane tables, model weights, and calibration artifacts retain the internal/approval classifications in `docs/person_b_release_readiness_v1.md`.

## 10. Suggested closing statement

Person B has independently implemented and tested prediction, interval, risk-analysis, explainability, and synthetic demonstration components. These results do not establish production deployment or complete Day 6 team integration; the current A/C interface and plan approvals remain dependencies.