# Source reconciliation — ImpulseTwin AI v1

Reviewed 30 September 2026. This is the implementation gate. The supplied files are retained unchanged in `data/source`; every nonempty workbook cell, cached value and formula is preserved in `artifacts/reference_workbook_snapshot.json`. Every source sheet has a CSV export. These are the canonical evidence for the exhaustive workbook cell-level inventory.

## Source authority and profiles

The PDF is the challenge/hardware specification. The workbook is a reproducible mathematical reference and synthetic benchmark. The briefing supplies operational expectations, not a replacement nameplate. Their parameters are not interchangeable.

| Parameter | PDF profile (p4 annotated figure) | Workbook profile (Hybrid Calculator) | Briefing profile |
|---|---|---|---|
| Overall voltage | 2400 kV | 3000 kV derived from stage rating | approximately 3 MV (4:54, 15:50) |
| Stages | 2–12; minimum from p4 text | 15 maximum, application minimum 2 | 15 (14:53, 15:43) |
| Stage voltage | 200 kV | B14: 200 kV | 200 kV; two 100 kV capacitors per stage |
| Stage capacitance | 0.125 µF | B15: 3 µF | unknown |
| Energy | 2.5 kJ/stage, 30 kJ total | 60 kJ/stage, 900 kJ total derived at 200 kV; mathematical reference only | verbal 2.5 kJ tentative, no verified total |
| Front resistors/stage | 30, 465, 3700 Ω | 10,20,30,50,75,100,150,200,300,500 Ω | unknown |
| Lightning tail/stage | 520 Ω | 5,10,15,20,25,30,40,50,75,100,150,200 Ω | unknown |
| Switching tail/stage | 22000 Ω | same untyped inventory | unknown |
| Inventory quantities | unknown | four of each value per stage | unknown |
| Charging R/stage | 135 kΩ in annotated figure | not specified | unknown |
| Potential resistor | 2 MΩ | unknown | unknown |
| Discharge resistors | 5.45 kΩ and 13 kΩ | unknown | unknown |
| External R front/tail | dash (not specified) | none specified | unknown |
| Repetition | 2/minute | unspecified | mentions two pulses |
| Basic load C | 545 pF | not separate; divider default 500 pF | unknown |
| Sphere diameter | 25 cm | unknown | unknown |
| Height | approximately 8.7 m | unknown | casual height reference, not a specification |
| Connections | ambiguous `1 p12 s; p s` | erected Marx equivalent assumed | charging parallel, discharge series |
| Mechanical area/weight | dashes/unknown | unknown | unknown |

PDF scan typography is small and some original nameplate resistor text is ambiguous; the readable annotated figure is the source for the table, not a claimed independent nameplate verification. Confirm with CPRI before laboratory application.

## Workbook defaults, formula and metric provenance

Hybrid Calculator B5=400 kV system voltage, B6=Lightning, B7=1425 kV test voltage, B8=850 pF test-object load, B9=500 pF divider, B10=150 pF stray, B11=18.5 µH loop inductance, B12=0.82 expected efficiency, B13=15 stages, B14=200 kV/stage, B15=3 µF/stage. System voltage B5 is a label/context input; it is not used to validate a BIL catalog.

For n stages, C2 is the sum of the three pF inputs converted to F, C1=Cs/n. Required stages=ceil(V/(eta*200)); charge=V/(eta*n). Theoretical front total R=sqrt(max(1e-18,(Tfront/1.67/1e6)^2-2.5*L*C2))/C2. Theoretical tail total R=Ttail/1e6/[0.693*(C1+C2)]. Each per-stage resistor is rounded to the nearest 5 Ω; this rounding DOES NOT check the inventory. Excel positive half-up rounding must be reproduced.

Front=1.67*sqrt((n*Rf*C2)^2+2.5*L*C2)*1e6 µs. Tail=0.693*n*Rt*(C1+C2)*1e6 µs. Crest=Vtest by definition, so workbook crest is not an independent circuit prediction. Constants 1.67, 2.5 and 0.693 are reference approximations, not verified universal waveform equations.

ML Helper fits the 1400 Train rows. Its distance is a sum of squared normalized feature differences, with NO square root. Normalizers: V=1500, load=1300, divider=800, stray=350, L=30, eta=1; Rf/Rt use 100 for a Lightning TRAINING row and 30000 for a Switching TRAINING row. A type mismatch adds 1. Excel RANK<=7 includes ties. Weight=1/(distance+1e-6). Three residuals are added to the physics results. This asymmetric distance must be preserved in the baseline.

Golden cached outputs: n=9, charge=193.08943089430895 kV, Rf=50 Ω, Rt=25 Ω, front=1.2100299583068181 µs, tail=52.20888749999999 µs; hybrid=[1.204896648838928,51.963708586038585,1432.94658495185]. H12 and H13 are YES.

