# Finale demonstration — five minutes

## 0:00–0:35 — the laboratory problem

“Every trial waveform can mean another physical change to front resistors, tail resistors or active stages. Our aim is to give the engineer a stronger first setup, with a component plan they can inspect before the next shot.”

Do not claim a measured percentage reduction in shots: no field trial dataset has been supplied.

## 0:35–1:10 — prove we understood the supplied work

Open the workbook parity view. Show the1425kV case:9 stages,193.0894kV/stage,50Ω front and25Ω tail. Show exact cached hybrid1.20489665µs /51.96370859µs /1432.94658kV. State that every cached neighbor distance/weight also matches.

Say: “We also found an unresolved discrepancy between the workbook's static validation table and evaluation of its formulas. We show that discrepancy and use a reproducible baseline.”

Open profiles briefly:12 stages/0.125µF in the PDF versus15 stages/3µF in the workbook. Explain why they cannot be merged.

## 1:10–2:00 — recommend constructible settings

Use Lightning preset. Run the optimizer. Show the best candidate and one alternative, exact series/parallel networks, per-stage and total counts, charge margin and stored energy.

Describe the objective in plain terms: waveform deviation, setup complexity, uncertainty and operating headroom. All rating and inventory failures are rejected before ranking. The search is bounded, not a proof of a global optimum.

Show nominal versus interval/scenario compliance. “A green point prediction is not the same as a verified laboratory shot.”

With the strengthened support guard and default ±5% parasitic range, the workbook Lightning example is nominally compliant but **MARGINAL**: some scenarios leave the calculator-selected hardware pattern represented by training. Explain this distinction directly; do not reduce uncertainty to obtain a green status. The independent circuit cross-check also fails this reference setting.

## 2:00–2:40 — demonstrate useful skepticism

Show the independent circuit cross-check. It may disagree with the workbook. Switch to the circuit solver and regenerate a setup, explaining that its waveform comes from a lumped RLC model and that synthetic workbook residuals are not blindly transferred to that model.

Use the OOD preset and show the correction goes to zero. Use the impossible-voltage preset and show explicit rejection. This is a software guard, not a substitute for lab interlocks.

For Switching, use the constructible high-capacitance preset:1025kV,1240pF load,740pF divider,320pF stray. Show the250/2500 challenge target, construction plan, and OOD warning for changed stages/resistors. Do not describe it as in-distribution simply because voltage is in range.

## 2:40–3:25 — show the AI earns its place

Open Model Lab. Show per-type/per-target RMSE for physics, exact workbook kNN and selected residual models. Keep pooledR² out of the headline.

“On the untouched synthetic test split, RMSE improved over physics by28.3%,13.0%,52.7% for Lightning front, tail and crest; and19.4%,17.6%,50.0% for Switching peak, tail and crest. We beat the exact workbook kNN on five of six outputs. Switching crest is slightly worse than kNN, and we preserve that result rather than tune on the test set.”

These rounded numbers come from `artifacts/models/hidden_test_evaluation.json`. They are not measured laboratory performance and do not quantify shot reduction.

If time permits, show the separate V2 development panel and its optional “Try V2 candidate” control. It improved macro tolerance-normalized Train CV RMSE by 5.37% against a historical V1 refit, with a 0.52% Lightning-tail regression. Its scores are from a different development protocol and must not be compared as if they replaced V1's final test. Leave V1 as the default for the main presentation.

## 3:25–4:30 — close the feedback loop

Return to Lightning and download its generated sample waveform. Open Trial Calibrator, choose that run, upload the CSV and keep “generated stress test” selected. Show unit mappings, extracted crest/front/tail, polarity and error.

Save the scoped local correction and rerun. Show the corrected original setup in calibration review even if another setup now ranks above it. Explain that no production retraining took place and that a bias is not extrapolated to different hardware or full-voltage shots.

Export the HTML report / save as PDF. It carries inputs, settings, provenance, waveform semantics, alternatives, uncertainty and limitations.

## 4:30–5:00 — finish with the concrete next validation

“We have a reproducible offline engineering workflow: physics, feasible hardware, residual learning, uncertainty and measured-shot feedback. The next step is CPRI stock confirmation and paired reduced-voltage waveforms across layouts. That is how we will measure first-shot compliance and actual reduction in physical setup changes.”

## Rehearsal fallback

Keep the app and this repository on two laptops. Start the server before presenting. Export one report and preserve the frozen model artifacts. Disable internet during a rehearsal to demonstrate independence. Use synthetic files only in the demonstration. If a cloud preview is unavailable, use the local app; its inference does not depend on the network.
