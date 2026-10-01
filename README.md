# ImpulseTwin AI

Physics-guided, inventory-aware high-voltage impulse-generator decision support for POWERnext-AI 2026 Track 1. Readiness target: 10 October 2026.

The local app combines the exact supplied workbook, a separate lumped RLC circuit, constrained resistor-network search, frozen residual models, explicit uncertainty/OOD handling, trial-waveform analysis, and auditable reports. It is not a hardware controller or a laboratory validation claim.

## Run the prepared demo

```sh
cd Impulse
make demo
```

Open `http://127.0.0.1:8000`. All frontend assets, numerical solvers, model files and data are local; no external API or cloud connection is used for inference. `Ctrl+C` stops the server. Port 8000 must be available. On this prepared Mac, double-click `Start_ImpulseTwin.command` as an alternative launcher.

For a clean machine, use Python 3.12 and Node 22+:

Clone this repository, or extract the release ZIP and open its `ImpulseTwin_AI` folder, then run:

```sh
make setup
make build
make test PYTHON=.venv/bin/python
make demo PYTHON=.venv/bin/python
```

Setup/build require internet to install pinned dependencies. The resulting application runs offline. Model artifacts are included; training is not needed during the final demo.

For the full continuation guide, read [HANDOFF.md](HANDOFF.md). The repository includes the prepared static frontend, frozen models, source material, experiment evidence and release ZIP.

## Workflows

| Command | Purpose |
|---|---|
| `make ingest` | Re-export unchanged workbook source sheets/formulas and verify split counts |
| `make train` | Create frozen model competition and evaluate Hidden Test once; existing frozen artifacts are reused |
| `make audit` | Rebuild source/data audit without training |
| `make stress` | Run separate generated circuit stress diagnostics |
| `make test` | Backend regression/E2E tests and frontend typecheck |
| `make build` | Produce static offline frontend |
| `make dev` / `make demo` | Serve the complete local application |

For independent frontend development, run `npm run dev` in `frontend` with the API on 8000. Engineering formulas live in Python only. API documentation: `http://127.0.0.1:8000/docs`.

Four self-contained fallback reports live in `reports/demo_*.html`. Clearly generated waveform CSVs and their archived run snapshots live in `data/demo`. Open a report directly if the live presentation is interrupted; import a sample only after creating a matching live run. Regenerate these with `python3 -m scripts.prepare_demo_artifacts`.

## Evidence and limitations to understand before presenting

- The exact 1425 kV calculator case and all 1400 cached kNN distances/weights reproduce the workbook. Its hardcoded published Validation table does not match evaluation of those same formulas on labeled Validation rows. This remains a source discrepancy, not a passed test.
- PDF 12-stage/0.125 µF, workbook 15-stage/3 µF, and incomplete briefing 3 MV profiles remain separate. PDF stock quantities are unknown and require explicit overrides.
- The six per-type/target frozen models improve RMSE over physics on the untouched synthetic Hidden Test. Five improve on exact workbook kNN; switching crest is worse than kNN. These are synthetic benchmark results.
- ML support now requires the exact calculator-selected stages, charging voltage and resistor settings for the entered inputs, as well as the feature envelope and neighbor-distance checks. Arbitrary stock networks or stage changes receive physics fallback even when their individual values look near training ranges. Parasitic scenarios can leave that support and widen the resulting envelope.
- All 1000 supplied Switching rows request front resistances beyond the sum of the entire workbook stock per stage. Constructible Switching alternatives use different stages/settings and are therefore flagged OOD.
- Reference compliance and independent circuit compliance can disagree. Reference curves reconstruct predicted metrics; the circuit curve is from a separate lumped RLC simulation. Neither replaces measured-waveform validation.
- Uncertainty intervals are marginal synthetic conformal intervals only within their stated assumptions. OOD envelopes, one-shot corrections and finite parasitic scenarios have no laboratory coverage guarantee.
- Trial imports preserve raw data, explicit units, polarity and onset metadata. Demo files cannot be relabeled as laboratory measurements by the built-in workflow.
- Local calibration is scoped to the same profile, model, layout, input neighborhood and resistor settings. It does not retrain the production model or infer reduced-to-full-voltage transfer.

## Optional V2 accuracy candidate

The advanced model selector can explicitly use the experimental V2 candidate. **V1 remains the default.** Its separate nested Train CV development study reduced mean tolerance-normalized RMSE across the six outputs by **5.3656%** against a matched-row V1 refit. Five outputs improved; Lightning tail RMSE was **0.5192% worse**. This is development evidence on previously explored synthetic data, not a newly untouched test or laboratory result. V2 did not rerun the exposed Hidden Test.

The final candidate was frozen before the separate Train calibration outcomes were read. Its joint three-output synthetic conformal envelope retains explicit limits for supported-input selection, optimizer selection, OOD and laboratory use. The experimental gate permits this optional comparison; it does not establish external validation or replace the active default. See `docs/accuracy_v2_results.md` for the complete comparison and prior-development limitations.

The controlled search completed locally in **54.96 seconds**, spent **$0 on cloud**, and preserved the V1 model, registry and saved Hidden Test hashes. `artifacts/qa/freeze_and_release_review.json` independently records those hash checks. Additional compute is authorized if a measured bottleneck justifies it; cloud deployment remains deferred until the user explicitly authorizes it.

## Current checks and handoff

The latest recorded backend run has **67 passing tests, zero failures and zero errors** in `artifacts/qa/backend-tests.xml`. The latest frontend typecheck and static build passed. The exported HTML references **17 local assets**, with no remote or missing assets in the in-process offline check. This does not replace a physically disconnected-network rehearsal on the presentation laptop. Browser review and final archive verification are recorded in `artifacts/qa_summary.json` as they are completed.

The release workflow includes source, frozen V1/V2 artifacts, static assets, generated fallback reports and executed QA evidence. It excludes live SQLite histories and raw uploaded trials. Release packaging follows the final QA update; a fresh-machine installation and disconnected-network rehearsal on a second laptop remain finale preparation tasks.

## Project map

`backend/app` contains source ingestion, ML, physics, constrained search, APIs, SQLite history and report export. `frontend` is the Next/TypeScript interface. `config` holds profiles and challenge rules. `data/source` preserves originals. `artifacts/models` holds the frozen model and one-time evaluation. `docs` contains source reconciliation, assumptions, judging narrative and cloud preparation. `tests` covers mathematical parity and application behavior.

Start with `docs/demo_script.md`, `docs/judges_qa.md`, `docs/source_reconciliation.md`, and `PROJECT_STATE.md`.

Google Cloud credit is optional. `docs/cloud_readiness.md` and the Dockerfile prepare a restricted ephemeral cloud demonstration; no resources have been deployed. The laptop demo remains the primary finale path.


Benchmark scores evaluate residual predictions before runtime support and scenario gating. The optimizer can fall back to physics and widen its envelope; the saved errors are not a laboratory or complete-optimizer accuracy estimate.
