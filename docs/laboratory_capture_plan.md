# Capture plan for the next measured accuracy comparison

This plan records evidence; it does not specify how to operate a high-voltage generator. The laboratory team selects permitted shots under its approved procedures and verified equipment ratings.

## Lock the comparison before collecting outcomes

1. Record the confirmed generator profile/version, actual stock quantities, layout and environmental/acquisition conditions. Keep the workbook's synthetic profile separate from the physical machine.
2. Assign shot IDs to a calibration group and a separate evaluation group in advance. A useful initial pilot is five calibration captures and five new evaluation captures at one confirmed setup. This small pilot establishes descriptive errors; it does not establish generalization or a success probability.
3. Save the original prediction and actual proposed settings before the captures. Use calibration-group outcomes only to develop a correction. The app currently applies a single-shot scoped correction; it does not average five shots or estimate instrument uncertainty automatically. Choose the calibration capture by a recorded rule before viewing evaluation outcomes.
4. Save the corrected prediction, then collect the separate evaluation shots. Upload those evaluation CSVs against that saved candidate. Use **Trial calibrator → Verify accuracy on new shots** to compare physics, the original model and the saved corrected prediction on the same captures.
5. Retain failures, review flags and negative error reductions. Record any exclusions with their acquisition reason. Do not select evaluation shots because they produce favorable results.

## Record alongside every untouched analyzer CSV

| Record | Required detail |
|---|---|
| Shot identity | Unique shot ID, acquisition date/time, calibration/evaluation assignment |
| Source setup | Saved run ID and candidate ID; actual generator profile/version and layout |
| Inputs | Requested voltage, load/divider/stray capacitances, inductance and efficiency assumptions |
| Actual hardware | Active stages, charge per stage, front/tail resistance per stage, network topology and counted parts |
| Acquisition | Instrument and divider identifiers, calibration references, range, bandwidth, sample interval and trigger configuration |
| Export mapping | Actual time/voltage columns and units; raw file hash |
| Processing origin | Explicit baseline and physical impulse onset, with how they were determined |
| Waveform extraction | Front/peak, tail and crest; polarity; acquisition review and any excluded shot reason |
| Independent reference | Laboratory-approved measurement result and uncertainty when available; keep it separate from the app's extraction |

The app checks basic acquired resolution and flat crests, retains raw bytes, and rejects duplicates or evaluation captures found in any calibration ancestor. It cannot authenticate operator labels, verify actual machine settings, infer instrument accuracy, or prove that a manually selected sample is independent.

Collect deliberate hardware variations only when approved by the laboratory, with new saved settings and separate recorded groups. Reduced-voltage calibration does not establish transfer to full voltage. Model support and constructibility limits remain active.

After the locked comparison is recorded, export its evidence JSON and retain its source CSVs and capture log. Future model development may use a separately designated development dataset. Keep a fresh evaluation group for the next independently assessed change.
