# Accuracy V2: independent experiment review

Date: 1 October 2026. This is a protocol and Train-only structural review, not a new performance claim. No production model, frontend or cloud resource was changed. V1 remains frozen. The existing audit document was inspected for structural limitations; its previously published Hidden Test numbers were not used to choose these recommendations. No Hidden Test predictions were run.

## What “accuracy” should mean for this challenge

The task predicts three continuous engineering quantities. Report six separate RMSE and MAE values: front/peak, tail and crest for each impulse type. Also report error divided by the challenge tolerance. A pooled R² or a single percentage accuracy hides the roughly 200-fold separation between Lightning and Switching time scales.

Use per-row normalized errors:

- Lightning: front error / 0.36 µs; tail error / 10 µs; crest error / (0.03 × requested Test_kV).
- Switching: peak error / 50 µs; tail error / 500 µs; crest error / (0.03 × requested Test_kV).

Report RMSE of these normalized errors, the median absolute error and 95th percentile absolute error. Calculate the crest denominator from each requested voltage, not mean observed crest. This is an engineering scaling convention; it does not prove that an error smaller than a tolerance guarantees waveform compliance.

No laboratory accuracy or failure-detection sensitivity can be inferred from the supplied synthetic data. The prior source audit establishes that its outcomes all pass the waveform constraints. Any additional circuit-generated stress cases remain separate diagnostics with an explicit generated source label.

## Highest-value defect to fix

V1 uses a transformed-target estimator, but its GridSearchCV score averages MSE after predictions are returned to the original units. Standardizing the targets inside the estimator therefore does not standardize the selection objective. Large numerical targets can dominate the choice of a shared hyperparameter.

Run six independent target searches. Select parameters by the target's normalized MSE, and show errors in physical units. Independent searches also permit a smooth crest correction and a different timing correction without forcing a common complexity. The physics calculation remains the fixed baseline; models learn residuals rather than replacing it.

## Preregistered data protocol

1. Read and hash the supplied CSV. Filter to `Split == Train` before any feature diagnostics or experiment. Assert 700 rows of each type, unique IDs, finite features and the original schema. Save the exact eligible IDs in an experiment manifest.
2. Preserve the existing deterministic 560 fit / 140 calibration split within each type if V1 comparability is important. Calibration rows must remain unused for feature choice, model search, family selection, early stopping, ensemble weights, error-scale modeling and promotion decisions.
3. On the 560 fit rows, use five outer folds and three inner folds. Synchronize the fold assignments between impulse types when fitting the exact workbook kNN on a combined training table. Outer rows never enter fit-time scaling, feature selection, fitting, early stopping or the inner search.
4. The inner loop chooses **the complete procedure**: model family, feature basis and hyperparameters. The outer loop scores the selected inner procedure on its held-out rows. Save every out-of-fold prediction, row ID, chosen family, parameters and run time.
5. Compare a V1 refit and exact kNN on the same outer fit budget. The existing trained V1 model must not predict Train rows for an alleged out-of-fold comparison: it already saw those rows. Refit its frozen family and parameters within each fold. The original workbook all-Train kNN can remain a clearly separate reference, but its larger data budget is not a matched experiment.
6. Choose the final deployable procedure with the preregistered inner search on all 560 fit rows. Freeze its model hash and manifest. Only then compute held-out calibration scores and intervals. Do not refit on calibration after doing so.
7. Keep official Validation as a **previously observed development diagnostic**. It selected V1 and therefore cannot become a newly untouched V2 test. Keep the exposed V1 Hidden Test closed: do not evaluate V2 on it or tune using its results. New genuine final evaluation requires new organizer-provided or laboratory data that has not influenced this work.

Nested CV estimates the performance of the whole search procedure, rather than a model chosen and scored on the same data. Selecting the best family using outer scores and reporting that same score as an unbiased final evaluation reintroduces selection optimism. [scikit-learn nested cross-validation documentation](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html)

Because these data were already explored during V1 development, even a careful new Train-only nested study is a development result. Label it “nested Train CV”; do not relabel it as an untouched test.

## Train-only structure checked in this review

