# Continue ImpulseTwin AI

Repository: https://github.com/Siddhanthkjain2005/Impulse

Read `docs/search_v4_results.md` for the latest search/precision checks. Read `PROJECT_STATE.md` first, followed by `docs/source_reconciliation.md` and `docs/accuracy_v2_results.md` and `docs/accuracy_v3_results.md`. The finale readiness deadline is 10 October 2026.

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

The latest recorded backend suite has 86 passing tests. Browser, build, offline-asset and model-freeze evidence is in `artifacts/qa_summary.json` and `artifacts/qa/`. A clean installation on a second machine still needs rehearsal.

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
