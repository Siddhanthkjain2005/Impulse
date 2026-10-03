# Review capture resolution before using a measured result

Updated 3 October 2026. The measured-capture review now checks the acquired samples around the crest and falling half-value crossing. This prevents demonstrated sparse captures from becoming calibration inputs or measured accuracy evidence, while preserving their uploaded samples and extracted results for inspection.

## Application heuristic

The review requires the span between the immediate acquired neighbors of the sampled crest to be no greater than **25% of the selected challenge front/peak tolerance half-width**. It also requires the adjacent acquired samples bracketing the falling 50% crossing to span no more than **25% of the selected challenge tail tolerance half-width**. Existing rising-limb resolution and flat-crest checks remain in force.

For the POWERnext challenge rules version 1.0.0, these limits are:

| Impulse | Maximum peak-neighbor span | Maximum falling half-value bracket span |
|---|---:|---:|
| Lightning | 0.09 µs | 2.5 µs |
| Switching | 12.5 µs | 125 µs |

These are conservative application review preferences, not IEC requirements, instrument uncertainty estimates, or bounds on waveform error. A resolved neighborhood cannot prove there is no missed feature between samples. Instrument calibration, bandwidth, noise, ringing, clipping, baseline and onset determination still require laboratory review. In Lightning mode, the crest neighborhood check reviews acquisition of the amplitude reference used for the 30%, 90% and 50% thresholds; it does not redefine front time as time to crest.

The versioned quality report records the impulse type, rule ID/version, whether rules were supplied or defaulted, sample indices, acquired bracket endpoints, observed spans and their review limits. Explicit callers should pass the saved run's impulse type and complete rule record. Legacy callers can infer the impulse only from a recognized saved extraction definition. Unknown or conflicting context requires review; it never silently defaults to Lightning.

Unresolved captures remain available with their original interpolated metrics and nominal limit calculation. Those nominal results are provisional extraction results, not accepted measurement evidence. The quality report sets both `calibration_allowed` and `evaluation_allowed` to false. It does not repair, resample, smooth or alter a waveform or a saved prediction.

## Demonstrated false passes

The following isolated synthetic counterexamples sample smooth double-exponential reference curves. They are regression fixtures, not measured laboratory results or a new model benchmark. All three met the previous rising-limb and flat-crest checks. Their dense reference curves fail at least one challenge timing limit, but sparse interpolation produces a nominal pass at 1000 kV.

| Counterexample | Dense reference front/peak, tail, crest | Sparse extracted front/peak, tail, crest | Previous review | Updated review |
|---|---|---|---|---|
| Switching peak gap | 350 µs, 2500 µs, 1000 kV | 250 µs, 2579.087719 µs, 975.380096 kV | Usable; extracted nominal PASS | Review required; unresolved peak and half-value |
| Lightning tail gap | 1.2 µs, 35 µs, 1000 kV | 1.199320 µs, 50.402470 µs, 999.994823 kV | Usable; extracted nominal PASS | Review required; unresolved half-value |
| Switching tail gap | 250 µs, 1800 µs, 1000 kV | 248.829431 µs, 2132.889457 µs, 999.995451 kV | Usable; extracted nominal PASS | Review required; unresolved half-value |

The updated quality decision changes eligibility only. The displayed sparse metrics and their nominal arithmetic remain unchanged. For the first case, the crest neighbors span 760 µs. The falling half-value brackets span 500 µs, 80 µs and 2500 µs respectively across the three cases. The Lightning example also exceeds the conservative peak-neighbor limit.

## Verification

`tests/test_capture_resolution.py` reproduces all three examples and verifies raw arrays, rules and extracted metrics remain unchanged. Dense generated 1.2/50 and 250/2500 curves remain usable, including negative-polarity captures delayed by 700 µs with a 7 kV baseline. Additional tests verify supplied rule versions and limits, missing or conflicting impulse context and malformed rule records. API calibration and saved-prediction evaluation must both use this review with the captured run context.

The physics extractor, circuit solver, optimizer, model weights, final evaluation evidence and their frozen hashes are preserved. This change improves admission of measurement evidence; it does not establish new laboratory accuracy or resolve disagreement between the workbook equations and circuit model.
