# Accuracy V2 development results

Date: 1 October 2026. Source: `artifacts/experiments/v2/summary.json`. Experiment: `targetwise-physics-v2-experiment`.

The targetwise V2 search reduces the mean of six tolerance-normalized RMSE values by **5.3656%** against the matched-row V1 refit. Five outputs improve; Lightning tail RMSE is **0.5192% worse**. This passes the preregistered experimental gate of at least 5% macro improvement and no target more than 2% worse. **V1 remains the active model.** This is a synthetic-data development study, not newly untouched or laboratory validation.

## Comparable outer-fold results

The table uses the same held-out outer-fold rows for all predictors. There are 560 fit rows per type, with five outer folds and three-fold selection inside each outer training set. Model family, feature basis, relative versus absolute residual representation and hyperparameters are selected per output using inner tolerance-normalized MSE. Fitting and preprocessing occur within the corresponding training folds.

| Impulse / output | Physics RMSE | Exact kNN RMSE | V1 refit RMSE | V2 search RMSE | V2 change versus V1 |
|---|---:|---:|---:|---:|---:|
| Lightning front, µs | 0.010155 | 0.007861 | 0.007486 | 0.007221 | 3.5516% lower |
| Lightning tail, µs | 0.806883 | 0.707696 | 0.634878 | 0.638174 | **0.5192% higher** |
| Lightning crest, kV | 11.200052 | 5.442521 | 5.254785 | 4.864206 | 7.4328% lower |
| Switching peak, µs | 2.437427 | 1.895352 | 1.957611 | 1.743182 | 10.9536% lower |
| Switching tail, µs | 32.659361 | 27.507552 | 26.037649 | 25.707973 | 1.2662% lower |
| Switching crest, kV | 8.086987 | 3.870069 | 3.904028 | 3.640386 | 6.7531% lower |

V2 improves all six outputs against physics and the outer-fold exact kNN comparator. It does not improve every output against V1. Small differences have not been established as statistically significant; fold reuse, prior development and model selection limit the interpretation.

The macro calculation is `100 × (1 − mean(V2 normalized RMSE) / mean(V1 normalized RMSE))`. It is not the mean of the six percentage changes in the table. Timing errors are scaled by the challenge half-tolerances: 0.36 µs and 10 µs for Lightning, 50 µs and 500 µs for Switching. Crest errors are scaled per row by 3% of requested voltage. No pooled “percentage accuracy” is claimed.

## Limits of this comparison

The V1 comparator is refitted on the same current-type outer training rows; its existing fitted predictions are not reused. However, its family and hyperparameters were previously selected during V1 development, including hyperparameter selection on rows now serving as outer holdouts. V1 is also an eligible inner fallback. This prior selection exposure means the V1 comparison and fallback are not a fully nested, untouched baseline procedure.

The V2 candidate features were informed by exploratory diagnostics on the fit data before this run. Nested selection correctly separates the declared inner search from each outer fit, but does not erase that prior feature-development exposure. Report the result as **nested Train CV development evidence**, not an unbiased final accuracy estimate.

The outer-fold exact kNN comparator fits the 448 outer training rows of each type, using both types as required by the workbook's asymmetric distance and type-mismatch rule. Its predictions and the V1/V2 predictions are scored on identical held-out rows; no outer held-out labels enter those fits. During inner selection, kNN uses current-type inner training rows plus all opposite-type outer training rows. This gives it a larger opposite-type inner training budget than a synchronized inner split would. No current-type inner-held-out labels enter its fitting, but that budget difference must accompany claims of a matched inner comparison.

The source data are synthetic, follow calculator-selected settings and do not provide an independently varied setting grid or measured laboratory repeatability. A CV improvement does not validate different resistor networks, a different generator profile or stock feasibility. Preserve support restrictions, physical checks and explicit model-disagreement warnings.

## Frozen candidate and calibration

After the final inner searches on the 560 fit rows per type, the candidate model configuration and weights were frozen before opening calibration outcomes. The selected final models are:

- Lightning: relative minimal-mechanism Ridge for front (`alpha=0.01`), absolute minimal-mechanism Ridge for tail (`alpha=1`), and relative physics-interaction Ridge for crest (`alpha=1`).
- Switching: absolute minimal-mechanism Ridge for peak (`alpha=0.01`) and tail (`alpha=1`), and relative physics-interaction Extra Trees for crest (`min_samples_leaf=5`).

Calibration uses the separate 140 Train rows per type. One score per row is the maximum of the three absolute errors divided by fixed scales estimated from fit residuals. The joint 90% rectangular interval uses the **127th smallest** calibration score: `ceil((140 + 1) × 0.90)`. This is an exact finite-sample order statistic, with no interpolation.

| Impulse | Front/peak half-width, µs | Tail half-width, µs | Crest half-width, kV | Legacy Validation joint coverage |
|---|---:|---:|---:|---:|
| Lightning | 0.012841 | 1.033039 | 14.042427 | 90.67% |
| Switching | 3.132562 | 42.337866 | 10.410132 | 94.00% |

The empirical coverage values are diagnostics on the previously used Validation split, read after freeze. They did not tune the candidate or interval. They are not an independent test or a laboratory guarantee. The conformal claim requires exchangeability with the supplied synthetic distribution; it does not establish conditional coverage among supported inputs, OOD coverage, coverage after optimizer selection or measured-shot coverage.

## Reproducibility and production status

The controlled experiment completed locally in **54.96 seconds**. No cloud resource was created and no cloud credit was spent. Cloud deployment remains deferred. Additional compute was unnecessary for this candidate search.

The run verified that the V1 model, registry and saved Hidden Test artifact hashes remained unchanged. Hidden Test was not evaluated again. V2 artifacts are stored separately under `artifacts/experiments/v2`; passing the experimental gate does not activate them in the application.

The saved protocol SHA-256 is `9881369852ae43f5ca7aadc35544d9bbb3ab75236d5ebd447591fdaba0cd5b61`. The frozen candidate model SHA-256 is `024f5228fafbe6431d8252aec041c7a5c68642277fea6f1d7d3b9a005aee4105`. The summary, outer-fold selections, out-of-fold predictions and separate candidate artifacts preserve the experiment for review.

New independent organizer data or laboratory shots are required before claiming externally validated improvement or replacing the active model on that basis.


Benchmark scores evaluate residual predictions before runtime support and scenario gating. The optimizer can fall back to physics and widen its envelope; the saved errors are not a laboratory or complete-optimizer accuracy estimate.
