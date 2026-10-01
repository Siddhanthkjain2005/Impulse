# Supplied data and frozen model audit

All benchmark data is supplied synthetic data. Laboratory validation is pending. The frozen production models and previously saved Hidden Test evaluation were not changed or retrained by this audit.

## Findings that change how the product should be used

- All 2,000 supplied observations pass the challenge waveform limits. This dataset cannot demonstrate failure-detection sensitivity or a laboratory false-pass rate.
- The voltage support is narrow: Lightning approximately 1,350–1,500 kV and Switching approximately 950–1,100 kV. Hardware-valid requests elsewhere require physics fallback and an explicit support warning.
- All 1,000 Switching front resistances (9,370–21,810 Ω/stage) exceed 5,740 Ω/stage, the maximum obtained by putting every workbook front component in series. Those settings are impossible with the supplied workbook stock. Reference predictions cannot be presented as constructible recommendations.
- The dataset uses 3 µF/stage; the PDF machine uses 0.125 µF/stage. PDF stock quantities are unknown. Synthetic residual corrections are disabled outside the workbook profile. An explicit stock assumption is not a verified hardware inventory.
- The exact workbook formula reproduces the displayed case and all 1,400 helper distances/weights. Its recomputed Validation scores differ from the hardcoded published table; the unresolved source discrepancy is preserved in source reconciliation.

## Frozen per-target performance

The table compares the selected residual predictor before production OOD gating. Validation selects models and therefore has selection optimism. Hidden Test is the saved one-time evaluation after freeze. No hidden result changed the selection.

| Split | Regime / target | Physics RMSE | Exact kNN RMSE | Selected RMSE | Gain vs physics | Gain vs kNN |
|---|---|---:|---:|---:|---:|---:|
| Validation | Lightning Front/peak (µs) | 0.0100952 | 0.00822119 | 0.00733767 | 27.32% | 10.75% |
| Validation | Lightning Tail (µs) | 0.845853 | 0.730195 | 0.677424 | 19.91% | 7.23% |
| Validation | Lightning Crest (kV) | 11.7979 | 5.59329 | 5.29199 | 55.14% | 5.39% |
| Validation | Switching Front/peak (µs) | 2.45704 | 1.88741 | 1.79114 | 27.10% | 5.10% |
| Validation | Switching Tail (µs) | 30.4922 | 28.1525 | 25.8136 | 15.34% | 8.31% |
| Validation | Switching Crest (kV) | 8.431 | 3.95691 | 3.98124 | 52.78% | -0.61% |
| Hidden Test | Lightning Front/peak (µs) | 0.0102895 | 0.00800634 | 0.0073788 | 28.29% | 7.84% |
| Hidden Test | Lightning Tail (µs) | 0.73165 | 0.665816 | 0.636808 | 12.96% | 4.36% |
| Hidden Test | Lightning Crest (kV) | 11.6002 | 5.97851 | 5.49049 | 52.67% | 8.16% |
| Hidden Test | Switching Front/peak (µs) | 2.17096 | 1.86549 | 1.74918 | 19.43% | 6.23% |
| Hidden Test | Switching Tail (µs) | 32.4978 | 29.4239 | 26.7835 | 17.58% | 8.97% |
| Hidden Test | Switching Crest (kV) | 8.234 | 3.92928 | 4.1209 | 49.95% | -4.88% |

The selected hybrid improves all six Hidden Test outputs against physics; five of six improve against exact kNN. Switching crest RMSE is 4.1209 kV versus exact kNN 3.9293 kV (4.88% worse). Preserve this result: do not claim uniform improvement.

Exact kNN uses all 1,400 Train rows. Advanced models fit 560 rows per regime and reserve 140 per regime for calibration. Exact kNN is excluded from calibrated model selection because its fitted reference uses those calibration rows; comparing its raw benchmark is still useful, but its data budget differs.

Pooled exact-kNN Validation R² is approximately 0.9999 for front and 0.9997 for tail, but within-regime R² is much weaker: Lightning tail 0.2791; Switching peak 0.3395; Switching tail 0.0790. The separation of 1.2/50 and 250/2500 timescales drives the pooled result. Headline metrics must remain per regime.

