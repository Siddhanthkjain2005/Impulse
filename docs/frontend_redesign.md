# Frontend redesign — 8 October 2026

Branch `codex/frontend-redesign`, based on `codex/switching-crest-review` at `64209d1`. Only `frontend/` source and assets plus this documentation and a new QA record changed. Backend, physics, optimisation, schemas, storage, configuration, supplied sources, frozen models, benchmark records and generated or measured provenance were not changed.

**Before reviewing:** the committed `frontend/out` is still the earlier export. Rebuild it on the Mac (Node 22, existing `node_modules`):

```bash
git switch codex/frontend-redesign
cd frontend && npm run typecheck && npm run build -- --webpack && npm run test:unit
cd .. && python -m scripts.release_smoke   # fresh DB, network denied, checks every asset in the new export
```

The production `next build` could not run in this session (see "Not executed"). Commit the rebuilt `frontend/out` once you have reviewed it.

## Design direction

The product is decision support for a high-voltage test bay. The design uses that setting.

- **Control room.** Request forms, setup tables, limits and evidence sit on light, paper-like sheets. These pages are dense, carry many numbers and must stay legible on a projector.
- **Test hall.** The selected candidate is shown on a dark stage beside an oscilloscope-style waveform. This is the one dramatic surface.
- **Trace channels.** Each evidence type always has the same colour and line style: prediction cyan, measured yellow, independent circuit magenta, physics green, target grey dashed. Every chart has a written key, so meaning never depends on colour alone.
- **States.** Pass, fail, attention and unknown always show an icon and text. Unknown values show as "Not recorded" or "Unknown", never as zero.
- **Type.** Barlow is a DIN-like signage face; it is used for text. Barlow Condensed is used for large engineering numbers and headings. Numbers use tabular figures.

Three directions were considered:

1. A dark glass dashboard everywhere. Rejected: the evidence tables were hard to read and it looked like a generic template.
2. A blueprint/print style. Rejected: it gave the 3D element no stage.
3. The chosen control room plus test hall.

**Signature interaction.** A conceptual 3D Marx stack is built from the saved candidate. Its time cursor reads the plotted prediction samples and drives the stack's output glow. A judge can move along the waveform and see the generator respond, while the labels state clearly what is illustrative.

## Changed frontend areas

| Area | Change |
|---|---|
| Shell (`workspace.tsx`) | Grouped navigation: Judge Mode · Engineering · Evidence. Run chip showing the saved run or "Request edited". ⌘K command palette. Engine status with an offline banner and Reconnect. In-app Quiet motion switch. Mobile menu. |
| Store (`workspace.tsx`) | Original fields and actions kept. Added: an optimise ticket and in-flight guard so stale or duplicate responses never replace the selection; a restore that only runs when no run is loaded; `reconnect()`; `draftOverride` for local stock edits. **Changed behaviour:** edits made while a solve is in flight are now kept and shown as unsolved. Previously they were overwritten by the returned run's inputs. |
| Optimizer `/` | Request sheet, a dark test-hall panel (3D stack, scope with time cursor, tolerance gauges), counted setup with IEC-style network schematics, a candidate rail, and anchored evidence sections (limits, evidence ladder, fixed-setting challenge, model agreement, why this configuration, models and source parity, R/L/C sensitivity, calibration review). |
| Judge `/judge/` | Seven-step presentation with a step rail and one persistent 3D view. Each step sets its own camera view. Waveforms appear on the steps that discuss them. Arrow keys, PageUp/PageDown and fullscreen work. The structured stock editor replaces the raw JSON textarea, but still emits the same payload. |
| Compare `/compare/` | Context bar and setup transition planner with before/after stacks (shared, newly active and deactivated stages; per-part deltas), plus a ranking strip, a grouped comparison table and component plans. |
| Trial calibrator | Step flow, drag-and-drop upload, and the optional existing upload fields `captured_at`, `measurement_instrument` and `operator_notes` (sent only when filled). Also: comparison chart, quality review, calibrate, re-optimise and independent evaluation. |
| Evidence routes | Model lab: evidence-kind cards, a six-output verdict grid, the V2 experiment with Try V2, and V3–V7 panels. Laboratory evidence: designed empty state bound to live counts. Hardware verification, experiment timeline and search quality: redrawn with the same data. |
| Profiles, Runs | Nameplates and a side-by-side table where an unknown minimum stays unknown. A run table with filters, Restore, report and JSON. |
| Design system | `app/globals.css` (tokens, controls, tables, notices, print), `app/workbench.css`, `app/pages.css`. `evidence.css` and `polish.css` were removed, and Tailwind is no longer imported. |
| Pure modules | `lib/generator-model.ts` (topology parsing and verification, scene models), `lib/inventory.ts`, `lib/series.ts`, `lib/motion.ts`. `lib/api.ts` only gained helpers; the existing exports are byte-identical. |

## Preservation checklist

- [x] All 11 routes exist with the same paths and trailing slashes. The static export config is unchanged.
- [x] Endpoint set unchanged. A scan of both trees finds no endpoint dropped and none added. Request bodies are unchanged, and the three optional trial upload fields already exist in the backend form.
- [x] Defaults unchanged: CPRI profile, circuit solver, residual ML off, base C included, unknown CPRI stock blocks Optimize until counts or an assumed-stock demo are supplied.
- [x] `profileInputs` and `solverInputs` resets unchanged (covered by unit tests). Changing profile clears stock, calibration, agreement and the mismatch confirmation.
- [x] Seven demo presets are identical to the original. The *CPRI out-of-range* preset has no stock, so it was already unsubmittable on CPRI and still is. This is reported below, not changed.
- [x] Try V2 (workbook profile plus `experimental_v2`), agreement search ("Find settings passing both models"), and equipment-reference validation with explicit mismatch confirmation.
- [x] Judge Mode keeps its 7 steps, draft/review locking, recommend (validate → optimise → judge), upload, demonstration, active trial, calibration admission and summary checklist.
- [x] Evidence distinctions kept: simulation, reconstruction, generated, synthetic, measured, unknown, assumption and conceptual each have their own tag. Nominal compliance, interval containment and scenario fraction stay separate. V1 5/6 vs kNN, V2 development-only 6/6, and numerical 6/6 are not merged. Laboratory measured captures show as none.
- [x] Reports, JSON exports, run restore, sensitivity preview with stale discard, transition planning, generated trial feedback and the measured-evaluation empty and ineligible states.

