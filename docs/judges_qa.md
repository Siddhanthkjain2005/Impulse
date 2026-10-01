# Questions the team should be able to answer

**What is the innovation beyond the supplied kNN?**
An inventory-aware discrete search returns actual resistor constructions. Residual model choice is separated by impulse and target, with frozen validation selection, explicit training-support gating and uncertainty. A separate circuit model can challenge the workbook prediction. Trial measurements are analyzed numerically and feed a scoped, auditable correction.

**Why not use a large neural network or generative AI?**
There are2000 structured synthetic rows. The relevant uncertainty is source fidelity and missing real measurements. Regularized regression, SVR and tree ensembles are appropriate competitive baselines. They run locally; no external language model guesses engineering values.

**Do you really improve accuracy?**
On the untouched supplied synthetic Hidden Test, all six selected targets have lower RMSE than physics. Five improve on exact workbook kNN; Switching crest does not. The full per-type metrics, split IDs, calibration separation, chosen hyperparameters and source hash are recorded. No real-lab accuracy claim is made.

**Why does the workbook already haveR²≈0.9999?**
Pooling Lightning≈1.2µs with Switching≈250µs creates enormous between-regime variance. A pooled score can hide weak prediction within each regime. We show within-regime outputs and errors normalized to challenge tolerances.

**Why do your recomputed validation metrics differ from the supplied table?**
The table cells are static values. Our formula implementation reproduces the golden output and every1400 cached helper distance and weight, but evaluating the labeled Validation rows gives a different aggregate. The table-generation script is not supplied. We preserve both values and ask for that script; we do not invent parity.

**How do you know a resistance is physically usable?**
The search enumerates bounded series, parallel and mixed constructions, checks each component count, and reports per-stage/total usage. This verifies stock arithmetic and stated voltage/energy bounds. Mechanical mounting, resistor pulse rating and approved connections remain engineering checks because the sources do not specify them.

**Why separate three generator profiles?**
The PDF describes12 stages,200kV/stage and0.125µF/stage. The workbook uses15 stages and3µF/stage. The briefing mentions3MV and15 stages but leaves other details incomplete. Merging them would create a nonexistent machine with inconsistent stored energy and tail behavior.

**What happens at2400kV?**
A2400kV erected-stage rating is not a guarantee of2400kV load crest at efficiency below1. The stage voltage, efficiency and circuit transfer can make that requested output infeasible. We reject it when constraints cannot be met rather than silently overcharge stages.

**Why can the waveform disagree with the workbook?**
The workbook estimates times using closed-form approximations and defines crest as the requested voltage. Its chart is therefore a reconstruction from metrics. The enhanced solver discharges generator capacitance through a lumped RLC equivalent into the load and extracts metrics from numerical samples. Its model assumptions and circuit topology remain approximations; disagreement signals a need for measured validation.

**Does90% confidence mean a90% chance of passing in the lab?**
No. The intervals are marginal split-conformal intervals under the supplied synthetic distribution and exchangeability assumptions. They are not simultaneous three-output, conditional-on-support or lab guarantees. OOD uses explicitly uncalibrated envelopes. Parasitic scenario fractions describe the sampled assumptions, not a physical probability of success.

**Why disable ML for some normal-looking inputs?**
The training support includes generator settings, not just requested voltage. Switching source resistors9370–21810Ω exceed the entire workbook front stock5740Ω/stage. Constructible settings use other stages/networks and can be OOD even at an in-range voltage. The software falls back to physics rather than treating nearby voltage as proof of support.

**What does a single calibration shot change?**
It stores the raw waveform, units, preprocessing, complete configuration and measured-minus-predicted residual. A local additive correction applies only within a narrowly matched scope. Production models do not retrain automatically. Reduced-voltage to full-voltage transfer is not inferred from one shot.

**Are you IEC60060 compliant?**
We implement the supplied challenge rules with explicit provenance. The current IEC2025 publisher describes a changed switching front definition170/2500, while this challenge requires250/2500. We retain the challenge target and do not claim complete licensed-standard certification.

**How many trial shots does this save?**
Not yet established. Proposed field evaluation: compare engineer/workbook first setups and optimizer setups on held-out objects/layouts, record first-shot compliance, total trial shots, physical component changes and false-pass predictions. Freeze the model and evaluation protocol before collecting the comparison outcomes.

**Why Google Cloud if the app is offline?**
Cloud hosting can provide a convenient judge preview. The demo itself does not require it. The available credit does not justify an unnecessary GPU or paid external inference service. Cloud durable history/authentication would need further work beyond the local PoC.
