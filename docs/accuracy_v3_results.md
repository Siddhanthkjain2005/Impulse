# V3 accuracy search and model-agreement improvement

Updated 1 October 2026. V1 remains the default and V2 remains optional. **V3 was not promoted.**

## Additional ML search

Thirty Ridge, polynomial, spline, Huber and RBF kernel configurations were evaluated with 50%/100% blends and the historical V2 fallback. The predefined gate required at least 5% improvement in mean tolerance-normalized RMSE and no output regression above 2%. V3 achieved **1.0339%**, below the gate. No production weights changed.

Only the original 560 Train-fit rows per impulse type were used. Five outer folds contain three-fold inner model selection. The historical V2 comparator uses previously selected settings; feature choices had prior development exposure. This is a development comparison, not an unbiased generalization estimate. Calibration, Validation and Hidden Test outcomes were not evaluated. The saved source, dataset and frozen V1/V2 hashes preserve the experiment record.

| Regime | Output | Historical V2 refit RMSE | V3 search RMSE | Error reduction |
|---|---|---:|---:|---:|
| Lightning | Front / peak (µs) | 0.007187 | 0.007227 | -0.561% |
| Lightning | Tail (µs) | 0.633297 | 0.633297 | +0.000% |
| Lightning | Crest (kV) | 4.873002 | 4.790585 | +1.691% |
| Switching | Front / peak (µs) | 1.739125 | 1.739125 | +0.000% |
| Switching | Tail (µs) | 25.607145 | 25.607145 | +0.000% |
| Switching | Crest (kV) | 3.591840 | 3.523261 | +1.909% |

The macro percentage compares the means of six tolerance-normalized RMSE values; it is not the arithmetic mean of the six percentages above. The study took 7.28 seconds locally. Cloud spending: $0. A larger model or more cloud compute is not supported by these results. Further external accuracy claims require new independent outcomes, especially real waveforms and varied resistor settings.

Reproduction entry point: `python -m backend.app.ml.experiment_v3`. Completed evidence is immutable; the runner exits when its saved summary exists. Full protocol, fold selections and out-of-fold predictions are in `artifacts/experiments/v3/`.

## Search that requires two-model agreement

Use **G · Lightning · agreement across models**, or **Find settings passing both models** on a failed circuit cross-check. This broadens stock-network candidates, balances the raw workbook/circuit crest predictions through charging voltage, and checks final reference and circuit outputs at the same settings. Hardware and challenge limits remain unchanged. Ranking uses both nominal checks, sampled agreement, reference interval containment, then weighted cost. The bounded shortlist does not prove a global optimum.

At the default 1425 kV case the selected configuration is 9 stages, 196.785 kV/stage, 40 Ω front and 23.823529 Ω tail per stage. Stored energy is 522.779 kJ under the workbook profile's derived ratings.

| Metric | Reference | Independent circuit | Allowed |
|---|---:|---:|---:|
| Front (µs) | 1.003356 | 1.416773 | 0.84–1.56 |
| Tail (µs) | 49.751999 | 52.927774 | 40–60 |
| Crest (kV) | 1452.273304 | 1397.726696 | 1382.25–1467.75 |

Both nominal checks pass, as do 32/32 sampled ±5% parasitic scenarios. This is finite simulation evidence, not laboratory accuracy or a success probability. ML corrections are disabled because these hardware settings are outside training support. The uncertainty envelope remains **MARGINAL**, with no calibrated coverage claim.

The five-case diagnostic improves both-model nominal agreement from failure to pass in the default Lightning, higher-load Lightning and 500 kV Lightning cases. The tested constructible Switching and PDF Lightning cases still fail agreement and remain diagnostic alternatives. PDF stock counts are explicitly assumed. This small set includes the development case and must not be reported as test-set accuracy. Reproduce with `python -m scripts.check_model_agreement`; complete settings and outcomes are saved in `artifacts/qa/model_agreement_diagnostic.json`.

A review also corrected scenario calibration: a one-shot bias now applies only when each scenario stays within its saved 1% input scope. Other scenarios use uncalibrated predictions, and the audit records both counts.
