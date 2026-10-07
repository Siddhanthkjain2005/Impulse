# V7 spline-envelope crest development results — 7 October 2026

The fixed V7 development gate **failed**. The search reduced Switching crest
RMSE against the historical V2 refit and exact workbook kNN, but one of the three
seeds missed the predeclared 2% improvement requirement. The simpler frozen V6
spline control also had slightly lower combined RMSE. No model was promoted or
activated, no final weights or intervals were created, and no new final-test or
laboratory-accuracy claim follows from this study.

## Fixed protocol and data boundary

The separately named protocol was written at `2026-10-07T10:27:34.549107+00:00`
before parsing numerical fit outcomes. It records the complete 12-spec grid,
runner/helper/dataset hashes, historical V2 settings, original fit and excluded
calibration IDs, and 68 preserved V1–V6 source/evidence hashes. The runner refuses
to overwrite an existing protocol, completed result, or failed attempt.

Only the original 560 Switching Train-fit IDs supplied target outcomes. Exact
kNN additionally used the corresponding Lightning fit rows, with both regimes'
outer and inner held rows excluded from its fit data. The loader rejected all
calibration, Validation and Hidden Test rows before converting outcomes to
numbers. Previously explored rows, feature choices and historical V2 selection
remain development information; changing fold seeds does not create independent
data.

The hypothesis was that a multi-input smooth envelope center or Bayesian
regularization could reduce trend-fit variance in relative crest residuals.
No known noise bound or uniform-noise distribution was assumed.

The registered grid contained two input bases, `C,L,C*L` and additive `C,L`.
Each used fold-fitted input scaling, cubic splines with three knots and no
bias column, expanded-feature scaling, and target standardization. The six
estimators per basis were Ridge with alpha 1, Bayesian Ridge, a minimax envelope
with standardized-coefficient L1 penalty 0.001 or 0.01, and the mean of fitted
0.1/0.9 quantiles with alpha 0.0001 or 0.001. The minimax intercept was unpenalized.
No blending or later grid expansion occurred.

Outer evaluation used five folds for each seed 503, 607 and 709. Three inner
folds selected minimum physical-kV MSE; a candidate had to improve at least 2%
over the better inner historical-V2/exact-kNN baseline to replace it. A numerical
failure would disqualify that inner fit, or log an outer fallback to the chosen
baseline. No numerical failures occurred. The exact frozen V6 unweighted compact
spline with alpha 1 was scored separately as a control.

## Results

| Outer seed | V7 RMSE (kV) | V2 refit RMSE (kV) | Exact kNN RMSE (kV) | V6 spline control (kV) | V7 reduction vs V2 |
|---|---:|---:|---:|---:|---:|
| 503 | 3.484093 | 3.567490 | 3.948628 | 3.486527 | 2.3377% |
| 607 | 3.493366 | 3.563200 | 3.932490 | 3.477092 | 1.9599% |
| 709 | 3.506095 | 3.627705 | 3.872745 | 3.505827 | 3.3523% |

Across all 1,680 repeated out-of-fold predictions, V7 RMSE was **3.494530 kV**,
versus 3.586253 kV for historical V2 and 3.918090 kV for exact kNN. These are
2.5576% and 10.8104% error reductions on these development folds. The frozen V6
spline control achieved **3.489836 kV**, so V7's extra complexity increased RMSE
by 0.1345% against that control.

V7 beat both principal baselines in 14 of 15 outer folds. Its 95th-percentile
absolute error was 5.828367 kV, and its worst absolute error was 6.956668 kV on
the repeated development predictions. Those values are descriptive; they are
not guaranteed physical error bounds.

The predeclared promotion gate required at least 2% RMSE reduction versus both
V2 and exact kNN in **every** seed, plus at least 10 of 15 fold wins. Seed 607's
1.959870% reduction against V2 failed that requirement. The requirement was
retained after observing results.

## Decision and verification

Keep existing serving behavior and all prior evidence. Further complexity on
the same synthetic rows is not supported by this comparison. A frozen candidate
needs genuinely independent outcomes for final-test evidence; transfer to CPRI
also needs appropriate physical data and cannot be inferred from this workbook
development study.

The single local run took 10.243 seconds, spent $0 on cloud resources and kept
all 68 recorded protected hashes unchanged. Twenty-one focused tests pass,
covering query-outcome exclusion, restricted baseline fit inputs, fold leakage,
solver failures and explicit fallback, fixed gates, no-overwrite behavior, and
independent recomputation of saved scores. All prior V1–V6 files remain intact.

Evidence: `artifacts/experiments/v7/protocol.json`, `summary.json` and
`oof_predictions.json`. The separate `exploratory_structural` subdirectory
retains the earlier rejected product-only exploration; it was not an additional
post-result V7 search.
