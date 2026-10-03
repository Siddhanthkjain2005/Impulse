# Laboratory evidence

`/laboratory-evidence/` reads every saved trial, not only the last 50. It separates **SYNTHETIC BENCHMARK**, **GENERATED DEMO**, **MEASURED LAB** and unknown legacy sources. With no measured captures it displays an intentional readiness state, never a laboratory accuracy percentage.

Uploads retain original bytes and SHA-256, selected run/candidate, units, baseline, onset, acquisition review and a normalized `evidence` record. Capture timestamp, instrument and operator notes are optional multipart fields. Unknown values remain null. Existing `generated_stress_test` records map to `generated_demo` in the unified view without rewriting history. Embedded synthetic/generated provenance defeats a measured checkbox. Untagged origin remains an operator assertion; this is not instrument authentication.

Readiness rechecks capture quality, original bytes, prediction-before-upload order, duplicates and calibration sources. Counts are grouped by impulse, profile, layout and model. A duplicate or calibration-source capture cannot count as an independent shot. A missing calibration audit conservatively blocks readiness. Eligibility is not an accuracy result.

For evaluation, save predictions first, upload real captures, then select 3–100 distinct shots in Trial calibrator. The existing `/api/evaluations` workflow independently checks every applied calibration ancestor, raw hashes, numerically equivalent duplicates and captured rules. It reports separate MAE/RMSE/MAPE/tolerance-normalized RMSE and false-PASS/FAIL denominators for physics, original model and saved prediction. The new highest evidence level requires an intact evaluation for the exact saved run/candidate. No cross-layout or cross-model transfer is inferred.

Generated demos may exercise scoped calibration, but cannot establish measured calibration or external accuracy. Tests use isolated generated fixtures labeled as measurements solely to test admission logic; they do not populate a live laboratory benchmark.
