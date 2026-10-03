# V4 pooled residual accuracy experiment

Recorded 2 October 2026. The experiment found **no additional development error reduction** against the historical V2 refit: **0.0000%**. No pooled candidate cleared the inner selection threshold; all 30 outer-fold/output selections retained the V2 fallback. The declared 5% macro improvement gate was not met. V1 remains the serving default and V2 remains the existing optional candidate.

## Hypothesis and registered procedure

Relative residual patterns may transfer between Lightning and Switching. Pooling their input-derived structure could increase the useful sample size without extra labels. The registered experiment tested 48 configurations: two physical feature bases, polynomial degrees one/two, four sharing strategies and three Ridge penalties. Strategies shared all coefficients, added a regime intercept, partially pooled regime slopes, or allowed separate regime slopes. Each configuration was eligible at 50% or 100% weight against the same-row historical V2 fallback.

Only the original 560 fit IDs per type from official Train were eligible. The 140 calibration IDs per type were excluded; Validation and Hidden Test outcomes were not parsed or evaluated. Five synchronized outer folds each held out 112 rows per type and made 896 combined rows available for training. Each shared fit excluded *both* regimes' held-out rows. Three synchronized inner folds performed selection without either outer holdout. All feature/target scaling and polynomial transforms were fitted inside the relevant training fold.

Selection required at least 2% lower inner tolerance-normalized MSE than the matched historical V2 refit. Promotion required at least 5% lower mean of the six outer tolerance-normalized RMSE values, with no output more than 2% worse. The protocol, complete grid and source hashes were saved before the experiment ran. Completed experiments refuse to retune.

## Same-fold results

| Output | Historical V2 refit RMSE | V4 search RMSE | Unit |
|---|---:|---:|---|
| Lightning front | 0.007187 | 0.007187 | µs |
| Lightning tail | 0.633297 | 0.633297 | µs |
| Lightning crest | 4.873002 | 4.873002 | kV |
| Switching peak | 1.739125 | 1.739125 | µs |
| Switching tail | 25.607145 | 25.607145 | µs |
| Switching crest | 3.591840 | 3.591840 | kV |

The identical scores describe the selection procedure's fallback to V2, rather than performance of a deployed shared model. No pooled production weights were created. The experiment completed locally in **5.95 seconds** with **$0 cloud spend**.

## Interpretation and preserved evidence

These are development scores on previously explored synthetic Train inputs, reused outer folds and historically selected V2 parameters. They are not a new independent test, a laboratory accuracy percentage, or a reliable estimate of an irreducible noise floor. “100% accuracy” would require a precisely defined success measure and fresh outcomes; zero prediction error cannot be promised from these data. The active V1's saved synthetic MAPE values remain about 0.33%–1.06%, and those residual benchmark scores precede runtime support gating.

The V1, V2 and V3 saved artifacts were preserved and their hashes verified. The actual hidden-test artifact was not reevaluated. Hardware support checks and the physics fallback remain unchanged. Tests verify that shared training excludes held-out IDs from both regimes, features ignore labels/IDs/split metadata, predictions retain physical units, scoring excludes calibration rows, and completed results cannot silently retrain.

Files: `artifacts/experiments/v4/protocol.json`, `summary.json`, `oof_predictions.json`; runner: `backend/app/ml/experiment_v4.py`. The Model lab displays the decision and exposes its saved result and method. `make experiment-v4` reproduces the refusal to overwrite completed results; a new hypothesis needs a separate version and declared protocol.

Fresh measured shots are now the highest-value route to verified further improvement. Use `docs/laboratory_capture_plan.md` to separate correction-development shots from new evaluation shots and vary documented hardware settings. The measured-shot review already scores saved predictions without fitting the evaluation waveforms. Heavy cloud training on the same small synthetic dataset would not fill that evidence gap. Deployment remains deferred.
