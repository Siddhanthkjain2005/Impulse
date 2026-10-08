# ImpulseTwin AI — complete frontend redesign brief for Claude

You are acting as a principal product designer, creative director, senior frontend architect and creative 3D developer. Redesign and implement the frontend of **ImpulseTwin AI**, our working POWERnext AI 2026 Track 1 hackathon project. Aim for exceptional visual craft, memorable motion, purposeful 3D and a polished engineering workflow. Use your own judgment, research and taste. We want an original, visually stunning product that feels appropriate to high-voltage engineering and can impress judges immediately while staying useful during a real demonstration.

**Implement the redesign in the existing project. Retain every working feature, the backend, API contracts, engineering behavior and evidence.** Do not stop at a mood board, a landing page, a mockup or a description of what could be built. Bring the complete application to a coherent finish.

“Best in the world” is our aspiration for craft, not a claim to put in the product. Make specific design decisions, execute them carefully and refine the result. You have creative freedom over the frontend; you do not have permission to make up engineering results, change model decisions or rewrite the backend to make the demonstration look better.

## 1. Repository, starting point and source of truth

- Repository: https://github.com/Siddhanthkjain2005/Impulse
- Current continuation branch at this handoff: `codex/switching-crest-review`.
- Latest completed implementation commit at this handoff: `64209d1`.
- Existing draft integration PR: https://github.com/Siddhanthkjain2005/Impulse/pull/2
- Current local checkout: `/Users/swetha/Downloads/HACKTHON_WIN`. Your checkout may be elsewhere; resolve paths from the actual repository root.
- This branch includes friends’ evidence/Judge Mode work and engineering-hardening work. Inspect the actual checkout and current remote state; preserve any newer or uncommitted work. Do not assume an older `main` checkout contains the complete product.
- Read `AGENTS.md`, `HANDOFF.md` and the newest `PROJECT_STATE.md` sections first. Historical sections preserve earlier states; the newest sections and current code take precedence for factual context.
- Work on a new `codex/` frontend branch when appropriate, based on the complete current continuation. Do not reset, force-push, delete work or merge the existing draft without the owner’s instruction.

Read these project documents before deciding what the product should communicate:

1. `README.md`
2. `docs/source_reconciliation.md`
3. `docs/assumptions.md`
4. `docs/judging_criteria_evidence.md`
5. `docs/judge_pitch.md` and `docs/demo_script.md`
6. `docs/accuracy_progress.md`
7. `docs/accuracy_v6_results.md` and `docs/accuracy_v7_results.md`
8. `docs/independent_simulation_results.md`
9. `docs/trusted_waveform_data_search.md`
10. `docs/reference_waveform_data_review.md`
11. `docs/laboratory_capture_plan.md`
12. `docs/release_readiness.md`

The supplied challenge sources are also present:

- `POWERNEXT_Track1_Astra_Winning_Master_Prompt.md`: internal implementation specification, not the organizer’s judging rubric.
- `PowerNext_AI_Track1_Briefing_Transcript.md`: expert briefing, with transcription imperfections.
- `data/source/HV IG Problem Statement.pdf`: primary challenge specification.
- `data/source/Hybrid_Physics_ML_Impulse_Generator_Optimiser.xlsx`: reference calculator and synthetic benchmark.

Do not overwrite these sources. Inspect the code when a document’s older feature count conflicts with current implementation.

## 2. Product purpose and audience

High-voltage impulse testing can require repeated changes to active generator stages and front/tail resistor networks. Engineers need a useful starting setup, an explanation of the physics, a counted hardware plan and a clear indication of whether the predicted waveform meets the requested limits.

ImpulseTwin helps the operator:

