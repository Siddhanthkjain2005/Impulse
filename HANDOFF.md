# Continue ImpulseTwin AI

## Evidence and Judge Mode update — 3 October 2026

The evidence/release feature branch adds unified capture provenance, Laboratory Evidence, Hardware Verification, a versioned test-object catalog, deterministic recommendation evidence levels, a controlled exhaustive search benchmark, saved-artifact experiment timeline and seven-step Judge Mode. Existing engineering workflows and frozen V1–V5 evidence remain preserved. README now links deep history rather than accumulating every release note.

Use `python scripts/verify_release.py` for the current report and `docs/release_readiness.md` for cross-platform setup. Original QA files and release ZIP are historical; the latest source and rebuilt static frontend on this branch are authoritative for this update. Windows clean setup, automated checks and fresh-database/offline-process checks are recorded in the new release report; untested platforms remain explicit. No deployment or new model training occurred.


Repository: https://github.com/Siddhanthkjain2005/Impulse

Read this guide, then `PROJECT_STATE.md`, `docs/judging_criteria_evidence.md` and `docs/accuracy_progress.md`. Source discrepancies are documented in `docs/source_reconciliation.md`; detailed search and experiment results are linked below. The finale readiness deadline is 10 October 2026. Official event dates are 10–11 October.

## Continuation snapshot — 3 October 2026

The latest handoff includes the working local app, prebuilt UI, frozen model artifacts, original supplied sources, V2–V5 experiment evidence, 198 passing backend tests, fallback reports and the offline release ZIP. The most recent work improves capture-quality review and measured-shot decision reporting, adds RLC sensitivity and setup-change planning, and documents the organizer's published expectations.

V1 remains the default; V2 is an explicit experimental option. V3, V4 and V5 failed their promotion gates. The recorded V1 synthetic benchmark improves macro error by 41.9265% versus physics; V2's 5.3656% improvement is development CV evidence. No measured laboratory accuracy or 100% accuracy has been established. Keep these evidence types separate when presenting.

Continue in this order:

1. Run the prepared app and verify installation on a second laptop; rehearse with internet disconnected. Keep the 10 October readiness deadline in view.
2. Confirm actual generator settings, stock quantities, component ratings and allowed connections with the laboratory team. Keep conflicting workbook, PDF and briefing profiles separate.
3. Obtain real waveform captures with full setup metadata. Save predictions before uploads, separate calibration and evaluation captures, and follow `docs/laboratory_capture_plan.md`. Use the existing measured-shot review to report errors and false PASS/FAIL decisions.
4. Address demonstrated failures and presentation usability, then freeze the demo and rehearse `docs/demo_script.md` and `docs/judges_qa.md`. Preserve all failed-study and frozen-test evidence.

For another coding assistant, paste [the continuation prompt](docs/continuation_prompt.md). It carries the project's goals, current decisions, constraints and next tasks. Cloud deployment remains deferred by the owner.

## Start the application

Use Python 3.12. The prebuilt interface and model artifacts are committed, so Node is only needed when modifying or rebuilding the frontend.

```sh
git clone https://github.com/Siddhanthkjain2005/Impulse.git
cd Impulse
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make demo PYTHON=.venv/bin/python
```

Open http://127.0.0.1:8000. API documentation is available at http://127.0.0.1:8000/docs. No cloud credentials or external inference services are required.

## Make and verify changes

Install Node 22+ for frontend development:

```sh
cd frontend
npm ci
cd ..
make build
make test PYTHON=.venv/bin/python
```

The latest recorded backend suite has 198 passing tests. Browser, build, offline-asset and model-freeze evidence is in `artifacts/qa_summary.json` and `artifacts/qa/`. A clean installation on a second machine still needs rehearsal.

Create a feature branch for changes. Do not force-push or replace the preserved model evidence.

## Important continuation constraints

