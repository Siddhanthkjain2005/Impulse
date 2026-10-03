# V5 bounded-envelope accuracy experiment

Recorded 3 October 2026. **1.0921% lower macro development error versus a historical V2 refit**, with no output RMSE regression, is below the declared 5% promotion threshold. No model was promoted or fitted for serving. Frozen V1 remains the default and V2 remains the existing optional candidate.

## Hypothesis and registered comparison

Earlier Train-only diagnostics found a relatively flat, bounded residual remainder. That motivates testing whether a trend fitted from residual extremes or symmetric quantiles improves on mean-loss models. It does not establish uniform noise or an irreducible error floor.

The registered grid contained 12 configurations: three estimators (minimax/Chebyshev envelope, midpoint of 10% and 90% quantile regression, matched Ridge control), absolute/relative residuals, and degree-one/two compact mechanism features. Each could be used at 50% or 100% weight alongside the historical V2 fallback. Compact features were reused from V3: total capacitance and inductance for front/peak; load capacitance for tail; total capacitance, inductance and their product for crest. There was no new feature mining or pooling of regimes.

Only the original 560 Train fit IDs per type were eligible. The loader excluded calibration and non-Train rows before parsing their numeric outcomes. Five outer folds and three inner folds used the existing seeds 71/73. Scaling, polynomial transforms, estimation and selection were fitted within training folds. A candidate needed at least 2% lower inner tolerance-normalized MSE to replace the V2 fallback. Final scoring used each held-out row once within this study.

A separate control search selected only among the four matched Ridge configurations and the V2 fallback using the same folds, basis, transforms, blend choices and inner threshold. This helps distinguish envelope estimation from the effect of changing the regression basis.

The protocol, code/dependency hashes and grid were recorded before outcomes were evaluated. The stopping rule allowed this one grid; it prohibited expansion after results. Completed results refuse to retrain. No calibration, Validation or Hidden Test outcomes were evaluated, and no final candidate weights or intervals were created.

## Same-fold results

| Output | V2 refit RMSE | Ridge control RMSE | V5 search RMSE | Reduction vs V2 | Unit |
|---|---:|---:|---:|---:|---|
| Lightning front | 0.007187 | 0.007187 | 0.007187 | 0.0000% | µs |
| Lightning tail | 0.633297 | 0.633297 | 0.633297 | 0.0000% | µs |
| Lightning crest | 4.873002 | 4.819780 | 4.805382 | 1.3877% | kV |
| Switching peak | 1.739125 | 1.739125 | 1.738478 | 0.0372% | µs |
| Switching tail | 25.607145 | 25.607145 | 25.607145 | 0.0000% | µs |
| Switching crest | 3.591840 | 3.526777 | 3.508980 | 2.3069% | kV |

The mean of six tolerance-normalized RMSE values decreased **1.0921%** versus V2. The matched Ridge control search achieved **0.8578%**, leaving **0.2363%** lower error for the complete envelope search compared with that control. These relative comparisons cannot be added to the original V1 or V2 gains.

The complete search retained the V2 fallback in 19 of 30 outer fold/output choices; it selected quantile-center models in four and minimax models in seven. The modest gains were concentrated in crest. The experiment finished locally in **7.86 seconds**, with **$0 cloud spend**.

## Decision and limitations

The declared promotion rule was at least 5% macro improvement and no physical-unit target RMSE regression over 2%. The first condition failed. This remains an unpromoted development study, and the active synthetic benchmark is unchanged.

Previously explored features, reused outer folds, and historically selected V2 parameters limit interpretation even though individual fitting and selection remain nested. The result is not an independent final-test estimate or evidence of laboratory performance. Minimax estimators can be sensitive to outliers; a favorable synthetic trend estimate does not establish robustness to laboratory noise, clipping, unmodeled topology or different stock settings. Twelve configurations do not exhaust all possible models, but the observed gain does not justify a larger post-result sweep or cloud training on this small dataset.

The 33 older model/experiment artifacts retain their registered hashes. Tests recompute recorded errors from saved out-of-fold predictions, audit all inner/outer IDs, reject forbidden outcomes before numeric parsing, verify physical-unit scaling and frozen transformations, and prevent completed experiments from silently retuning. The default support guard, circuit equations, optimizer and previous evidence are preserved.

Evidence: `artifacts/experiments/v5/protocol.json`, `summary.json`, `oof_predictions.json`; runner: `backend/app/ml/experiment_v5.py`; tests: `tests/test_accuracy_v5.py`. `make experiment-v5` leaves existing results untouched. A new experiment requires a separate version and registered protocol.

The practical accuracy work accompanying this study addresses three demonstrated sparse-capture false passes and adds measured nominal-decision errors to the existing review. See `capture_resolution_review.md` and `measured_decision_review.md`. These changes improve measurement evidence handling; they do not create laboratory measurements.
