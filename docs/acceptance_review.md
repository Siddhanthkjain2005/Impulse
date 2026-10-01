# Independent acceptance review

Reviewed 1 October 2026 against the supplied master prompt, source reconciliation, implementation, frozen model evidence and executed backend test record. This review separates an implemented local proof of concept from a verified laboratory system.

## Current evidence

The latest recorded backend test run in `artifacts/qa/backend-tests.xml` contains **67 tests, zero failures, zero errors and zero skipped tests**. The record is dated 1 October 2026; the final QA summary records browser and release verification. Frozen V1 artifacts and its original Hidden Test evidence remain unchanged. The separate optional V2 candidate, Train-only cross-validation and calculator-setting support guard are covered by additional checks; see `docs/accuracy_v2_results.md` for gains, regressions and methodological limits.

| Acceptance requirement | Evidence | Status and practical limit |
|---|---|---|
| Preserve and reconcile supplied sources | Original PDF/workbook, all six exported sheets, formula/cached-cell snapshot, SHA manifest, `docs/source_reconciliation.md` | Implemented. Physical nameplate/stock confirmation remains external. |
| Reproduce workbook golden case and weighted kNN | `tests/test_workbook_parity.py`; golden numerical output and all 1,400 cached helper distances/weights | Verified formula/cached-cell parity. **Published static validation-table parity remains unresolved.** |
| Compare stronger residual models fairly | Frozen fit/calibration IDs, three-fold fit CV, official Validation selection, saved one-time Hidden Test evaluation | Implemented and isolation tested. All six selected outputs improve RMSE over physics; five improve over exact kNN. Switching crest does not improve over kNN. |
| Separate metrics by impulse and target | Registry and saved Hidden Test metrics contain three outputs for each impulse type | Implemented. Results describe supplied synthetic data only. |
| Preserve profile provenance | Versioned PDF, workbook and incomplete briefing profiles | Implemented. Briefing profile cannot optimize; PDF quantities require an explicit override with provenance. |
| Return realizable stock plans and hard-filter ratings | Bounded series DP and limited parallel/mixed search; exact per-stage/total component counts; stage-voltage and energy checks | Stock arithmetic verified. Mechanical mounting, pulse ratings and permitted physical connections are not established by the sources. The search is bounded and does not prove global optimality. |
| Numeric waveform compliance and alternatives | Shared extraction, versioned challenge limits, top-five outputs, explicit score terms and nominal/interval statuses | Tested. Challenge compliance is model-specific; it is not a complete IEC certification. Diagnostic failing alternatives are explicitly labeled. |
| Independent physics check | Lumped RLC solver, shared metric extraction and energy diagnostics | Tested numerical behavior. The topology and loss convention remain unvalidated laboratory assumptions. Reference and circuit models can disagree materially. |
| OOD and uncertainty | Feature-envelope and scaled-neighbor gating; synthetic split-conformal intervals; finite parasitic scenarios | Tested gating and interval ordering. Coverage is marginal under synthetic assumptions; OOD and one-shot corrections have no calibrated coverage guarantee. Scenario containment is not proof over continuous bounds. |
| Reject wrong inputs | Range, units/numeric, profile, inventory, stage, optional equipment-reference checks | Tested API workflows. No authoritative equipment BIL catalog was supplied. |
| Trial upload and scoped correction | Raw file hash/storage, explicit mappings and units, polarity/onset handling, generated-demo provenance, configuration matching | End-to-end tested with generated CSVs. No actual laboratory trial is claimed. Correction does not transfer across different settings or reduced/full-voltage conditions. |
| Versioned history and report | Local SQLite runs/trials/corrections; saved JSON and print-ready HTML | End-to-end tested. Local storage is a demo deployment choice; cloud durability/authentication would require separate work. |
| Local/offline operation | Static frontend export, local solvers/models/data, self-contained API documentation and report assets | Backend architecture and export are present. Final browser and disconnected-network rehearsal should be recorded in `artifacts/qa_summary.json` before release packaging. |
| Finished primary UI and release | Next/TypeScript app and `scripts/package_release.py` | Final visual review, frontend build/typecheck result and ZIP verification are being completed separately. This review does not infer those checks from file existence. |

## Evidence interpretation

The supplied 2,000 observed synthetic rows are all challenge passes. They cannot establish false-pass sensitivity or actual shot reduction. The separate 120-case generated circuit stress artifact records model disagreement: 21 reference passes disagree with circuit failures. It is **not** a laboratory false-pass rate because the circuit is also an unvalidated model.

All 1,000 supplied Switching front-resistance settings exceed the entire workbook stock's all-series upper bound of 5,740 Ω per stage. A constructible Switching demonstration necessarily uses different settings and may be OOD even when requested voltage is within the source training range. Do not describe that preset as an in-distribution hardware recommendation.

The frozen competition uses a multioutput CV mean-squared-error objective in original units. Larger numerical targets can dominate hyperparameter choice. The limitation is documented; it is a prospective improvement for a new independently evaluated version, not a reason to tune on the already exposed Hidden Test.

## Finale risks to resolve

1. **A green reference result can conceal a conflicting circuit prediction if presented too quickly.** Keep the independent cross-check beside the reference status and explain its meaning before moving to model scores. Use the circuit solver demonstration to show a separate, honest prediction path.
2. **“Hardware-realizable” can be overinterpreted.** Say that stock counts, resistor equivalents and declared voltage/energy limits are checked. Obtain CPRI confirmation of quantities, pulse ratings and allowed mountings before claiming a deployable lab setup.
3. **The workbook table discrepancy is an acceptance exception.** Preserve golden/helper parity as executed evidence and ask for the organizer's evaluation script. Do not state that every published workbook metric was reproduced.
4. **A new laptop still needs installed dependencies.** Setup/build require internet; inference after setup is local. Rehearse the pinned installation and the prepared export on a second laptop before 10 October. Keep backup reports and frozen artifacts ready.
5. **Final presentation time/rubric is unconfirmed.** The five-minute script is a working rehearsal assumption. Prepare shorter and longer versions after the organizer confirms the format.

## Release checks

- Refresh `PROJECT_STATE.md` to describe actual completed modules and remaining external limitations.
- Record executed backend, frontend and browser results in `artifacts/qa_summary.json`; retain the test XML as supporting evidence.
- Verify the packaged file manifest, archive extraction and one-command launch. Include the executed QA record in the handoff if practical.
- Keep generated samples, live uploaded trials and benchmark source labels distinct. Avoid carrying private uploaded trial data into the release archive.
- Preserve the user's cloud hold: **no Google Cloud deployment or resource creation until the user explicitly authorizes it.**

The appropriate completion claim is a tested local engineering proof of concept with explicit source and laboratory-validation limits. A hackathon result, laboratory first-shot success rate and reduction in physical setup changes cannot be guaranteed by the current evidence.
