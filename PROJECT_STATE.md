# ImpulseTwin AI project state

Readiness deadline: **10 October 2026**. Inputs reviewed: supplied master prompt, Track 1 archive, and briefing transcript. Updated 1 October 2026. Current status: working local engineering proof of concept with a separate optional V2 accuracy candidate; final browser review is complete and release evidence is recorded in `artifacts/qa_summary.json`.

## Implemented and verified

- Original sources preserved, six workbook sheets exported, full formulas/cached-cell snapshot and SHA manifests retained.
- Exact 1425 kV golden case and every one of the 1,400 cached neighbor distances/weights reproduced.
- Separate PDF, workbook and incomplete briefing profiles, with source provenance and explicit stock assumptions.
- Reference equations and independent lumped RLC simulation, shared waveform extraction, energy diagnostics and versioned challenge compliance.
- Counted discrete resistor networks, hard voltage/energy/inventory filters, five ranked alternatives and transparent score terms.
- Frozen V1 per-regime residual model competition, one-time final synthetic test, OOD gating, synthetic marginal intervals and sampled parasitic scenarios.
- A strengthened model-support guard requires calculator-selected stages, charge and resistor settings as well as range/distance support; arbitrary setting interventions receive physics fallback. Unsupported parasitic scenarios widen envelopes and remove calibrated coverage claims.
- Separate targetwise V2 experiment with nested Train CV, frozen candidate, disjoint calibration, joint synthetic envelopes and an explicit optional selector. V1 remains the default.
- Six-page responsive local interface, interactive numeric waveforms, model evidence, profiles, run history and comparison.
- Raw CSV preservation, explicit units/polarity/onset, generated-data labeling, scoped one-shot correction and retained original-setting review.
- Local audit histories, readable print-ready reports, five regenerated offline fallback reports, generated rehearsal CSVs and judge preparation documents. Reference/circuit disagreement remains prominent in each applicable report.
- **86 backend regression/E2E tests pass** with zero failures/errors. Latest frontend typecheck and static build pass. Static asset verification finds 17 local assets, no remote/missing assets and successful local serving. Root verified the accuracy dashboard, visible regression, optional V2 optimizer and 390px mobile width; see QA artifacts for executed results.

## Demonstrated benchmark

All six selected outputs improve RMSE over physics on the frozen synthetic Hidden Test; five improve on exact workbook kNN. Switching crest is 4.88% worse than kNN. The model was not changed in response. These results do not establish laboratory accuracy, first-shot success or reduced setup changes.

The optional V2 candidate improves macro tolerance-normalized RMSE by **5.3656%** in a matched-row nested Train CV development comparison. Five outputs improve; Lightning tail is **0.5192% worse**. Prior feature exploration and V1 family/hyperparameter selection limit the interpretation; this is not an unbiased final test estimate. Final weights/configuration were frozen before disjoint calibration. No new Hidden Test evaluation or laboratory evaluation was performed.

The V2 search ran locally in **54.96 seconds** with **$0 cloud spend**. Independent SHA checks confirm the V1 model, registry and saved Hidden Test artifact remain unchanged relative to the preregistered protocol. Candidate, protocol and frozen-selection hashes also match. Evidence: `artifacts/qa/freeze_and_release_review.json`; detailed results: `docs/accuracy_v2_results.md`.

Benchmark scores evaluate residual predictions before runtime support and scenario gating. The optimizer can fall back to physics and widen its envelope; the saved errors are not a laboratory or complete-optimizer accuracy estimate.

## Remaining external limits

- The workbook's hardcoded Model Validation table disagrees with evaluation of its own formulas; source reconciliation records the unresolved exception.
- Actual CPRI resistor quantities, allowed mountings, pulse ratings, machine configuration and the role of 545 pF need confirmation.
- No measured laboratory waveforms or verified equipment BIL catalog were supplied. Circuit topology and uncertainty need engineer/laboratory validation.
- Constructible Switching settings differ from training stock and are flagged outside model support. The bounded optimizer does not prove a global optimum.
- V1's shared original-unit CV objective can be dominated by larger-unit targets. V2 uses separate target searches and tolerance-scaled scoring, but new independent data is still needed for an external accuracy claim; the exposed Hidden Test must not become a tuning set.
- Fresh-machine installation on a second laptop and a physically disconnected-network rehearsal remain team tasks before the finale. Archive verification on the current machine is recorded separately.

## Cloud hold

The user authorized additional compute and explicitly deferred cloud deployment. **No cloud resources were created, no cloud credit was spent and no cloud deployment was performed.** The compact V2 search needed only local compute. The $300 credit remains available for a justified later bottleneck; deployment awaits explicit authorization. Local inference requires no external service.

## Start here

Run `make demo` or double-click `Start_ImpulseTwin.command` on the prepared Mac. Open `http://127.0.0.1:8000`. Rehearse with `docs/demo_script.md`, `docs/judge_pitch.md`, `docs/judges_qa.md` and `docs/finale_readiness.md`. Review the optional experiment through `docs/accuracy_v2_results.md`.

The release input inspection confirms live SQLite histories and raw uploads are excluded. The ZIP includes source, frozen models, optional V2 evidence, static interface, five reports and executed QA. Its manifest and extracted application checks are recorded in the release verification.

## Latest agreement and accuracy work

Optional two-model agreement search, clearer waveform-failure labels, an agreement comparison table, and a fifth fallback report are implemented. Three of five declared engineering diagnostic cases gain nominal agreement; Switching and PDF examples remain failures. The default Lightning agreement case passes both simulations in 32 sampled parasitic scenarios but remains MARGINAL under its unsupported-settings uncertainty envelope. This is not laboratory accuracy.

The further V3 Train-only nested search achieved 1.0339% macro improvement versus a historical V2 refit and failed the 5% gate. V1/V2 remain unchanged. Calibration bias is now applied only to scenarios within the saved 1% input scope. See `docs/accuracy_v3_results.md` and the latest QA records.

## Search and numerical verification update

Expanded four-part series/parallel networks (six parts for small catalogs) and identical parallel banks now preserve stock counts and earlier target choices. Circuit v2 refines continuous crossing times and passes independent time-domain integration tests. Every returned setup receives 128 fresh-seed samples and 16 boundary corners after ranking; these do not reorder results. The UI shows their limiting condition and overlays the independent circuit waveform. The default Lightning agreement, two additional Lightning cases and both PDF circuit presets pass all sampled checks. Two model-agreement cases still fail, and uncertainty remains MARGINAL. See `docs/search_v4_results.md` and `artifacts/experiments/search_v4/final_summary.json`. No cloud compute was necessary.