1. Specify a Lightning or Switching impulse and the relevant object/parasitic inputs.
2. Select a source-identified generator profile and declare available stock.
3. Obtain ranked, constructible candidate settings.
4. Inspect stage count, charge per stage, resistor networks, energy and predicted waveform metrics.
5. Understand compliance, model disagreement, uncertainty and unsupported ML settings.
6. Compare alternatives and estimate changes from a previous setup.
7. Upload a captured waveform, review its acquisition quality and compare it with the saved prediction.
8. Apply a strictly scoped local correction where admitted.
9. Evaluate separate eligible measured shots and inspect the evidence trail.

Users include high-voltage engineers, laboratory staff, student demonstrators and judges who may not know our code. The frontend should make the physical decision understandable before exposing deeper model/evidence detail.

The event is publicly scheduled for 10–11 October 2026; team readiness is targeted for 10 October. This is a working engineering proof of concept with a local, offline-capable demonstration. No official numerical finale scoring weights were found. Do not invent a rubric or claim a beautiful frontend guarantees a win. The supplied challenge emphasizes predicted waveform behavior, feasible settings, numerical compliance, explanation, alternatives and a working demonstration.

## 3. Creative freedom and visual ambition

Develop your own strongest direction for this subject. Choose the typography, palette, composition, density, lighting/material treatment, spacing, navigation, motion and 3D vocabulary. You may restructure frontend components and presentation hierarchy substantially while preserving every workflow and route.

Before implementation, briefly consider two or three distinct visual directions. Choose one with a clear reason connected to this product. Then implement that direction fully; do not spend the whole task making alternatives or waiting for routine aesthetic approval.

Useful starting ideas, not a prescribed design:

- A precision engineering instrument with cinematic hardware visualization.
- A premium laboratory studio with material depth, an elegant waveform workspace and exceptionally readable technical details.
- A modern industrial control room with sophisticated data density and a calm, confident interaction system.

Dark, light or mixed surfaces are your choice. Originality matters more than a fashionable dark palette. Use strong contrast and hierarchy, coherent surfaces and a distinctive visual signature. Colors should communicate engineering state as well as identity. Make the actual hardware, waveform and decision feel central.

Avoid a generic admin template, decorative gradient cards everywhere, illegible miniature labels, endless glass panels or unrelated particle wallpaper. This should feel designed for this particular problem. A restrained working area can coexist with a spectacular presentation moment.

Research relevant websites and technical examples if browsing is available. These are optional starting points, not templates to copy:

