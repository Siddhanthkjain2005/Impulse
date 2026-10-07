# Accuracy progress and the next independent check

## Latest crest follow-up — 7 October 2026

V7 compares 12 fixed multi-input spline/envelope/quantile/Bayesian configurations in three new nested fold arrangements. Switching-crest repeated-development RMSE is **3.494530 kV**, versus historical V2 refit's **3.586253 kV** and matched exact kNN's **3.918090 kV**: 2.5576% and 10.8104% lower error respectively. It wins 14/15 folds, but seed 607's 1.9599% reduction versus V2 misses the fixed 2% gate. The compact spline control is slightly better overall, so more complexity is not justified. No serving artifacts or earlier scores changed. Read `accuracy_v7_results.md` for the complete failure and scope.

Optional V2's existing 6/6 development comparison remains separate from V1's 5/6 saved synthetic final test. Further independent accuracy evidence requires unused outcomes, not another random split of these explored rows. The owner will ask their friend whether new data exists; no new files have been supplied. The existing capture/evaluation workflow below is prepared for independent shots with recorded setup metadata.

## Focused continuation — 7 October 2026

Frozen V1 is still 5/6 versus exact workbook kNN and 6/6 versus physics. Existing V2 development CV is 6/6 versus matched kNN; these are separate evaluations. A new repeated nested Switching-crest study records RMSE 3.488831 kV versus V2 refit's 3.552288 kV and exact kNN's 3.837058 kV: 1.7864% and 9.0754% lower error respectively, with 14/15 fold wins. It misses its fixed 2%-in-every-seed gate and creates no serving weights. See `accuracy_v6_results.md`. The saved final test and all earlier experiment artifacts remain preserved.

The current circuit additionally rejects an independently demonstrated inaccurate stable-looking pole, and new calibration creation preserves conservative generated provenance. These are correctness fixes, not a new measured-accuracy result. The older summary below retains its dated scope.

Updated 3 October 2026. Numerical source: `artifacts/models/hidden_test_evaluation.json`. The active model remains frozen V1; no new final-test predictions were generated for this review.

## Recorded improvement so far

On the supplied synthetic final test, V1 reduces the mean of the six tolerance-normalized RMSE values by **41.9265% against physics alone**. The calculation is `100 × (1 − mean(hybrid normalized RMSE) / mean(physics normalized RMSE))`, with equal weight for the three outputs of each impulse type. This is an error reduction, not a pooled accuracy percentage.

| Impulse / output | Physics RMSE | V1 RMSE | RMSE reduction | V1 mean absolute percentage error |
|---|---:|---:|---:|---:|
| Lightning front, µs | 0.010290 | 0.007379 | 28.29% | 0.523% |
| Lightning tail, µs | 0.731650 | 0.636808 | 12.96% | 1.056% |
| Lightning crest, kV | 11.600188 | 5.490493 | 52.67% | 0.327% |
| Switching peak, µs | 2.170961 | 1.749183 | 19.43% | 0.591% |
| Switching tail, µs | 32.497808 | 26.783469 | 17.58% | 0.930% |
| Switching crest, kV | 8.234004 | 4.120903 | 49.95% | 0.339% |

The separate optional V2 achieved **5.3656% additional macro development improvement** versus a matched-row historical V1 refit. Lightning tail was 0.5192% worse. Its nested Train CV has prior feature-development and comparator-selection exposure; it is not an independent final-test gain. V2 is not the default. See `accuracy_v2_results.md` for the complete protocol.

V3 achieved only **1.0339% development improvement versus a historical V2 refit**, below the declared 5% promotion gate. It was not activated. These percentages refer to different comparisons and cannot be added together.

V4 tested 48 shared/partially pooled model configurations across both impulse types, with both regimes held out inside every shared fit. No candidate cleared the inner selection gate, so all six outputs retained the historical V2 refit and macro additional development improvement was **0.0000%**. It was not promoted. See `accuracy_v4_results.md`; no new calibration, Validation or Hidden Test outcomes were evaluated.

