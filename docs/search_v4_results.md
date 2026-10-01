# More complete hardware search and numerical verification

Updated 1 October 2026. This update improves engineering search, numerical precision and verification. Frozen V1/V2/V3 evidence and the challenge thresholds remain unchanged. No new supervised training or cloud resources were needed.

## What changed

- Search now includes all generated series/parallel trees through four components, through six components for catalogs with at most three values, and identical parallel banks up to declared stock and the component limit. Four 520 Ω resistors can now form 130 Ω; four 22000 Ω resistors can form 5500 Ω. Counts are retained in every intermediate tree and independently checked from the returned topology. Allowed physical mounting and pulse ratings are still unverified.
- Expanded target neighborhoods retain the earlier choices. During development, new close-by values crowded out an older simpler construction; this was corrected before the final check. The initial study is preserved separately from the final study. This remains bounded search, not exhaustive optimization over every possible topology.
- Circuit thresholds use bracketed roots on the continuous modal waveform. Plot-grid interpolation no longer determines the final 30%, 90% or 50% crossing metrics. Independent charge/current time-domain integration checks both Lightning and Switching at a relative tolerance of 2e-7. This is numerical consistency, not measured circuit accuracy. Circuit solver version is now v2; old circuit calibration records do not silently transfer to it.
- Every returned setting receives 128 fresh-seed Latin-hypercube scenarios and 16 boundary corners after ranking. Their results do not change selection or order. The original 32 search scenarios remain separate. The UI and reports show the limiting scenario, limits, inputs, passing counts and margin.
- The waveform chart overlays the independent circuit. Failed agreement cases also show disjoint raw charging-voltage ranges where charge adjustment alone cannot repair crest at that fixed network.

## Final seven-case development check

Default uncertainty is ±5% in object/divider/stray capacitance and inductance. Settings, efficiency and hardware tolerances are fixed. “Margin” is the minimum remaining fraction of an allowed half-range across checked metrics and models; negative means a violated limit. For agreement cases both models must pass; circuit-mode cases check only the circuit prediction. None of these fractions measures laboratory accuracy or continuous-range coverage.

| Development case | Post-ranking scenarios passing | Smallest margin | Uncertainty envelope |
|---|---:|---:|---|
| workbook lightning | 144/144 | 17.1% | MARGINAL |
| higher load lightning | 144/144 | 30.2% | MARGINAL |
| low voltage lightning | 144/144 | 21.3% | MARGINAL |
| constructible switching | 0/144 | -176.7% | FAIL |
| pdf lightning assumed stock | 0/144 | -151.0% | FAIL |
| pdf lightning circuit | 144/144 | 51.4% | MARGINAL |
| pdf switching circuit | 144/144 | 69.6% | MARGINAL |

The complete final check took 57.64 seconds locally. The nominal Lightning agreement setup remains 9 stages, 196.785 kV/stage, 40 Ω front and 23.823529 Ω tail per stage. It passes both nominal models and all 144 post-ranking cases; its uncertainty envelope remains MARGINAL. All distinct cases, precise settings and limits are in `artifacts/experiments/search_v4/final_summary.json`.

PDF Lightning circuit mode finds 12 stages, 170.710 kV/stage, 30 Ω front and 520 Ω tail: 1.236312/54.391642 µs and 1425 kV. PDF Switching circuit mode finds 11 stages, 142.837 kV/stage, 4165 Ω front and 22000 Ω tail: 243.439780/2468.016310 µs and 1050 kV. Both use explicitly assumed quantities of four per value per stage. These are circuit-mode results and must not be described as agreement with the workbook.

## Remaining failures are informative

The tested workbook Switching case and PDF Lightning agreement case still fail. A separate development search relaxed resistor discreteness and searched continuous raw-reference timing-feasible resistances across stage counts. It also failed to find agreement. The best maximum normalized deviations were about 2.88 and 2.23 respectively, where a value at most 1 is required. This is bounded numerical evidence suggesting model incompatibility; it is not proof of global infeasibility.

For the PDF profile, charging ranges at a fixed network can be disjoint between raw workbook and loaded circuit predictions. Changing charging voltage alone cannot fix that network. Do not silently change efficiency, capacitance, stock or tolerance rules to make a passing result.

## What would improve real accuracy next

The existing synthetic training records contain calculator-selected hardware settings rather than independent resistor interventions. More cloud training on the same records cannot supply missing response measurements. The strongest next evidence is confirmed physical stock and topology plus measured waveforms across hardware settings, loads and layouts, with a separately locked validation set. Continue to preserve exposed synthetic test results and report circuit agreement separately from ML prediction error.

Reproduction: `python -m scripts.check_final_search` preserves completed final evidence rather than overwriting it. The initial continuous diagnostic is in `scripts/check_search_v4.py` and its saved protocol. The standalone numerical and construction checks live in the regular test suite.
