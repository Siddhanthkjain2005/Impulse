# ImpulseTwin AI — engineering handoff and progress

## Latest authorized continuation — 7 October 2026

The owner requested trusted external data or properly generated data for six-output improvement. That work is complete as a bounded source review and separately registered independent numerical verification. Read `docs/trusted_waveform_data_search.md` and `docs/independent_simulation_results.md`. External sources lack the full compatible generator input/output mapping; do not invent units/settings or merge them into frozen residual training. Generated 240 cases pass 6/6 numerical agreement channels using independent Radau/BDF/refinement against the same assumed CPRI topology. This does NOT replace V1's saved 5/6-versus-kNN result or establish laboratory accuracy. All new numerical evaluation labels are now exposed. Preserve them; do not tune or overwrite the completed study. All V1–V7 hashes and models remain preserved.

Acquisition review v3 rejects incomplete falling limbs for calibration/evaluation while retaining original samples and metrics. The independently reproduced VTT/PTB step-response failure is covered by source regressions plus suitable LI/SI controls. Thresholds are application heuristics, not IEC certification. CPRI/circuit defaults and unsupported-profile ML gates remain unchanged. Latest checks pass 337 backend tests, Node 22 typecheck/build, 23 local assets and fresh-database external-network-denied smoke. Latest automated checks are in `artifacts/qa/october7_independent_verification.json`. User still defers cloud deployment and browser previews; $0 cloud was needed.

## Current continuation — 7 October 2026

The owner explicitly requested review of friends' commits and further improvement
of the sixth output. Work continues on `codex/switching-crest-review`, incorporating
main `047841f` and engineering hardening `efde726`. Separately registered Train-only V6 and V7 crest
studies are complete; both gates failed and their results are frozen. Do not rerun/tune
these completed studies or overwrite V1/V2–V7 evidence. No model weights, exposed
test outcomes or cloud deployment have changed. Read `docs/accuracy_v7_results.md`, `docs/accuracy_v6_results.md`
and the latest HANDOFF/PROJECT_STATE sections. The historical hardening scope's
no-new-fit instruction below applied to that earlier task; the owner's later
accuracy request authorized this separately recorded development study.

Preserve CPRI/circuit defaults, unknown stock/rating facts and generated/measured
provenance. New correctness checks reject unresolved RLC modes and conservatively
classify calibration sources. Current tests/builds are recorded separately from
the historical 6 October evidence. Website previews remain deferred to the owner.

Earlier continuation verification: 301 backend tests, Node 22 typecheck/build,
23 local asset checks, fresh-database/network-denied smoke and all 45 protected
hashes pass. See `artifacts/qa/seventh_october_verification.json`. Release packaging
now includes friends' hardening/release evidence and these separately recorded studies.
Latest checks pass 322 backend tests, Node 22 typecheck/build, 23 local assets
and fresh-database external-network-denied smoke. Latest branch refresh and checks are in `artifacts/qa/october7_remote_branch_review.json`
and `artifacts/qa/october7_envelope_verification.json`. All four published heads
were included; no new friend commits were found. No new independent files have
been supplied; the owner is checking with their friend.

## Current task — 6 October 2026

Work from `feat/engineering-hardening`, based on current main commit
`047841f587c4b00bc8d018d5174961d3356eebbf`. The user requests the final
optimization/hardening brief and a selective cleanup of the existing UI.
The detailed final evidence is in `OPTIMIZATION_REPORT.md` and
`artifacts/optimization_report.json`.

## Engineering constraints

- CPRI's problem-statement profile is the primary physical reference. Keep the
  15-stage/3 µF workbook benchmark separate from the 12-stage/0.125 µF machine.
- Preserve supplied sources, frozen V1 weights, saved Hidden Test results and
  V2–V5 experiment evidence. Do not tune on Hidden Test or fit another ML version.
- CPRI recommendations use circuit physics; workbook residual ML has no validated
  transfer to this profile. Unsupported corrections remain disabled.
- Unknown stock quantities, mounting and pulse ratings stay unknown. Demo stock
  is an explicitly labeled assumption, never a statement of laboratory inventory.
- Generated captures remain generated. Measured data is not a prerequisite for
  this hardening task and no laboratory-accuracy claim is created.
- Preserve the existing product scope, pages and seven Judge Mode steps. Improve
  readability and correct ambiguous labels/defaults. Do not deploy.

## Progress

- [x] Read the new brief and inspect current main; prior evidence work is merged.
- [x] Record protected file hashes, fixed runtime/profile snapshots and four
  bounded/exhaustive comparisons before backend changes.
- [x] Baseline frontend typecheck and production build pass on Windows.
- [x] Preserve the initial Windows native crash log; unchanged isolated baseline
  passes 237 tests with bounded native threads. The crash root cause is unproven.
- [x] Reproduce CPRI 1425 kV: 11 stages, 181.902790 kV/stage, 30 Ω/520 Ω,
  22.748430 kJ. No change to CPRI physical equations is justified.
- [x] Identify early circuit charge filtering that excludes valid inductive
  overshoot setups; retain actual solved voltage/energy limits.
- [x] Identify numerical edge cases in absolute tiny-L reduction and crossing
  tolerance; audit stable zero-inductance formulation before keeping a correction.
- [x] Profile pandas support-check/base-slicing overhead; preserve ML outputs,
  thresholds and scalar workbook rounding during optimization.
- [x] Implement focused fixes: circuit numerical policy v2.1, actual-charge stage
  eligibility, single-solve normalization, exact inference batching, energy limits.
- [x] Add 26 targeted regressions; all 263 backend tests pass. Four warnings:
  existing pytest-option/Starlette notices and two Windows cache permissions.
- [x] Preserve all ranked settings/metrics in the three pipeline comparisons;
  4,096 inference outputs exactly match original code. Four exhaustive fixtures
  retain rank 1 and zero gap; all are nominal failures, so scope remains limited.
- [x] Predeclare and execute two additional CPRI circuit development comparisons.
  LI and SI both nominally pass; bounded/exhaustive top-1/top-3 match with zero
  gap before/after. These are development checks with assumed stock, not held-out
  physical validation, and no weights/shortlists/models were tuned.
- [x] Polish navigation/typography, CPRI defaults, stock/ML/second-model labels,
  saved-trial source/admission and preservation of pending operator requests.
- [x] Verify desktop CPRI walkthrough, generated feedback and mobile layout.
  Fresh browser found a pre-existing server/client locale mismatch; deterministic
  numeric hints, rebuilt export and fresh-origin review now yield zero errors.
- [x] Final frontend typecheck/build, 23 local static assets and fresh-database
  external-network-denied smoke pass. Other platforms/disconnected browser remain
  explicitly untested; overall release status is PARTIAL for those omissions.
- [x] Produce both final optimization reports and retained browser/runtime/search/
  test records. Workbook LI/SI warm medians improve 34.0%/11.4%; CPRI is 4.3%
  slower while checking 11 rather than 4 stage/network pairs for correctness.

The separate CPRI pseudo-laboratory waveform pack mentioned in the brief is not
present in current main or the supplied new attachment. Existing generated
fixtures and new narrowly scoped synthetic regression cases cover failure modes;
they are not treated as supplied measurements.

## Starting locally

Use the repository Python environment with `PYTHONUTF8=1` and run
`python scripts/dev.py`, then open `http://127.0.0.1:8000/judge/`.
See `docs/release_readiness.md` for installation and platform limitations.
The old release ZIP and earlier QA summaries are historical records.
