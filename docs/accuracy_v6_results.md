# Switching crest study and friend-commit review — 7 October 2026

## What 5/6 means

Frozen V1 has lower RMSE than physics for all six outputs and lower RMSE than the exact workbook kNN for five. Switching crest is the exception: **4.120903 kV** versus **3.929275 kV**, or **4.876916% higher error**. These are preserved synthetic final-test results, not a count of successful laboratory shots. Exact workbook kNN also uses all official Train rows while V1 reserved some Train rows for calibration.

The existing optional V2 already has lower RMSE than matched exact kNN on all six outputs in its separate nested Train development study. Its Switching crest scores are **3.640386 kV** versus **3.870069 kV**. This development comparison cannot replace the saved V1 test or establish new 6/6 final-test performance.

## Fixed V6 comparison

The focused study searches only Switching crest. It predicts a relative correction using total capacitance, inductance and their product, with compact Ridge, cubic spline Ridge, kernel Ridge and trend-plus-local-mean candidates. Some candidates weight the relative fit by squared physics crest to target physical-unit error. Both historical V2 and exact workbook kNN compete as fallbacks. Every transformation and model is fit inside the corresponding inner folds.

The fixed grid contains 15 configurations and two blend weights. Three-fold inner selection replaces the better baseline only when inner physical-unit MSE improves by at least 2%. Five-fold outer comparisons repeat at seeds 191, 293 and 397; other-regime held rows are also excluded from kNN training. Only the original 560 Train fit IDs per impulse type are numerically parsed. Calibration, Validation and Hidden Test outcomes remain excluded. Protocol registration precedes this fixed run; prior exploratory crest studies and their outcomes are preserved under `artifacts/experiments/v6/exploratory/`.

| Outer fold arrangement | V6 RMSE, kV | V2 refit RMSE, kV | Exact kNN RMSE, kV | Reduction vs V2 | Reduction vs kNN |
|---|---:|---:|---:|---:|---:|
| Seed 191 | 3.481508 | 3.557543 | 3.856566 | 2.1373% | 9.7252% |
| Seed 293 | 3.491968 | 3.538337 | 3.844687 | 1.3105% | 9.1742% |
| Seed 397 | 3.493004 | 3.560943 | 3.809767 | 1.9079% | 8.3145% |
| Combined repeated predictions | **3.488831** | **3.552288** | **3.837058** | **1.7864%** | **9.0754%** |

V6 beats both baselines in **14 of 15 outer folds**. Its 95th-percentile absolute error is **5.981711 kV**, versus V2's **6.362397 kV**; maximum recorded absolute error is **7.861861 kV**, versus **9.125415 kV**. All values refer to these development rows. The repeated predictions are three predictions per original shot, not 1,680 independent shots, and maxima are sample maxima rather than bounds.

The preregistered gate requires at least **2% lower crest RMSE versus both baselines in every seed** and wins in at least 10 of 15 folds. Seeds 293 and 397 miss the V2 threshold, so **the gate fails**. No final serving weights or calibration intervals were created. V1 stays frozen; optional V2 stays available. No new final-test, laboratory or complete-optimizer accuracy claim follows.

The compact fixed spline looked stronger in an earlier exploratory comparison than the more conservative nested selection. This distinction is preserved rather than presenting a selected exploratory score as independent evidence. Even fresh random folds reuse previously explored data. [Scikit-learn's nested-CV guidance](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html) explains why model selection must occur within training folds; nested folds do not erase prior dataset exposure.

Run `make experiment-v6 PYTHON=python3` to read the frozen-result stopping message. The runner refuses to overwrite completed results. The full protocol, per-fold selections, training/held IDs and out-of-fold predictions are in `artifacts/experiments/v6/`. Tests independently recompute reported metrics and check split separation and protected hashes.

## Friends' changes reviewed and integrated locally

Merged main `047841f` adds evidence provenance, hardware/test-object checks, saved experiment history, Judge Mode and release verification. The unmerged branch `feat/engineering-hardening` at `efde726` adds stable RC handling, a better tiny-inductance policy, scale-aware crossing roots, actual solved-voltage/energy stage eligibility, exact inference batching and CPRI/circuit defaults. Both preserve the original model and source bytes; neither attempted a sixth-output model improvement.

Two additional correctness issues were reproduced during this review:

- A historical generated capture with a measured operator label could create a calibration that retained the measured label. New creation now persists the conservatively classified source. Applying an existing calibration rechecks its source, raw CSV and acquisition quality; Judge Mode corrects old evidence labels in a temporary view while preserving saved predictions and immutable records. Missing/changed origin evidence prevents application and remains unverifiable. API regressions cover both demo aliases, intact measured declarations, synthetic-benchmark rejection and old saved calibrations.
- On macOS, an extreme circuit returned a finite negative slow pole with about **43% tail-time error**: approximately 4.9433 s instead of the independently verified 8.66434 s. A scaled characteristic-polynomial check now rejects unresolved RLC poles. Tests accept independently accurate results across platforms and reject incorrect stable-looking poles. A 64-case ordinary circuit comparison preserved all returned values, waveforms and diagnostics.

The first local integrated baseline retained a failing platform-dependent physics assertion in `artifacts/qa/seventh_october_baseline.xml`; it remains as historical evidence. The final suite/build and source-preservation checks are recorded separately. No website preview or cloud resources were used in this update.

Final verification: **301 tests pass**, frontend typecheck/static build pass, 23 local referenced assets are present and served, fresh-database external-network-denied smoke passes, and all 45 protected hashes match. The intermediate V5 integrity-test failure is also retained; its assertion now checks every originally registered artifact without treating a separately named later study as a modification of V5. See `artifacts/qa/seventh_october_verification.json`. A newly executed browser or disconnected-laptop rehearsal is not claimed.

## Next evidence

The current app's primary CPRI physical profile uses circuit physics; workbook residual ML does not have validated transfer to it. A stronger synthetic crest model alone does not improve that physical-generator prediction. Confirm inventory and hardware assumptions, retain circuit-limit failures, and obtain independent waveform outcomes when available before changing real-equipment accuracy claims. Do not reuse the exposed test to turn the saved score into 6/6.