## 3D and motion

- **Truthful label.** "Conceptual schematic" is always visible.
- **What comes from data.**
  - Stage count (active, inactive and maximum) and per-stage front/tail banks come from the saved candidate.
  - Wiring is drawn only when the backend topology string parses to a tree that reproduces the saved `equivalent_ohm` and per-stage counts. All 50 topologies in local runs passed this check. Anything else is shown as a parts list.
  - Transition mode uses the saved review's part deltas.
- **What is illustrative.** The "Illustrate" erection sequence is labelled as not spark-gap physics. The output glow interpolates only the plotted prediction samples.
- **Loading and rendering.**
  - three.js r170 is lazy-loaded with `import('./engine')` after a WebGL probe.
  - Frames render only on demand: rendering pauses when the view is off screen or the tab is hidden.
  - Quality tier comes from core count, pointer type and pixel ratio. Pixel ratio is capped at 2 (high tier) or 1.5. Shadows are used on the high tier only.
  - The environment map is procedural; there are no textures, models or HDR files.
  - Mounted 3D views: one on Optimizer, one on Judge, and two small ones in the Compare transition planner.
- **Fallback.** When WebGL is unavailable, or the graphics context is lost, the same saved information is shown as a 2D SVG elevation. A "Restart 3D" button appears after a context loss. The 2D/3D choice is remembered.
- **Keyboard.** The 3D view is a focusable group: arrows rotate, +/− zoom, PageUp/PageDown select a stage, 0 or Escape resets.
- **Motion.** Duration tokens are `--d1..--d4`. One orchestrated moment plays only on a freshly solved run: the illustrative erection sequence plus a waveform clip-sweep. Restoring or switching runs does not replay it. Everything else is a response to user action. `prefers-reduced-motion` or the Quiet motion switch sets all durations to 0 and skips the sequence.

## Dependencies and assets

- **npm.** No new packages. `package.json` gained only `test:unit`; the lockfile is untouched.
- **three.js.** r170 (MIT), vendored as `frontend/vendor/three/three.module.min.js` with its `LICENSE` and a typed subset (`three.module.min.d.ts`). It ships with the app and needs no CDN.
- **Fonts.** Barlow and Barlow Condensed `.woff2` files (SIL OFL 1.1, licence in `public/fonts/OFL-Barlow.txt`) are served from `/fonts/` by the existing static mount.
- **Packaging note.** `scripts/package_release.py` does not copy `frontend/public` or `frontend/vendor`. The built `frontend/out` contains everything needed at runtime. If the release archive must also rebuild from source, add those two folders to that script; it was not changed here.

## Validation performed

The environment limits matter for reading these results. Most checks ran in a Linux cloud sandbox where the npm registry was blocked. That sandbox had TypeScript 6.0.3, a shim for `next`, Python 3.13, and pytest 9 built from source. The project's own TypeScript 5.9.3 and real Next 16.3.7 types were used in a Linux VM on the owner's machine.

| Check | Result |
|---|---|
| `tsc --noEmit` with the project's TypeScript 5.9.3, real Next/React types and `node_modules` | Pass |
| Same with TypeScript 6.0.3 in the sandbox | Pass |
| `npm run test:unit` (10 node:test cases: topology verification, request identity, profile/solver resets, stock payload, time cursor, scene models, formatting) | 10/10 pass on both |
| Backend regression suite (`pytest`, unchanged backend) | 337 passed |
| Frozen-evidence hashes / configuration and registry | PASS (45 files) / PASS |
| `scripts.release_smoke` (fresh database, external network denied) | PASS, run against the **previous** committed export |
| Render harness: real backend app plus the redesigned frontend bundled with esbuild, in headless Chromium with SwiftShader WebGL. All 11 routes at 390, 768, 1024 and 1440 px | No console or page errors, no horizontal overflow |
| Server render (`renderToString`) and hydration of all 11 routes | No errors, no hydration mismatches |
| 27 behaviour checks against the real backend (listed in the QA record) | 27/27 |
| WebGL unavailable, context loss and restart, 2D toggle, reduced motion | Pass |

Screenshots from that harness were used only for self-review. They were not committed, in line with the owner's preference to review the site themselves.

## Not executed / remaining review

- **Production `next build` / static export.** Not run. The registry was blocked and the Linux SWC binary was unavailable, so the export could not be produced here. The offline-asset check of the new export therefore still needs to run after building.
- **Real-hardware review.** Not done on a real GPU, in Safari or Firefox, on touch devices or a projector, or with a screen reader. No frame rate was measured. All visual checks used SwiftShader in headless Chromium.
- **Release archive.** Not regenerated.
- **Finding (unchanged).** The *CPRI · out-of-range rejection* preset cannot be submitted because CPRI stock is unknown. The rejection path itself works: an assumed-stock run with a 2800 kV request returns the backend's 422 and keeps the saved run, clearly labelled. Giving this preset the demo stock is a one-line change if wanted.
