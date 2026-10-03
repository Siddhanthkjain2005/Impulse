# Compare setup changes before another shot

Updated 2 October 2026. The briefing at 6:07–6:48 identifies physical resistor and stage changes as part of the laboratory problem. The Compare page now contains **Plan changes from a saved setup**.

Choose a baseline saved run and candidate that represent the current setup. The planner compares that counted plan with the target run’s returned alternatives. The baseline remains an operator-selected saved plan; the app cannot confirm installed hardware or actual stage positions.

## Selection and evidence

The baseline and target must share the full generator profile and declared layout. Different source profiles or versions are rejected. Saved counts, stage totals and equivalent resistances must agree with their candidate settings.

An option can be selected only if its primary nominal result, all available nominal model checks, declared stock quantities and recomputed stage-voltage/energy ratings pass. Reference mode requires a recorded passing independent circuit check; a missing check is not a pass. Circuit-only mode is identified as a single-model comparison. Missing or failed evidence remains visible in diagnostic alternatives.

Among eligible returned options, the change preference is lexicographic:

1. Fewer changed front/tail network families.
2. Smaller active stage-count change.
3. Fewer component additions/removals on shared stages.
4. Smaller absolute charge change.
5. Original rank as the final tie-breaker.

This is a declared planning preference over the saved shortlist, not a globally optimal mechanical plan. Original candidate order, optimizer scores, model weights and uncertainty labels remain unchanged. Post-ranking challenge results do not choose or reorder the option. If the closest nominal option fails its saved challenge or lacks challenge evidence, the planner explicitly requests review; it does not silently select another candidate using that evidence. A passing finite challenge can coexist with MARGINAL uncertainty.

## What the counts mean

Each network shows before/after quantities by resistor value. For the corresponding shared active stages, it computes retained quantities and active-plan additions/removals. Parts required on newly active stages and present on deactivated stages are recorded separately. Deactivating a stage does not imply physically removing its resistors.

Changing the connection description is conservatively treated as changed wiring, even when the multiset of parts is unchanged. The planner does not prove electrical graph equivalence, know mounting locations or determine which parts can actually be reused. Uniform per-stage networks and corresponding shared stages are assumptions.

The saved transition includes source/target IDs, SHA-256 hashes of both source records, the full option list and separate review evidence. Export **Printable change plan** for an offline discussion handout, or the audit JSON for reproducibility. Neither output instructs hardware operation or establishes laboratory approval.

The updated Optimizer chart also uses the same baseline/polarity/onset-corrected trial comparison curve as Trial calibrator. Raw CSV bytes and stored original samples remain intact.

## Validation and limits

Regression tests cover charge-only preference, preserved ranking and challenge independence, shared/new/deactivated stage accounting, rewiring with unchanged parts, missing model/stock evidence, rating failures, mismatched generators/layouts, corrupted totals, immutable audit records and escaped printable HTML.

No actual reduction in climbs, shots, time or physical rewiring has been measured. This update adds planning and consistency; it does not establish an additional accuracy gain. Models, physics/search source files and challenge tolerances are preserved.

For an offline rehearsal, open `reports/demo_setup_transition.html`. Its archived synthetic example selects original rank 4, with 45 modeled shared-stage additions/removals versus 63 for rank 1. Both retain their recorded 144/144 checks and MARGINAL status. The generated banner remains visible.
