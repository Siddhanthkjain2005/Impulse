# Train-only residual signal review

Date: 1 October 2026. Source: `artifacts/experiments/train_signal.json` and the associated diagnostic run notes. This review uses the existing diagnostic results; it performs no new training and changes no production model.

## Scope and interpretation

The diagnostic analyzes 560 fit rows per impulse type, selected from official Train by the seeded 80/20 split with `random_state=41`. The other 140 Train rows per type remain unused calibration data. Validation and Hidden Test outcomes were not used. All 560 complete input signatures within each type are distinct.

The candidate results are exploratory five-fold out-of-fold (OOF) comparisons. They show whether simple input-derived structure can predict supplied synthetic residuals. Selecting the lowest-error candidate from these same OOF results introduces selection optimism. These numbers are neither a newly untouched test nor performance of the current deployed model. The follow-up nested experiment should evaluate the complete inner selection procedure, as described in `docs/accuracy_v2_protocol_review.md`.

## What the diagnostic found

| Impulse / output | Physics-only RMSE | Lowest diagnostic OOF RMSE | Reduction | Candidate |
|---|---:|---:|---:|---|
| Lightning front, µs | 0.010155 | 0.007213 | 29.0% | Minimal mechanistic relative Ridge |
| Lightning tail, µs | 0.806883 | 0.634760 | 21.3% | Minimal mechanistic relative Ridge |
| Lightning crest, kV | 11.200052 | 4.849169 | 56.7% | Engineered relative Ridge |
| Switching peak, µs | 2.437427 | 1.739601 | 28.6% | Minimal mechanistic relative Ridge |
| Switching tail, µs | 32.659361 | 25.758230 | 21.1% | Minimal mechanistic relative Ridge |
| Switching crest, kV | 8.086987 | 3.583077 | 55.7% | Engineered relative Ridge |

Both relative Ridge candidates use `alpha=1` in this diagnostic. “Relative” means the model learns residual divided by the corresponding physics output and rescales to the physical quantity. Constant residual corrections offer little gain: their RMSE remains near physics-only RMSE. Raw Ridge already captures much of the structure. The engineered interaction improves crest most; degree-two polynomial models did not improve the best timing candidates in this exploratory comparison.

These reductions are against physics on the same diagnostic rows. They do not establish a gain against frozen V1, and should not be compared to a V1 Hidden Test score from different rows and a different protocol.

## Useful input structure

Front/peak residuals correlate positively with total capacitance: Pearson correlation is approximately 0.55 for both types. They correlate negatively with inductance, approximately −0.44 for Lightning and −0.46 for Switching. Tail residuals correlate with load capacitance at approximately +0.62 in both types.

Crest residuals have a stronger association with the derived `L_C_product` interaction than with inductance alone: approximately −0.83 in Lightning and −0.82 in Switching, compared with approximately −0.65 and −0.66 for inductance. An inductance–capacitance interaction is therefore a concrete candidate for a compact, interpretable residual model.

These are synthetic-data associations. Correlated quantities such as total capacitance, its components, RC time scales and the physics outputs can redistribute Ridge coefficients. Coefficients expressed per training standard deviation are descriptive within this fit set, not measured physical sensitivities or causal effects. Keep transformation fitting and feature selection inside training folds in the next experiment.

## All fit settings lie on the calculator's selected-setting surface

The diagnostic run reported that every fit row reproduces the workbook calculator's selected stage count, stage charge, front resistance and tail resistance. An independent deterministic check of the saved fit IDs confirms this for all 560 Lightning and all 560 Switching rows. Stage counts and resistances match exactly; stage-charge differences are at most approximately 5.7 × 10⁻¹⁴ kV, consistent with floating-point representation.

This is a major support limit. The supplied outcomes cover the settings produced by the calculator for sampled inputs; they do not independently vary resistance or stage count at otherwise fixed conditions. A model can interpolate that selected-setting surface without learning what happens when an optimizer changes settings away from it.

The fit ranges illustrate the restriction:

| Setting | Lightning fit | Switching fit |
|---|---:|---:|
| Requested voltage, kV | 1,350.041–1,499.658 | 950.296–1,099.958 |
| Stages | 8–10 | 6–7 |
| Front resistance, Ω/stage | 30–65 | 9,370–21,810 |
| Tail resistance, Ω/stage | 25, constant | 1,195–1,200 |

The broader source audit also identifies the Switching front settings as exceeding the supplied workbook stock's all-series bound. A residual model must not turn these source settings into supposedly constructible hardware recommendations. Preserve stock checks and physics fallback; neither a favorable synthetic CV score nor more training compute validates new resistor combinations, a different stage capacitance or a different generator profile.

## Remaining error and possible random jitter

For the selected diagnostic candidates, the Jarque–Bera normality-test p-values of signed OOF errors range from roughly 8 × 10⁻⁸ to 1 × 10⁻⁵. The run notes describe these remaining errors as relatively flat and bounded, rather than Gaussian. This is consistent with a possible synthetic random-jitter remainder after removing smooth input structure.

That interpretation is a hypothesis, not identification of the source generator or an irreducible error floor. Normality rejection does not prove uniform jitter; selected-model errors also include approximation error, omitted features and correlations induced by reused folds. The source generation script and repeated observations at identical settings are unavailable. The JSON does not preserve kurtosis values, so no exact uniform-distribution claim is made here.

The saved nearest-pair semivariance quantities are explicitly labeled `not_noise_floor`. Nearest rows have different inputs, so their outcome differences contain input effects as well as any random variation. Additional compute can improve approximation, but cannot remove genuinely unobserved variation or establish laboratory accuracy.

## Consequences for the next accuracy experiment

Use compact mechanistic relative Ridge candidates in the preregistered nested search; compare them against the same-fold V1 refit and exact workbook kNN. Keep the 140 calibration rows per type separate. Evaluate each output separately and report physical-unit and tolerance-normalized errors.

Add a distinct support diagnostic for deviations from calculator-selected settings. Its outcomes must come from independent measurements or explicitly labeled simulation, rather than invented residual labels. Keep simulated circuit disagreement outside official predictive benchmarks.

The highest-value new evidence is repeated reduced-voltage laboratory shots at confirmed constructible settings, including deliberate changes in resistance and stage count. That would separate repeatability from model error and test whether the correction transfers beyond the calculator's selected settings.