The diagnostics below use only the 1,400 official Train rows. No target correlations or support decisions were computed on Validation or Hidden Test.

| Diagnostic | Lightning Train | Switching Train |
|---|---:|---:|
| Rows | 700 | 700 |
| Requested-voltage range, kV | 1,350.001–1,499.658 | 950.296–1,099.958 |
| Front resistance range, Ω/stage | 30–65 | 9,370–21,810 |
| Tail resistance range, Ω/stage | 25, constant | 1,195–1,200 |
| Front residual SD, µs | 0.009802 | 2.384429 |
| Tail residual SD, µs | 0.805448 | 32.299395 |
| Crest residual SD, kV | 10.908184 | 8.044796 |
| Rank of current 14 standardized model columns | 11 | 12 |
| Repeated raw-input signatures | 0 | 0 |

The current feature set contains deterministic dependencies: Physics_Crest_kV equals Test_kV; Test_kV equals stages × stage charge × efficiency to numerical precision; Total_C_pF equals the sum of three capacitances. Lightning tail resistance is constant. Target residuals equal observed minus physics to less than 10⁻¹² in the original units.

These relationships do not make the input-only physics features target leakage. They do make ordinary Euclidean distances count related information more than once, and make individual feature-importance values difficult to interpret. Compare a compact raw-input basis with the current physics-augmented basis **inside the inner folds**. Do not remove a physical input globally based on a pooled importance value. For explanations, permute coherent physical groups on held-out rows; independent permutation of stages and stage charge can create impossible settings. Correlated predictors can hide individual permutation importance. [scikit-learn correlated-feature example](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html)

Train-only absolute residual correlations suggest smooth structured correction is worth testing: load capacitance is correlated with tail residuals at approximately 0.62 in Lightning and 0.60 in Switching; inductance is correlated with crest residuals at approximately 0.65 and 0.66. These are descriptive associations, not causal or laboratory evidence.

## Candidate set and controlled compute budget

Use a small, preregistered candidate set rather than adding many families after inspecting scores:

| Candidate | Purpose | Proposed small search |
|---|---|---|
| Physics residual = 0 | Fixed baseline and safe fallback | None |
| Constant mean residual | Tests whether global bias is enough | None; mean fit only on fold training rows |
| Linear Ridge | Low-variance correction | alpha = 0.01, 0.1, 1, 10, 100, 1,000 |
| Degree-2 polynomial Ridge | Smooth interactions | Same alpha grid; raw inputs standardized before polynomial expansion |
| Additive splines + Ridge | Smooth per-input deviations | 3 or 5 knots; degree 2; alpha = 0.1, 10, 1,000 |
| RBF SVR | Smooth nonlinear correction | C = 1, 10, 100; gamma = scale, 0.05; epsilon = 0.05, 0.15 in standardized residual units |
| Extra Trees | Interaction baseline | 200 trees; leaf = 5 or 15; max_features = 0.7 or 1.0 |
| Histogram gradient boosting | Smooth tree correction | max_iter = 150; leaf nodes = 7 or 15; L2 = 1 or 10; learning rate = 0.05 |
| Exact workbook kNN, fold refit | Verifiable reference | Fixed workbook k = 7, asymmetric squared distance and tie rule |

Treat the two feature bases as part of the inner selection procedure. Drop constants within each fold. Keep all transforms inside a fitted Pipeline. Any residual scaling must fit only the fold's training targets. Log package versions, seeds, data and source hashes. If a learned kNN search is added, label it separately from the exact workbook reference.

With hundreds of rows and compact tabular models, a GPU is unlikely to provide the main benefit. A few thousand CPU fits are practical locally. Run and time one outer fold first; estimate the full wall time from that measurement. Parallelize one layer only, with each estimator using one thread, to avoid nested oversubscription. Reserve cloud spending for a measured bottleneck rather than increasing the search after viewing outcomes. This review creates no cloud resources. App deployment remains deferred.

Gaussian processes or large neural networks are optional future ablations, not a default need for this data volume. Added complexity earns its place through matched nested scores, stable intervals and readable diagnostics.

## Calibration versus more predictive training rows