- Each ranked candidate now has 144 post-ranking scenario checks. Inspect failures and the worst-case inputs; these checks never rerank candidates. Circuit v2 refines continuous waveform crossings.
- The new agreement search is optional: preset G or the button beside a failed circuit cross-check. It finds both-model nominal passes for the default Lightning case; uncertainty remains MARGINAL. V3 did not meet its promotion gate and was not activated.
- V1 is the default. V2 is available through the optimizer's advanced residual-correction selector and is explicitly experimental.
- V2's 5.37% macro error improvement is Train cross-validation development evidence, with a small Lightning-tail regression. It is not a new untouched test or laboratory accuracy claim.
- Preserve `artifacts/models/hidden_test_evaluation.json` and the frozen V1 models. Do not reuse the exposed Hidden Test for tuning or overwrite the completed V2 experiment. New experiments need separate names and untouched final data.
- All supplied training outcomes are synthetic and compliant. Arbitrary resistor/stage interventions and constructible Switching hardware lack corresponding training evidence; runtime support checks disable learned corrections where appropriate.
- Workbook, PDF and briefing generator profiles disagree. Keep them separate. Real stock quantities, pulse ratings, mounting and laboratory waveforms remain unverified.
- Cloud training was authorized using the user's reported $300 credit, but no resources or spending were needed. Cloud deployment remains explicitly deferred until the user requests it. No credentials are included.
- Never label generated rehearsal CSVs as measured laboratory shots. Live histories, raw uploaded trials, dependencies, caches and temporary files are excluded from Git.

## Where to work

| Area | Location |
|---|---|
| API, runtime support and experiment serving | `backend/app/main.py`, `backend/app/ml/registry.py` |
| Physics and compliance | `backend/app/physics/` |
| Hardware search and ranking | `backend/app/optimization/` |
| Frozen V1 training and separate V2 search | `backend/app/ml/train.py`, `backend/app/ml/experiment_v2.py` |
| UI source / prepared interface | `frontend/` / `frontend/out/` |
| Original sources and processed records | `data/source/`, `data/processed/` |
| Optional experiment training dependencies | `requirements-experiments.txt` |
| Judge pitch, demo and remaining validation | `docs/` |
| Five generated fallback reports and CSVs | `reports/demo_*.html`, `data/demo/` |
| Packaged offline handoff | `release/ImpulseTwin_AI_Local_PoC.zip` |

The release ZIP includes the latest verified local handoff. Use the repository for subsequent development; regenerate the archive with `python -m scripts.package_release` after recording successful QA if you need a new release.

Latest feedback changes: see `docs/trial_feedback_update.md` for repeated-shot calibration, capture review, selected-candidate CSVs and the run-evidence views. The capture checks are application heuristics, not measurement-system certification.

For new laboratory evidence, use Trial calibrator → Verify accuracy on new shots. Keep evaluation captures separate from all calibration ancestors. The original raw CSVs must be present. See `docs/accuracy_progress.md`; test fixtures are synthetic and do not populate live laboratory scores.

For the hardware-change demonstration, open Compare → Plan changes from a saved setup, select a baseline run/candidate, and export Printable change plan. It compares the same generator/layout and does not change the optimizer ranking. See `docs/setup_transition_planner.md`.

For the RLC explanation, open Optimizer → Explore R, L and C. Preview object capacitance +30% on the Lightning agreement case, select Equivalent circuit and Front / peak detail, and explain the front-time limit crossing. Preview audit JSON preserves the generated evidence. Resistor previews are hypothetical; saved recommendations remain unchanged. See `docs/rlc_sensitivity.md`.


## Latest pooled accuracy study

The V4 Train-only experiment tested 48 shared/partially pooled configurations with both impulse types held out in every shared fit. No pooled candidate passed the inner selection gate; additional macro improvement was 0.0000%, and V1/V2 remain unchanged. The Model lab now records this result. Read `docs/accuracy_v4_results.md` before further tuning; preserve the frozen evidence and obtain new measured outcomes for independent accuracy evaluation. No cloud resources were created.


## Accuracy and judging update — 3 October 2026

Official and supplied expectations are mapped in `docs/judging_criteria_evidence.md`; no finale numeric weights were found. Prioritize accurate predictions, feasible counted hardware, both impulse types, numeric compliance and credible measured feedback. Public event dates are 10–11 October; team readiness remains 10 October.

V5 added 1.0921% macro Train development improvement versus a historical V2 refit (0.2363% beyond a matched Ridge control), below its 5% gate. It was not promoted; V1/V2 and old model evidence remain frozen. See `docs/accuracy_v5_results.md`.

Capture-resolution review now blocks three demonstrated sparse-waveform false passes from calibration and scoring, preserving raw samples and provisional extracted values. The measured-shot review adds false PASS/FAIL counts, denominators, worst-shot errors, saved-rule snapshots and separate envelope containment. See `docs/capture_resolution_review.md` and `docs/measured_decision_review.md`. No new laboratory accuracy result exists. Website previews were omitted at the user's request for this update; automated checks are recorded separately.