- [Linear](https://linear.app/): explore product hierarchy, typography, navigation and dense workspace composition.
- [Stripe](https://stripe.com/): explore how complex systems can be presented through organized visuals and layered explanation.
- [Apple Vision Pro](https://www.apple.com/apple-vision-pro/): explore product framing, material presentation and pacing.
- [Bruno Simon](https://bruno-simon.com/): explore original interactive 3D craft; adapt the ambition to a usable engineering tool.
- [Three.js examples](https://threejs.org/examples/): investigate rendering and interaction techniques that suit the chosen scene.
- [Motion for React documentation](https://motion.dev/docs/react): consult actual APIs if selecting that animation library.

Use your own web research to find better references. Explain which ideas fit this project. Do not copy another site’s identity, claims or unlicensed assets. Prefer procedural geometry and assets we can bundle locally. Do not turn this into a portfolio game or a marketing site that makes the engineering work harder to reach.

## 4. Current technical architecture

The existing frontend uses:

- Next.js **16.3.7**, App Router.
- React **19.2.0**.
- TypeScript **5.9.3**.
- Tailwind CSS **4.1.18**, plus existing authored CSS.
- ECharts **6.0.0** for engineering charts.
- Lucide React **0.468.0** for icons.

Verify the current `frontend/package.json` and lockfile before changes; these versions describe the inspected handoff, not a requirement to upgrade.

The backend is Python/FastAPI with existing physics, optimization, frozen ML inference, compliance, data provenance, local storage and report generation. Treat it as read-only for this redesign. Backend application code is under `backend/app/`; its request schemas are in `backend/app/schemas.py`.

Frontend source:

- `frontend/app/`: pages and global styles.
- `frontend/components/`: workflows, charts and shared UI.
- `frontend/lib/api.ts`: API helpers, default inputs and profile/solver transitions.
- `frontend/lib/trial-waveform.ts`: capture comparison handling.
- `frontend/components/workspace.tsx`: shared state, navigation and reusable UI.
- `frontend/out/`: committed static production export served by FastAPI.

The Next configuration uses static export and trailing-slash routes. Keep this architecture. The built application is served at `http://127.0.0.1:8000`; Next development runs on port 3000 and the existing API helper routes requests to port 8000. Retain same-origin behavior for the exported app.

You may add carefully chosen frontend libraries for motion and 3D. Evaluate React/Next compatibility and maintenance from official documentation. Three.js with React Three Fiber/Drei and Motion are possible tools, not mandatory choices. Choose the smallest coherent set. Do not stack multiple animation engines without a concrete reason. Do not upgrade the whole stack just to obtain a cosmetic effect.

Keep WebGL/browser-dependent code behind appropriate client boundaries and lazy loading. Do not introduce server features incompatible with the static export. Prevent hydration mismatches from time, random values, locale formatting, browser globals or viewport assumptions. Use deterministic formatting for scientific values.

## 5. Eleven existing routes — preserve all of them

| Route | Existing purpose | Redesign objective |
|---|---|---|
| `/` | Optimizer and engineering workspace | Make the request, selected setup and waveform the visual center; keep advanced controls accessible. |
| `/judge/` | Seven-step guided demonstration | Give the product its strongest presentation sequence without losing the guarded workflow. |
| `/model-lab/` | Saved model comparisons and numerical verification | Make the different evidence types instantly distinguishable and the six outputs easy to compare. |
| `/profiles/` | Generator sources, ratings, inventory and unknowns | Make source identity and differences comprehensible; do not merge machines visually or numerically. |
| `/trial-calibrator/` | CSV capture import, review, local correction and measured evaluation | Turn a complex form into a clear, complete workflow with truthful admission states. |
| `/runs/` | Saved run history and exports | Make finding, restoring and understanding previous results effortless. |
| `/compare/` | Candidate comparison and setup-transition planning | Show engineering tradeoffs and before/after hardware changes clearly. |
| `/laboratory-evidence/` | Capture provenance, admission and independent evaluation eligibility | Make traceability and exclusion reasons readable; zero measured evidence must look intentional. |
| `/hardware-verification/` | Source-derived values, constraints and unresolved physical facts | Communicate known, assumed and unknown hardware facts without fabricated certainty. |
| `/experiment-timeline/` | Saved model studies and promotion/rejection decisions | Give experiment history a clear visual narrative while preserving failed studies. |
| `/search-quality/` | Bounded versus exhaustive search evidence | Present declared cases, ranking agreement and scope without implying physical validation. |

You may group navigation into coherent sections, add a useful command palette or improve contextual navigation. Every existing route must remain reachable and directly loadable. Do not remove a feature because it is visually inconvenient or leave secondary pages in the old design.

## 6. Preserve the engineering request and defaults

The current frontend intentionally starts with the **CPRI physical profile, circuit solver and residual ML off**. Retain this default. Example parasitics and efficiency are editable assumptions, not measured machine facts.

Current CPRI frontend example inputs are approximately:

- Requested voltage 1425 kV; Lightning impulse.
- Object/load C 650 pF, divider C 250 pF, stray C 55 pF.
- Inductance 12 µH, efficiency 0.83.
- Profile base capacitance enabled, contributing 545 pF once.
- Circuit prediction and physics mode.

The primary CPRI source profile specifies up to 12 stages, 200 kV per stage, 0.125 µF per stage, 2.5 kJ per stage and 30 kJ total. Source resistor values include front 30/465/3700 Ω per stage, Lightning tail 520 Ω and Switching tail 22000 Ω. Counts, allowed mountings/topologies and pulse ratings remain unverified. Configured 50 kV/two-stage lower bounds are application assumptions, not independently established physical operating minima.

The separate workbook reference uses up to 15 stages and 3 µF per stage. Do not present it as the same machine. The incomplete briefing profile remains inspectable but disabled for optimization.

Preserve the full optimizer request fields and their backend-defined meanings:

- `profile_id`, `impulse_type`, `test_kv`.
- `load_c_pf`, `divider_c_pf`, `stray_c_pf`, `l_uh`, `efficiency`.
- `solver`, `model_mode`, `require_model_agreement`.
- `connection_mode`, `layout_id`, `include_base_c`.
- `stage_min`, `stage_max`, `max_components_per_network`.
- `inventory_override`, including separate front/tail values, counts per stage and a provenance note.
- `uncertainty_pct`, `monte_carlo_samples`.
- `test_object_id`, `equipment_reference_kv`, `equipment_reference_source`, `confirm_reference_mismatch`.
- `calibration_id`.

Respect schema bounds and validation; do not encode a new set of engineering limits in the frontend. You may replace the inventory JSON editor with a better structured editor if it emits exactly the existing validated payload and retains provenance. An advanced JSON view can remain for power users.

Profile and solver changes have deliberate reset behavior. Inspect and preserve `profileInputs` and `solverInputs`: changing profiles resets incompatible inventory, calibration, agreement and reference-confirmation state; circuit mode and non-workbook profiles disable workbook residual correction. The “Try V2” action switches to the workbook profile as well as choosing the experimental mode. Preserve it.

Equipment/BIL references are separate from machine capacity. Catalog values can be unavailable. Operator-supplied references require a source. A mismatch may require explicit confirmation. Do not invent an authoritative BIL catalog or automatically approve a mismatch.

## 7. Result presentation and waveform interactions

Keep the backend’s candidate ordering and settings authoritative. Candidate selection must coordinate the hardware plan, charts, explanation, evidence and exports.

Preserve and improve presentation of:

- Active stages and utilization.
- Charge per stage, requested crest and predicted crest.
- Front/tail equivalent resistance per stage and total-network context.
- Counted series/parallel resistor topology, per-stage and total component counts.
- Stored energy, voltage/energy margins and applicable hard constraints.
- Ranked feasible alternatives, diagnostic alternatives when no nominal pass exists, Pareto markers and score breakdowns.
- Physics prediction, raw residual/correction, gated prediction and secondary circuit comparison where applicable.
- Support/OOD state and the actual residual trust weight.
- Nominal compliance, individual metric deviations, uncertainty/envelope containment and sampled scenario results as distinct quantities.
- Post-ranking verification and original-setting review, including a corrected candidate outside the displayed top five where the backend retains it.
- Printed report and JSON downloads.

Give the selected candidate a clear focal point. A useful layout could connect a hardware view, the main waveform and three metric/tolerance views, but choose the final layout yourself. Keep deep technical detail available through well-designed disclosure rather than deleting it.

The existing engineering chart supports waveform layers, labels, time/voltage units, tooltip inspection, legend toggles, zoom/pan, target/crest context and full/front detail. Retain these capabilities. A visually elegant chart must keep quantitative accuracy: correct domains, units, series, actual samples and readable differences between layers.

Reference/predicted curves reconstructed from metrics are not independently predicted physical waveforms. Circuit curves are simulations; uploaded curves are captured samples with source metadata. Keep their kinds and limitations visible. Do not smooth, resample, invent intermediate points or change plotted data merely to make the curves prettier. A reveal animation may expose an existing curve without altering its coordinates or values.

RLC sensitivity remains a backend-requested preview varying one declared parameter from −30% to +30%. Stages, charge and efficiency remain fixed. It does not alter or rerank the saved recommendation. Resistance previews can be hypothetical and may need another stock search. Preserve exportable preview evidence and discard stale responses when the selected controls/run/candidate change.

## 8. Purposeful 3D — make it a signature feature

Build a genuinely useful, visually polished 3D element if it meets the performance and clarity requirements. You decide whether it belongs in Judge Mode, the selected-candidate workspace, or both through one reusable scene.

Recommended conceptual direction:

1. A procedural, schematic Marx generator stage stack driven by the selected candidate’s actual stage count.
2. Clear distinction between active and inactive stages within the selected profile’s maximum.
3. Front/tail resistor-bank concepts that connect to the counted network explanation.
4. A selection or hover interaction revealing useful information such as stage identity, charge or network role.
5. An optional before/after scene driven by the existing setup-transition output, showing shared/new/deactivated stages and retained/added/removed components.
6. A waveform time cursor that can drive an explicitly illustrative pulse through the scene, using the actual displayed waveform’s time coordinate.

Design geometry, camera, lighting, materials, annotations and transitions with your own taste. Use procedural local geometry unless a properly licensed local asset clearly improves the result. A technically abstract model can be more honest and more beautiful than a guessed photorealistic machine.

Critical interpretation rules:

- Label it **conceptual/schematic**. It is not a surveyed or validated geometric twin of the real CPRI machine.
- Do not invent dimensions, mounting, wire routing, available inventory, spark-gap behavior, pulse ratings or connection permissions.
- Do not depict active control of real equipment. This product is decision support, not a generator control console.
- A decorative discharge animation must be identified as illustrative. It is not computed electromagnetic or spark-gap physics.
- Drive reported settings from the saved candidate. Draft input changes must not silently masquerade as a new solved result.
- Preserve a crisp accessible 2D waveform and readable hardware details alongside the scene.

Interactions may include rotate, zoom, reset camera, focus a stage and inspect a network. Provide touch and keyboard alternatives for meaningful actions. Do not require a user to navigate a 3D world to complete a test request.

Lazy-load the scene. Handle WebGL failure/context loss. Pause rendering when off-screen or the tab is hidden; dispose resources on unmount. Use demand-based rendering where appropriate. Scale shadows, resolution and post-processing to device capability. Have a polished SVG/2D fallback that carries the same useful information. The whole product must remain usable when 3D is unavailable.

## 9. Motion system

Create one coherent motion language. Motion should explain hierarchy, selection, progress and transitions, and make the product feel considered.

Potential opportunities:

- A concise first appearance of the engineering workspace or conceptual generator.
- Navigation/selection feedback and coordinated candidate-to-waveform transitions.
- Judge Mode scene transitions that retain orientation and a visible step identity.
- Panel expansion, tooltips, drawers and advanced-control disclosure.
- A waveform reveal and a clearly labeled illustrative pulse sequence.
- Selection highlights across a candidate, stage visualization and counted network.
- Honest pending/loading states, success feedback and recoverable errors.

Choose timing/easing appropriate to the design. Keep routine controls responsive; hero/presentation motion can be richer than data-entry motion. Avoid repeated long entrance sequences on every navigation. No scroll hijacking, forced cinematic loading screen, cursor replacement that impairs forms or auto-playing audio.

Never invent optimization percentages, simulated backend phases, live device telemetry or measured laboratory results. If the API does not report progress, show honest indeterminate activity. Authoritative numerical results should be available immediately after the response; decorative count-ups must not create misleading intermediate scientific values or copy/export inconsistencies.

Respect `prefers-reduced-motion` and provide a usable quiet presentation. Avoid flashes/strobing. Animations must not cause layout shifts, steal focus or delay access to important errors.

## 10. Preserve Judge Mode’s exact seven-step workflow

The steps are:

1. **The problem**
2. **Test request**
3. **Configuration**
4. **Evidence**
5. **Alternatives**
6. **Trial feedback**
7. **Summary**

Keep this 4–6 minute narrative and its functions. You can improve composition, transitions and presentation controls. Do not silently collapse it into a showcase homepage.

The request step retains profile/impulse/voltage/load selection, equipment reference review, advanced physical inputs, inventory/provenance and validation/confirmation. Downstream steps require a saved result. Pending request edits must prevent presentation of an older result as the answer to the new request.

The remaining steps must show the actual counted configuration, waveform/metric evidence, alternatives, generated demonstration or explicitly classified capture feedback, calibration admission and an honest summary of what has and has not been established.

Keep the distinction between the selected backend prediction engine and a secondary cross-check visible. A failed waveform cross-check is an engineering diagnostic, not a failed software unit test.

## 11. Trial import, calibration, evaluation and history

Redesign these workflows without removing any required inputs or checks:

- Upload actual CSV files against an identified saved run and candidate.
- Preserve column mapping and time units ns/µs/ms/s, voltage units V/kV/MV, baseline subtraction and explicit physical impulse onset.
- Retain the current 5 MB upload limit and backend validation.
- Handle positive/negative polarity and delayed captures while preserving original raw samples and source bytes.
- Show source type, captured-at information, instrument/operator metadata, extracted metrics, provisional comparison, quality flags and admission reasons.
- Keep trial comparisons tied to their original run/candidate even if the current selection changes.
- Acquisition review v3 blocks incomplete falling limbs and other unresolved captures. Preserve the backend’s decision and explanatory messages.
- Generated demonstrations remain generated; a user-entered measured label cannot upgrade known generated provenance.
- Synthetic benchmarks, unknown origin and measured captures have different evidence/admission states.
- Local calibration is scoped to the profile, layout, solver/model/hardware and compatible inputs; approximately 1% input agreement is part of the existing scope. No automatic retraining or inferred reduced-to-full-voltage transfer.
- Keep calibration ancestry, conservative source review and the original prediction accessible.
- Evaluation requires at least three eligible independent measured captures. Duplicates and calibration-source waveforms are excluded. Display grouping, denominators, acquisition exclusions, false PASS/FAIL counts and negative error improvements.
- Saved runs, reports, JSON/evaluation exports and setup-transition exports remain available.

An attractive empty Laboratory Evidence page must honestly say no measured evidence is recorded. Do not fill it with fabricated laboratory charts. Existing generated demonstrations may be offered through their genuine workflow with unmistakable labels.

## 12. Evidence truth — preserve these distinctions everywhere

The frontend communicates saved/backend evidence; it does not recompute or improve accuracy.

- **Frozen V1:** saved synthetic test improves against physics for all six outputs and against exact workbook kNN for five. Switching crest is the exception. Recorded macro error reduction versus physics is approximately 41.9265%, not an “accuracy percentage.”
- **Optional V2:** six outputs beat matched kNN in its separate development cross-validation. It has no new independent final-test or laboratory result. It remains explicitly experimental and is not the default.
- **V3–V7:** completed, separately recorded studies and failures remain visible. V6/V7 crest studies missed their fixed promotion gates and did not create new serving weights.
- **Independent circuit verification:** 240 generated cases; all references passed solver/refinement/energy checks. Six numerical agreement channels passed on 40 fixed evaluation cases per impulse type. The independent charge/flux integrator and production modal solver use the same assumed topology. This is numerical verification, not six-output ML-versus-kNN improvement or laboratory accuracy.
- **Measured laboratory accuracy:** not established. The external trusted sources inspected do not supply the complete compatible per-shot input/output mapping needed for that claim.
- **Runtime support:** arbitrary resistor/stage/charge interventions, circuit mode and non-workbook profiles can disable learned corrections. Keep actual backend support and fallback state visible.
- **Uncertainty/scenarios:** nominal PASS, joint/marginal synthetic intervals, OOD sensitivity envelopes, model agreement and sampled scenario pass fractions are different evidence. A scenario fraction is not a laboratory success probability.
- **Unknown data:** unknown stock, ratings, source, missing metrics and “not recorded” must stay unknown. Do not convert nulls into zeros, GREEN/PASS badges or favorable summary counts.

Keep the supplied Lightning 1.2/50 µs and Switching 250/2500 µs challenge definitions. Current outside standards can use a different Switching front-time definition; do not silently substitute it. Use the saved/backend rules and units.

Evidence badges should be informative, readable and concise. Use progressive detail to explain limitations without covering the interface in repetitive warnings. Never remove a material distinction simply because it complicates the visual story.

## 13. Backend contracts and data/state continuity

Inspect actual request/response shapes before wiring redesigned views. Existing API groups include:

- Service and sources: `/api/health`, `/api/source-status`, `/api/generator-profiles`, `/api/generator-profiles/{id}`, `/api/reference`.
- Hardware and references: `/api/hardware-integrity`, `/api/test-objects`, `/api/test-objects/validate`.
- Optimization and inspection: `/api/optimize`, `/api/simulate`, `/api/compliance/check`, `/api/explain`.
- Models/evidence: `/api/models`, `/api/models/{id}/metrics`, `/api/experiment-timeline`, `/api/search-quality`, `/api/laboratory-evidence`, `/api/verification/independent-circuit`.
- Runs: `/api/runs`, `/api/runs/{id}`, `/api/runs/{id}/judge`, `/api/runs/{id}/report`, `/api/runs/{id}/json`, `/api/runs/{id}/demo-waveform`.
- Sensitivity: `/api/runs/{id}/candidates/{candidate_id}/sensitivity`, `/api/sensitivity/{id}/json`.
- Transitions: `/api/runs/{id}/setup-transitions`, `/api/setup-transitions/{id}/json`, `/api/setup-transitions/{id}/report`.
- Trials/calibration: `/api/trials/upload`, `/api/trials`, `/api/trials/{id}/calibrate`.
- Evaluation: `/api/evaluations`, `/api/evaluations/{id}/json`.
- Documents: `/api/documents/{name}`.

Methods, multipart field names, schema requirements and errors come from the current code/OpenAPI. Do not guess them from this list. Do not add backend endpoints or alter existing contracts for the redesign.

Preserve shared run/candidate/inputs/trial/calibration state, last-run restoration and storage IDs. The existing `impulsetwin-last-run` restoration handles missing records without inventing a replacement. Preserve compatible persistence behavior and selected-result identity.

Keep drafts and saved results distinct. Preserve a previous successful run after a failed new optimization, but label its age/identity clearly. Handle late or obsolete async responses so they do not overwrite the current selection. Avoid duplicate submissions, unnecessary repeated requests and request loops caused by scene/motion state.

Keep real backend connection states, retry/reconnect, loading, empty, error and partial/missing-data states. Do not replace a failing endpoint with plausible mocked data. Loading skeletons are acceptable; fabricated successful results are not.

## 14. Accessibility, responsiveness, performance and offline behavior

Design for the demo laptop, ordinary laptops and tablets/phones. Review the layout model at 1440px, 1280px, 1024px, 768px and roughly 390px. Wide comparison tables can use an intentional contained scroller; the whole page should not overflow horizontally.

Use semantic headings/forms/tables, persistent form labels, clear focus states, keyboard operation, sufficient contrast and meaningful screen-reader names. Status needs text/icons in addition to color. Essential information must not depend on hover, motion or 3D. Tooltips should not be the only way to learn a field’s meaning.

Make chart text legible on a projector and at normal laptop zoom. Prefer tabular numbers and correct scientific units. Formatting should distinguish zero from missing and preserve meaningful precision. Text should remain selectable; exports must retain actual numeric values.

Protect interaction responsiveness. Set an explicit scene/asset budget appropriate to the demo hardware and measure what tools allow. Aim for smooth desktop motion without promising an unmeasured frame rate. Avoid continuous GPU rendering behind every page, excessive full-screen blur, unnecessarily large textures, giant models and loading multiple canvases unintentionally.

No runtime CDN fonts, scripts, textures, HDR environments, videos or models. Bundle licensed assets locally and retain attribution. The product must work with external network access blocked once local dependencies/assets are installed. Do not require a paid 3D asset, API key or hosted rendering service.

Keep the static frontend served by the local backend. Do not deploy, spend cloud credit, alter infrastructure or move the application to another framework/hosting platform. Backend reports remain functional; you may improve their frontend entry points and print-friendly frontend views without rewriting backend report generation.

The owner has previously deferred live application browser previews/screenshots and intends to review the site themselves. Respect that unless they change the preference. External design-reference research is allowed. Perform automated checks and clearly report any visual, browser, mobile-device or WebGL verification that was not executed; do not claim visual inspection from compilation alone.

## 15. Implementation sequence and completion checks

1. Audit current routes, features, APIs, state and source/evidence rules. Create a concise route/feature preservation checklist before editing.
2. Research references and choose one original design direction. Briefly record the reasoning and the highest-value signature interaction.
3. Establish a coherent frontend design system: tokens, typography, spacing, surfaces, elevation, status colors, controls, tables, panels and motion.
4. Implement the shared shell/navigation and the core engineering workspace. Build reusable primitives that support every page.
5. Implement the purposeful 3D signature with real saved-data connections and a polished fallback.
6. Redesign Judge Mode and all remaining routes, including real empty/error/unsupported states.
7. Verify behavior and data/state continuity, then refine layout, motion and performance within the permitted review scope.
8. Rebuild the static export and update frontend-specific handoff/QA documentation. Do not overwrite historical QA or model evidence.

Allowed scope includes frontend source, frontend assets, justified frontend dependency/config changes and new redesign documentation/QA. Treat backend code, physics, optimization, schemas, storage, supplied sources, frozen models, benchmark records and generated/measured provenance as protected. If you find an unrelated backend defect, report it separately rather than quietly changing it during this redesign.

Run the project’s actual commands with the compatible runtime:

- Frontend TypeScript check.
- Production static build; use the documented Node22/webpack path if the local default runtime/build tool needs it.
- Existing backend regression suite to verify interface-only changes have not affected the project.
- Local/static asset checks and the fresh-database external-network-denied smoke.
- Source/model integrity checks without fitting models or rerunning exposed final-test predictions.
- Focused frontend behavioral checks for redesigned critical controls/state, not trivial tests that merely mirror styling.

Verify critical journeys: both impulse regimes, CPRI unknown-stock guidance and assumed-stock demo labeling, workbook supported/unsupported modes, out-of-range/reference mismatch handling, candidate switching, stale draft/result identity, run restoration, sensitivity preview, transition planning, generated trial feedback, source/admission errors and measured-evaluation empty/ineligible states.

If regenerating the existing local release archive, retain exact source/data hashes and excluded live histories/raw user uploads, follow the repository packaging workflow, and verify its manifest/extracted application. Preserve the original raw-data line endings and `.gitattributes` byte-preservation rules.

Completion requires:

- A substantial, cohesive visual redesign implemented across all eleven routes.
- A memorable, relevant 3D/interactive element with its truthful label and working fallback.
- A consistent motion system with reduced-motion behavior.
- Every existing feature, endpoint contract and scientific/evidence distinction preserved.
- No fake successful requests, fabricated numbers, hidden failures or backend/model changes.
- A successful typecheck/static export and appropriate regression/integrity checks, with any unexecuted review scope clearly stated.
- A concise final handoff: design rationale, changed frontend areas, retained feature checklist, motion/3D behavior, dependencies/assets, validation performed and remaining review needs.

Use your own brain throughout. Resolve routine design and implementation decisions yourself. Make this feel like a beautifully crafted engineering product worthy of its problem, with the full existing application still working underneath it.