Model Validation rows4–6 publish [MAE,RMSE,MAPE%,R²]: front=[0.8029226967468847,1.3268845868283912,0.6087737376034419,0.9998867803665854]; tail=[12.3111195841096,20.36728343332161,1.0555353274270178,0.999723971693066]; crest=[4.095831849727654,4.9528733296199166,0.3325965710497729,0.9994242228438336]. Model Card explicitly says no laboratory validation has been completed. These pooled results require within-impulse breakdowns.

Synthetic Dataset: 2000 rows, 1000/type, Train1400/Validation300/Hidden Test300. All 22 exact source columns are preserved in the manifest and CSV. Hidden Test is not available for fitting or tuning. Synthetic data is never described as measurements.

## Challenge rules and contradiction decisions

1. PDF 12-stage/0.125µF and workbook15-stage/3µF imply radically different energy and tail physics. Separate versioned profiles; briefing incomplete profile is inspectable but cannot optimize.
2. Workbook rounding creates R values not necessarily in inventory, especially switching. Reference reproduction is labeled a calculator benchmark. Hardware search must construct networks and account for every part; it may return infeasible. PDF stock quantities are missing, so optimization needs user-supplied quantities, clearly identified as an assumption until verified.
3. PDF545pF basic capacitance and workbook divider500pF could overlap. Keep a separate explicit include-base-capacitance setting; do not silently double-count.
4. Workbook3µF at200kV implies60kJ per stage, not PDF2.5kJ. Derived reference ratings must not be labeled physical generator ratings.
5. Challenge switching250/2500 differs from IEC60060-1:2025's new170/2500 definition. Retain challenge targets. IEC publisher verifies the change at https://webstore.iec.ch/en/publication/65088 (edition4, 17 April2025); full new extraction/tolerances are not supplied, so the optional entry is informational, not an invented compliance certification.
6. Challenge Lightning front tolerance±30%, tail±20%, crest±3%; Switching peak200–300µs, tail2000–3000µs, crest±3%. These are source-tagged challenge rules, not universal IEC compliance claims.
7. Briefing describes front as30–90 rise and tail as100–50 fall informally. Use Lightning virtual-front1.67*(t90-t30), virtual-origin tail; Switching challenge uses peak time and half-value from physical start. Display the definitions.
8. Efficiency must not be counted twice. Workbook defines charge through efficiency then asserts target crest; enhanced circuit derives its crest with one explicit efficiency factor. An enhanced result is distinct and can disagree with the benchmark.
9. Briefing BIL1550kV example and workbook1425kV are not an authoritative catalog. Preserve input and optional user reference comparison; never label sample equipment values as standards.

## Expert expectations mapped to implementation

- 6:07–6:48: reduce trial shots and physical resistor/stage changes; return stage/charge/front/tail and rank setup complexity.
- 6:48–8:52: test C, divider C, stray C/L, layout and grounding affect results; configurable parasitics, uncertainty and configuration identity.
- 7:06–7:21: physics feasible settings, residual correction, ratings and tolerances; preserve the full chain.
- 8:19–8:36: practical laboratory significance comes before ML branding.
- 8:59–9:32 and22:03–22:41: usable defaults for less-experienced users and exact series/parallel resistor plans, with assumptions visible.
- 10:13–11:54 and20:33–20:51: reproduce weighted kNN, compare stronger regressors locally with documented tuning and metrics.
- 14:04–18:00: both challenge waveforms and RLC explanations.
- 23:32–24:18: wrong-voltage/BIL checks; reject hardware violations and flag unsupported training inputs.
- 24:41–25:37: explain tuning and the behavior of R,L,C.
- PDFp4: real measured waveforms needed for calibration and validation; demo sample must remain synthetic.

The briefing opening2:34–2:48 says onsite work10–11October; user readiness deadline is10October2026. No separate numerical judging rubric was provided.

## Discovered validation-table discrepancy (explicit acceptance exception)

The displayed case and all1400 ML Helper distances/weights reproduce the cached workbook. However, exact formula evaluation on the300 rows labeled Validation yields MAE[0.815373028962,12.114165288224,4.039247248702], RMSE[1.334613494179,19.913511096431,4.844687368114], rather than the hardcoded Model Validation table above. Inverse-Euclidean and uniform weighting alternatives also do not reproduce the published table. No Hidden Test output was consulted to diagnose this. The table contains static numbers without a reproducible evaluation script or per-row predictions. Exact published-table parity therefore remains unresolved; we do not claim it passed. Formula/cached-cell parity is the executable baseline gate. Subsequent comparisons use the recomputed baseline on unchanged official splits. This documented source contradiction replaces an impossible silent acceptance claim, and must be raised with the organizer.