V5 tested minimax envelopes, symmetric quantile centers and matched Ridge controls using only the original Train fit IDs. It reduced macro development error **1.0921%** versus the historical V2 refit, below the 5% gate; it was not promoted. Its gain over the matched Ridge control search was **0.2363%**. No calibration, Validation or Hidden Test outcomes were evaluated. See `accuracy_v5_results.md`.

Recent calibration, waveform alignment and evaluation-workflow changes improve the application and its evidence. They have not changed frozen model weights or established a further measured accuracy gain. The synthetic benchmark evaluates residual predictions before runtime support gating; it does not establish accuracy on arbitrary stock networks, different generators or actual laboratory shots. Agreement checks and passing software tests are separate evidence.

## Evaluate new measured shots without fitting them

The Trial calibrator now contains **Verify accuracy on new shots**. Select at least three distinct uploads labeled as actual laboratory captures. `POST /api/evaluations` scores the predictions stored in the original run before each capture upload; it does not fit, retrain, re-optimize or promote a model.

The review:

- Excludes synthetic demo uploads and rechecks acquisition quality.
- Requires unchanged original CSV bytes and rejects duplicate IDs, identical raw files and numerically equivalent normalized waveforms, including repeated exports with changed comments or units.
- Walks every applied calibration ancestor through its source trial and saved candidate. Any evaluation waveform found in that ancestry blocks the review, including when imported under another ID. Missing ancestry also blocks scoring.
- Requires the prediction and its calibration to predate the evaluation upload.
- Separates physics, the original model without the applied local bias, and the prediction actually saved with that bias. The saved prediction reflects runtime fallback and support restrictions.
- Groups scores by impulse type, profile/version, layout, solver/physics version and model version/mode. It records support status, inputs and counted hardware plans per shot and reports MAE, RMSE, MAPE and tolerance-normalized RMSE in their proper units. Negative improvement is retained.
- Saves the selected IDs, hashes, predictions, calibration ancestry and results as an immutable local audit record. Download the complete evidence JSON from the review panel.

The capture origin remains operator-labeled, and acquisition checks are heuristics. A small manually chosen sample is not an authenticated, randomized or statistically independent test. No confidence interval or probability of laboratory success is inferred. The tests for this workflow use isolated synthetic fixtures; they do not create a laboratory benchmark or populate live laboratory results.

## Highest-value next evidence

Lock the device, layout, instrument settings and resistor inventory first. Use one group of repeated shots to establish repeatability and develop a local correction. Save the corrected prediction, then capture a separate group of new shots to evaluate it. Keep those evaluation shots out of the calibration process when making that comparison. Include deliberate, documented changes to resistance and stage count in separate evaluation groups to investigate the missing hardware coverage.

Further heavy training on the same 2,000 synthetic rows cannot establish performance on unseen real equipment. Fresh outcomes and a locked evaluation procedure are required to verify the next improvement. No cloud resources or spending were used for this update; deployment remains deferred.


## Practical accuracy update on 3 October

Capture review now blocks unresolved peak neighborhoods and falling half-value brackets. Three isolated synthetic cases previously yielded nominal PASS after sparse sampling despite a failing dense reference. They now remain provisional and cannot calibrate or enter measured accuracy scoring. Raw/interpolated values remain unchanged. This is a demonstrated evidence-quality fix, not a new laboratory score; see `capture_resolution_review.md`.

The measured-shot review now reports true/false PASS/FAIL counts for physics, original and saved predictions, with explicit rate denominators. It retains worst-error shot IDs, separates stored envelope containment and uses each run's saved rules/hash. No absent outcome class is treated as proven zero risk. See `measured_decision_review.md`.

The official/supplied judging audit is in `judging_criteria_evidence.md`. No finale numerical weights were found. User requested no website previews for this update; verification is limited to automated checks and release validation.