Using 700 instead of 560 rows might improve point prediction, but fitting on the 140 calibration rows invalidates those rows as split-conformal calibration for the refitted model. Preserve the disjoint split for the first V2. Do not give a fully fitted model the old interval widths.

Compare fit-only learning curves at 25%, 50%, 75% and 100% of each outer training fold, with the same outer test rows. Show whether error is still dropping at the largest available fit budget. That is more useful than assuming additional compute or more synthetic rows will help.

For optional simultaneous 90% coverage of the three outputs, define fixed positive scales using fit rows only, then calibrate one score per row: `max_j(abs(error_j) / scale_j)`. With 140 calibration rows, use the 127th smallest score, corresponding to `ceil((140 + 1) × 0.90)`, without interpolation. Multiplying the calibrated score by each fixed scale gives a joint rectangular interval under the same synthetic exchangeability assumptions. Alternatively use three Bonferroni-adjusted marginal intervals, which will usually be wider. The conformal argument requires calibration separate from fitting and exchangeability; it supplies marginal guarantees, not automatic conditional, shifted-domain or optimizer-selected coverage. [Angelopoulos and Bates, conformal prediction tutorial](https://arxiv.org/abs/2107.07511)

One interval method should be preregistered. Choosing the narrowest calibrated interval method using its own coverage outcomes reuses calibration for selection. Report empirical coverage and width on development diagnostics separately; never treat sample coverage as a guarantee. Gated or shrunk predictions need calibration of that complete prediction rule. Reusing ungated calibration widths after OOD-dependent correction changes does not establish coverage.

## Noise-floor and support limits

There are no repeated raw input signatures in Train, and the synthetic generator script is unavailable. The irreducible noise variance is therefore not identifiable from this data. A flexible model's cross-fitted residual RMSE estimates its remaining predictive error; it mixes noise, missing features and model error. It must not be called the measured noise floor.

Useful diagnostics are learning curves, cross-fitted residual-versus-input plots, residual autocorrelation by input ordering and agreement between independently regularized smooth models. Nearest-neighbor label differences are confounded by input differences. Real repeated reduced-voltage shots at fixed settings are needed to estimate shot variability and measurement uncertainty.

Keep physics fallback outside source support. In particular, no amount of synthetic training establishes behavior at a new stage capacitance, arbitrary tail resistance or a hardware setting absent from the supplied generator's stock. Test grouped holdouts of resistor values and stages as explicit **support stress tests**, using fit-only data, in addition to random nested CV. They are harder and answer a different question; do not merge their errors into an in-distribution headline.

## Promotion criteria and honest presentation

Preregister these practical gates before running the search:

1. No split or preprocessing leakage; all fold predictions and hashes saved; production V1 and its Hidden result remain unchanged.
2. Compare all six outputs on identical outer rows against physics, matched-budget exact kNN and a fold-refitted V1. Publish improvements and regressions together.
3. Require at least a 5% macro reduction in tolerance-normalized RMSE against the matched V1 refit, with no individual target more than 2% worse. These are proposed engineering decision thresholds, not universal statistical constants. If a target cannot satisfy its non-regression gate, keep the refitted V1 target for that target; this fallback rule belongs inside inner selection and outer evaluation.
4. Report fold-to-fold variation and paired per-row error differences. A naive bootstrap of fixed out-of-fold rows conditions on already fitted folds and understates fitting/selection uncertainty. Label such intervals descriptive. A second preregistered outer seed can check stability, but reusing rows does not double the sample size.
5. Verify calibrated model latency and interval widths, OOD fallback, source parity and all existing engineering tests. No performance promotion overrides construction constraints or calibrated-profile boundaries.
6. A nested-CV improvement can justify a separately versioned experimental champion. A new untouched laboratory or organizer test is still required before claiming externally validated accuracy. Do not repeat or replace V1's exposed Hidden Test evaluation.

The strongest final demo combines three independently visible claims: exact workbook reproduction, measured improvement on a clearly named synthetic evaluation protocol, and physical/stock safeguards with explicit model-disagreement and support warnings. More compute cannot substitute for laboratory evidence or a constructible setting.