## Splits, features and leakage checks

The source has 2000 rows and the original 22-column schema: Train 1,400, Validation 300, Hidden Test 300, balanced 700/150/150 within each regime. Missing values: 0. Duplicate IDs: 0. Duplicate full records ignoring ID/Split: 0. Repeated input signatures crossing splits: 0.

Fit and calibration IDs are disjoint, collectively cover official Train, and contain no Validation or Hidden Test ID. Features exclude observed values, residual targets, ID and Split. Derived total capacitance is checked. Source residuals equal observed minus physics to numerical precision. Physics crest equals requested voltage by definition, so its perfect correlation is expected; it is not an independent learned physical quantity.

No claim of causal independence follows from these structural checks: all outcomes were generated synthetically by an unavailable generator script. Source-generation bias and correlations cannot establish laboratory generalization.

## Uncertainty review

The calibration partition is held out from fitting, hyperparameter CV and Validation model selection. Selecting a model using the separate Validation set does not itself contaminate calibration. Calibration residuals are computed only after the per-target selection.

The 90% conformal statement is marginal, per target, under exchangeability with the supplied synthetic distribution. It is not simultaneous coverage of all three outputs, conditional coverage among supported inputs, coverage of an optimizer-selected candidate, or laboratory coverage. The quantile implementation is slightly conservative: with 140 calibration rows, its higher-interpolated quantile can select one order statistic above the minimal finite-sample rank.

Production uses the calibrated widths only with full residual weight. Partial trust or another profile uses an explicitly uncalibrated widened sensitivity envelope. Any robust-PASS statement means the returned interval lies inside the challenge limits; it is not a measured safety probability. OOD distances depend on scaled features and the fit partition; a feature range breach greater than 20% disables the correction. Constant features form especially strict boundaries: Lightning tail is always 25 Ω/stage in the data.

Saved ungated marginal Validation coverage (front, tail, crest): Lightning: [0.88, 0.9066666666666666, 0.9266666666666666]; Switching: [0.9133333333333333, 0.9466666666666667, 0.9]. The HTML report separately shows coverage of the deployed gated output. These empirical proportions do not upgrade the theoretical guarantee.

## Model-selection limitations and next-version work

Five advanced families were compared: Ridge, scaled SVR, Random Forest, Extra Trees and HistGradientBoosting. Three-fold CV occurs inside the fit partition. Validation selects one model per target. Optional external boosting libraries were not needed.

The frozen CV scorer averages MSE in original output units, despite scaling the training targets. Larger-unit targets therefore dominate hyperparameter selection (crest for Lightning, tail for Switching). A future version should preregister tolerance-normalized or per-target CV, nested selection and a new untouched evaluation set. Do not change this version using the exposed Hidden Test. Add uncertainty for model-selection variability, joint intervals and calibrated decision risk only after suitable data exists.

Stored Hidden Test latency is unavailable, not zero. Validation latency is batch timing from the training run and excludes API/optimizer overhead. Small differences between models have not been significance-tested.

## Engineering stress tests remain separate

Stress cases carry source_type=generated_stress_test and never enter training or official model benchmarks. The 120 generated circuit scenarios contain 23 reference PASS cases, 2 circuit PASS cases and 21 reference-PASS/circuit-FAIL disagreements. These are model disagreements between unvalidated simulators, not measured false passes. The report must not turn 82.5% agreement into a laboratory accuracy claim.

## Reproduce

Run `python3 -m backend.app.data.audit` to rebuild the standalone HTML and JSON audit without modifying frozen models. Run `python3 -m pytest tests/test_data_ml.py tests/test_workbook_parity.py -q` for data/model isolation and parity checks.

Sources: original workbook preserved in data/source; full cell/formula snapshot in artifacts/reference_workbook_snapshot.json; schema manifest in data/processed/manifest.json; profile definitions in config/generator_profiles.json; frozen metrics in artifacts/models/registry.json and hidden_test_evaluation.json. Exhaustive feature distributions, correlations and setting combinations are in artifacts/data_audit.json; reports/data_audit.html provides the readable tables and charts.
