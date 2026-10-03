# Reliable trial feedback and readable run evidence

Updated 2 October 2026. This update improves the feedback workflow and the interpretation of saved results. It does not change the frozen ML models, physics solver, search ranking, or challenge tolerances.

## Correct repeated calibration

A trial's displayed residual remains the measured value minus the prediction used for that shot. A new saved calibration carries the **total correction relative to the original model**.

For example, if the original model predicts 100, an earlier correction adds 5, and the next shot measures 107, the displayed new residual is 2 and the replacement calibration is 7. Saving only 2 would discard the earlier correction. The trial and calibration retain the parent calibration identifier, original prediction and previous correction so this sequence can be audited. A repeated shot matching the corrected prediction preserves the existing correction instead of resetting it to zero.

The existing profile, layout, hardware, model/version and 1% input scope still apply. The 30% discrepancy review also checks the total correction against the original prediction. This remains one-shot local feedback, not automatic retraining or proof of reduced-voltage transfer.

## Correct waveform attribution and acquisition review

The demo CSV is generated from the selected candidate. An explicitly supplied candidate identifier that does not belong to the run is rejected rather than silently selecting rank 1. The default without a candidate remains rank 1 for older callers. Tagged live exports also retain run, candidate and unit metadata. Uploads that conflict with those tags are rejected before storage; untagged analyzer files rely on the operator-selected setup. These tags record provenance and are not independently authenticated.

Uploaded CSVs keep their raw bytes and extracted metrics. A separate comparison curve uses baseline-corrected positive magnitude and time relative to the entered physical onset. Negative polarity and delayed captures now align with the prediction without altering the source waveform; polarity remains explicitly displayed. Older records can produce the same comparison in the interface from their saved preprocessing metadata. Before creating a calibration, an acquisition review checks for fewer than four acquired intervals across the rising 30–90% window, or a sustained flat crest that may be clipped or quantized. These are conservative application heuristics, not IEC certification or an instrument uncertainty model. Such uploads remain available for inspection but cannot create a new correction until the capture is reviewed and a suitable waveform uploaded. Passing the basic checks does not establish laboratory accuracy. Earlier uploads without a saved review are checked from their stored waveform before a new calibration can be created.

## Saved evidence stays distinct

Run history and candidate comparison display nominal waveform compliance, agreement with the independent circuit, post-ranking scenario results, and uncertainty status separately. Older records missing a check show **Not recorded**. Circuit-only runs are identified as single-model results. A green scenario result does not turn a MARGINAL uncertainty envelope into a robust pass.

The comparison view distinguishes search samples from the fresh post-ranking challenge and explains the saved ranking order. Counts and filters in history refer to the loaded records, not an inferred total database population.

## Accuracy boundary

These fixes prevent incorrect feedback and misleading comparisons. They are not a new accuracy benchmark. Actual measured waveforms, verified acquisition settings and confirmed machine stock remain necessary to establish performance on the physical generator.
