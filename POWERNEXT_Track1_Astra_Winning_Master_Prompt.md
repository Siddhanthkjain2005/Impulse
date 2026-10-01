# POWERNEXT-AI 2026 — TRACK 1
# MASTER BUILD PROMPT FOR ASTRA

## Mission

You are acting as an elite multidisciplinary product-and-engineering team: senior high-voltage laboratory engineer, impulse-generator specialist, power-systems engineer, applied physicist, numerical simulation engineer, ML scientist, constrained-optimization engineer, data engineer, FastAPI architect, Next.js/TypeScript frontend engineer, UX designer, QA engineer, and technical-demo storyteller.

Build a complete, polished, technically defensible, offline-capable proof-of-concept named:

**ImpulseTwin AI — Physics-Guided High-Voltage Impulse Generator Optimizer**

for the PowerNext-AI 2026 Track 1 challenge:

**AI-Driven Optimisation of High-Voltage Impulse Generator Settings for 400 kV Insulator Testing**.

The application is a **decision-support digital twin**. It is not a direct hardware controller and must never claim to replace laboratory safety procedures or engineer approval.

The product must solve the real laboratory pain point: engineers currently estimate generator settings, perform reduced-voltage trial shots, inspect the waveform, physically change resistor arrangements/stages/settings, and repeat. The goal is to drastically improve the first recommended setup and reduce repeated trial-and-error.

The core product story must be visible everywhere:

> **Physics defines what is possible. ML learns the lab-specific residual left by simplified physics. A constrained optimizer searches only hardware-realizable settings. Uncertainty/OOD logic tells the engineer when the ML correction is trustworthy. Trial-shot feedback closes the loop.**

Do not build a generic ML dashboard. Build an engineering tool that a CPRI high-voltage engineer could plausibly take into the lab.

---

# 0. SOURCE-FIRST RULE — DO THIS BEFORE CODING

You will be given at least these official/supplied sources:

1. `HV IG Problem Statement.pdf`
2. `Hybrid_Physics_ML_Impulse_Generator_Optimiser.xlsx`
3. Track 1 briefing-session transcript/markdown if present

Before implementing the product, inspect every source and create:

`docs/source_reconciliation.md`

This document is mandatory and must contain:

- all generator ratings and constraints in the PDF;
- all defaults, formulas, inventory values, dataset columns, model logic and metrics in the workbook;
- all practical expectations stated by the CPRI expert in the briefing;
- every contradiction between PDF, workbook and transcript;
- the design decision used to preserve rather than hide each contradiction;
- provenance for each parameter.

### Critical source contradiction that must be handled correctly

The supplied materials describe more than one generator representation/configuration.

The PDF technical figure appears to describe a HAEFELY-style profile with approximately:

- maximum charging/output rating around 2400 kV;
- 12 stages;
- 200 kV stage voltage;
- 2.5 kJ stored energy per stage;
- 30 kJ maximum stored energy;
- impulse capacitance per stage around 0.125 µF;
- lightning and switching waveforms 1.2/50 µs and 250/2500 µs;
- separate practical resistor values for front/tail functions;
- base/load capacitance around 545 pF;
- sphere-gap and other fixed generator data;
- software support requirement approximately 50 kV to 2400 kV with a minimum of 2 active stages.

The briefing verbally discusses a roughly 3 MV, approximately 15-stage machine, with around 200 kV per stage.

The spreadsheet reference calculator uses its own simplified defaults, including 15 maximum stages, 200 kV maximum stage voltage and a 3 µF stage-capacitance input.

**Do not merge these into one fake machine.** Build a versioned **Generator Profile Registry** and keep them separate, e.g.:

- `cpri_problem_brief_profile`
- `workbook_reference_profile`
- `briefing_3mv_profile` if sufficient verified details exist

Unknown/ambiguous values must stay unknown or configurable. Never invent a precise hardware specification to fill a gap.

---

# 1. WHAT THE PRODUCT MUST DELIVER

For a selected generator profile and test setup, the user must be able to enter:

- impulse type: Lightning or Switching;
- desired crest/test voltage;
- test-object/insulator capacitance;
- measuring-divider/system capacitance;
- estimated stray capacitance;
- stray/connection-loop inductance;
- expected efficiency;
- any known connection/layout configuration;
- optional uncertainty ranges for poorly known parasitics;
- optionally available resistor inventory overrides.

The system must return at least:

- active generator stage count;
- charging voltage per stage;
- stage utilization;
- practical front-resistor setting/network;
- practical tail-resistor setting/network;
- component counts and series/parallel arrangement where applicable;
- expected front time / peak time;
- expected tail / time-to-half value;
- expected crest voltage;
- predicted waveform array;
- target waveform array;
- compliance status with numeric deviations and tolerance limits;
- top alternative feasible settings, not only one result;
- reason for ranking;
- voltage/energy/operating margins;
- confidence / prediction interval;
- out-of-distribution / training-support indicator;
- explanation of physics prediction versus ML correction;
- saved report suitable for carrying to a laboratory setup discussion.

The application must support both challenge waveforms:

- Lightning: **1.2/50 µs**
- Switching: **250/2500 µs**

and the practical generator voltage range required by the selected profile.

---

# 2. BRIEFING-SPECIFIC EXPECTATIONS — TREAT THESE AS PRODUCT REQUIREMENTS

The CPRI expert emphasized that the significance of the project is the **practical laboratory problem**, not merely the presence of ML.

Therefore the software must explicitly address:

1. Repeated physical changes of front/tail resistors and related setup work.
2. Dependence on R, L and C behavior and on actual physical test arrangement.
3. Prediction of stage count, front resistance, tail resistance, charging voltage and resistor combinations.
4. Hardware-realizable series/parallel resistor combinations.
5. A workflow simple enough for a user who does not already know every internal generator parameter.
6. Improving accuracy beyond the supplied weighted-kNN proof of concept.
7. Comparing multiple regression models and documenting tuning/metrics.
8. Detecting obviously wrong/suspicious requested test voltage or BIL input instead of blindly producing an answer.
9. Supporting both lightning and switching tests.
10. Remaining explainable and useful in an offline/local environment.

Do not reduce the challenge to “train a model to get a high score.”

---

# 3. REPRODUCE THE SUPPLIED WORKBOOK EXACTLY FIRST

Before advanced work, programmatically ingest `Hybrid_Physics_ML_Impulse_Generator_Optimiser.xlsx`.

Preserve all source sheets and create versioned exported artifacts from them.

Expected workbook roles include:

- `Hybrid Calculator`
- `Resistor Inventory`
- `Synthetic Dataset`
- `ML Helper`
- `Model Validation`
- `Model Card`

Create scripts such as:

- `backend/app/data/ingest_workbook.py`
- `backend/app/data/workbook_reference.py`
- `backend/app/data/validators.py`

Export cleaned, versioned representations such as:

- `data/processed/synthetic_dataset.csv` or parquet
- `config/generator_profiles/*.yaml`
- `config/resistor_inventory.yaml`
- `artifacts/reference_workbook_snapshot.json`

## 3.1 Exact dataset schema

Preserve the supplied 22-column schema exactly:

`ID, Split, Impulse_Type, Test_kV, Load_C_pF, Divider_C_pF, Stray_C_pF, L_uH, Efficiency, Stages, Charge_kV_Stage, Front_R_Stage, Tail_R_Stage, Physics_FrontPeak_us, Physics_Tail_us, Physics_Crest_kV, Observed_FrontPeak_us, Observed_Tail_us, Observed_Crest_kV, Residual_FrontPeak, Residual_Tail, Residual_Crest`

The supplied dataset contains **2,000 synthetic records** with:

- Train: 1,400
- Validation: 300
- Hidden Test: 300
- Lightning: 1,000
- Switching: 1,000

Preserve these split labels. Do not reshuffle and then call a new split the official hidden test.

## 3.2 Reproduce the weighted-kNN baseline

Reimplement the workbook’s weighted k-nearest-neighbour residual regression with **k=7** and the workbook’s exact distance normalization/weighting.

The architecture is:

`hybrid prediction = physics prediction + predicted residual`

Residual targets:

- front/peak-time residual;
- tail-time residual;
- crest-voltage residual.

Create an automated parity test that reproduces the workbook’s published validation metrics to a small tolerance.

## 3.3 Golden workbook case

Create a regression test around the displayed Lightning case:

- required test voltage: 1425 kV
- load capacitance: 850 pF
- divider capacitance: 500 pF
- stray capacitance: 150 pF
- stray inductance: 18.5 µH
- efficiency: 0.82
- maximum stages: 15
- maximum stage voltage: 200 kV
- workbook stage capacitance: 3 µF

Reference spreadsheet output is approximately:

- total load capacitance: 1500 pF
- required stages: 9
- charging voltage per stage: 193.0894 kV
- selected front resistance: 50 Ω/stage
- selected tail resistance: 25 Ω/stage
- physics front time: 1.21003 µs
- physics tail time: 52.20889 µs
- hybrid front: 1.20490 µs
- hybrid tail: 51.96371 µs
- hybrid crest: 1432.9466 kV
- feasible: YES
- waveform compliant: YES

Do not proceed to “better” models until this parity gate passes.

---

# 4. DATA AUDIT — THIS IS A MAJOR DIFFERENTIATOR

Create `reports/data_audit.html` and `docs/data_audit.md`.

The supplied synthetic data is useful as a benchmark but has important limitations that the product must handle honestly.

Audit and visualize:

- ranges and distributions of every feature by impulse type and split;
- correlations and leakage checks;
- unique stage/resistor combinations;
- profile compatibility;
- residual distributions;
- whether all synthetic rows are already compliant;
- coverage of the full hardware operating range;
- distance between a requested input and training support.

Important observations that should be verified programmatically:

- the synthetic set is concentrated in a narrow voltage region rather than the full approximately 50–2400 kV machine range;
- Lightning data is around the high-voltage insulator region, while Switching data is around another narrow region;
- some resistor values in the synthetic/workbook representation do not correspond literally to the PDF hardware inventory;
- the workbook model card explicitly says laboratory validation is still pending;
- the supplied overall R² values can be visually impressive because Lightning and Switching time scales are radically different.

### Never use one pooled R² as the headline result

A diagnostic reconstruction of the workbook kNN on the supplied Validation split shows why this matters. The pooled workbook-style R² values are around 0.9999 for the time outputs, yet when evaluated *within each impulse regime* the same residual kNN is much less impressive: Lightning tail R² is only about 0.28, Switching front/peak R² about 0.34, and Switching tail R² about 0.08. Physics-only already explains much of crest voltage, while several residual targets contain substantial noise. **Use these numbers only as a diagnostic to be reproduced from source, not as immutable ground truth.**

This means the winning solution must not chase a cosmetically huge pooled R². It must demonstrate improvement over physics within each regime, preserve physical feasibility, reduce false-pass risk, and be honest when synthetic residuals do not contain enough learnable signal.

Report model performance separately for:

- Lightning front time
- Lightning tail time
- Lightning crest
- Switching peak/front time
- Switching tail time
- Switching crest

Also report pooled values only as a secondary reference.

The reason is simple: approximately 1.2 µs and approximately 250 µs live on very different scales, so pooled R² can hide weak within-regime behavior.

### Stress-testing dataset

Create a second dataset for engineering stress tests and optimizer/compliance QA. It must be clearly labeled:

`source_type = generated_stress_test`

Use it to exercise:

- near-tolerance cases;
- outside-tolerance cases;
- extreme but physically allowed load capacitances;
- varying stray C/L;
- different stage counts;
- impossible resistor inventory requests;
- machine-boundary voltages;
- OOD inputs.

Do **not** mix this dataset into official benchmark claims. Do not present synthetic stress cases as lab measurements.

---

# 5. GENERATOR PROFILE REGISTRY

Implement typed, versioned generator profiles.

Each profile should support at least:

- profile id, display name, version;
- provenance/source document;
- overall voltage rating;
- minimum/maximum active stages;
- rated stage voltage;
- stage capacitance / impulse capacitance;
- stored energy per stage and total energy rating;
- charging resistor per stage;
- front resistor inventory;
- lightning tail resistor inventory;
- switching tail resistor inventory;
- optional external front/tail resistors;
- potential resistor;
- discharge resistors;
- basic generator/load capacitance;
- connection possibilities;
- sphere-gap metadata;
- pulse repetition constraints;
- efficiency defaults/ranges;
- notes and unresolved uncertainties.

Use YAML/JSON configs with Pydantic validation.

The frontend must allow selection of the profile and show the provenance.

Never silently use a workbook value under the CPRI/PDF profile or vice versa.

---

# 6. PHYSICS ENGINE — TWO LEVELS

Create:

`backend/app/physics/`

with two deliberately separated solvers.

## 6.1 Solver A — Workbook Reference Physics

Reproduce spreadsheet equations exactly, including the same constants and conventions.

Document every constant such as 1.67 and 0.693.

This solver exists for:

- source parity;
- judge explainability;
- transparent baseline comparison.

Return all intermediate quantities, not only final outputs.

## 6.2 Solver B — Enhanced Equivalent-Circuit Digital Twin

Implement a more defensible equivalent-circuit model for waveform simulation.

Use an RLC/Marx equivalent formulation, double-exponential waveform model and/or SciPy numerical integration where justified.

Do not claim it is a full electromagnetic transient model.

Inputs should include:

- active stages;
- charge voltage;
- effective generator capacitance;
- load/test-object capacitance;
- divider capacitance;
- stray capacitance;
- stray inductance;
- front resistance network;
- tail resistance network;
- external resistors where applicable;
- efficiency;
- connection mode.

Return:

- time array;
- voltage array;
- crest voltage and crest time;
- front/peak time;
- time to half value;
- overshoot/ringing indicators where numerically meaningful;
- damping/solver diagnostics;
- energy and rating margins.

Use the same waveform-extraction code for simulated and measured waveforms.

---

# 7. WAVEFORM METRIC EXTRACTION

Create one reusable waveform-analysis module.

For Lightning, support interpolation-based extraction of:

- crest;
- rising 30% crossing;
- rising 90% crossing;
- virtual front-time construction used by the challenge/reference implementation;
- virtual origin where applicable;
- falling 50% crossing;
- tail/time-to-half;
- overshoot/ringing if available.

For Switching, implement the challenge-selected peak/front definition and tail/time-to-half definition.

Never estimate compliance from chart pixels. Use numeric samples.

For uploaded laboratory CSV files:

- require/match time and voltage columns;
- handle units explicitly;
- validate monotonic time;
- preserve raw values;
- detect polarity;
- baseline-correct only in a non-destructive processing layer;
- use interpolation for crossings;
- record preprocessing steps in metadata.

---

# 8. COMPLIANCE ENGINE

Compliance rules must be versioned configuration, not scattered `if` statements.

Create a challenge profile derived from the supplied workbook/briefing, with source metadata.

The supplied material indicates a Lightning target of 1.2/50 µs with approximately ±30% front tolerance and ±20% tail tolerance. The workbook also uses a crest-voltage tolerance around ±3%. The workbook applies a 200–300 µs window around the 250 µs switching front/peak target and ±20% tail around 2500 µs.

Treat these as **challenge reference rules** unless an exact external IEC edition is independently verified. Do not falsely label every tolerance as universally applicable IEC law.

**Standards-version nuance:** the hackathon explicitly requires Switching **250/2500 µs**, while the current IEC 60060-1:2025 revision introduced a new switching-impulse front-time definition and describes the standard switching impulse as **170/2500 µs**. Therefore, for judging, default to the supplied POWERnext challenge profile (250/2500) and expose the current IEC profile only as a separately versioned optional profile. Never silently change the challenge target. Likewise, keep challenge tolerances source-tagged rather than silently substituting newer IEC rules.

For every candidate return:

- target;
- predicted;
- lower bound;
- upper bound;
- absolute deviation;
- percentage deviation;
- PASS/FAIL;
- reason.

Overall PASS requires every hard waveform and hardware requirement to pass.

---

# 9. ML ENGINE — PHYSICS-GUIDED RESIDUAL LEARNING

The primary production approach must be residual learning rather than a black-box direct predictor.

For each waveform target:

`prediction = physics_prediction + ML_residual_correction`

## 9.1 Use separate models by impulse type

Train separate Lightning and Switching residual models unless validation clearly proves a shared model is superior.

This prevents scale mixing and simplifies interpretation.

## 9.2 Features

Use physically meaningful features such as:

- required test voltage;
- load capacitance;
- divider capacitance;
- stray capacitance;
- total capacitance;
- stray inductance;
- efficiency;
- active stages;
- charge voltage/stage;
- front resistance;
- tail resistance;
- physics front/peak prediction;
- physics tail prediction;
- physics crest prediction;
- generator profile id/configuration only when the data meaningfully supports it.

Do not include observed targets or derivatives that leak them.

## 9.3 Benchmark models

Mandatory benchmark set:

1. Physics-only / zero-residual baseline
2. Exact workbook weighted-kNN k=7 baseline
3. Ridge/ElasticNet
4. SVR with scaling
5. Random Forest
6. Extra Trees
7. Gradient Boosting / HistGradientBoosting
8. CatBoost/XGBoost/LightGBM only if dependencies are stable and they genuinely improve validation

Do not choose the fanciest model by name. Choose by validation behavior, stability, explainability and inference speed.

A strong likely strategy for this small tabular dataset is to compare a simple regularized model against a tree ensemble and optionally create a small validation-weighted ensemble.

## 9.4 Split discipline

Use:

- official Train for fitting/tuning;
- internal cross-validation inside Train for hyperparameters;
- official Validation for model selection;
- official Hidden Test exactly once after the pipeline is frozen.

Do not repeatedly inspect Hidden Test to tune the model.

## 9.5 Metrics

For every impulse type and every target report:

- MAE;
- RMSE;
- MAPE or SMAPE;
- R²;
- normalized RMSE relative to the target magnitude/tolerance;
- improvement versus physics-only;
- inference latency.

Also report engineering decision metrics on stress/real data where both PASS and FAIL cases exist:

- compliance accuracy;
- false-pass count/rate;
- false-fail count/rate;
- worst-case normalized error.

False PASS should receive a heavier penalty than false FAIL in safety-oriented ranking.

---

# 10. TRUST-REGION ML / OOD GATING — KEY WINNING FEATURE

Because the supplied dataset covers only a narrow part of the full hardware range, never extrapolate the ML residual with fake confidence.

Implement a training-support score based on scaled distance to the training manifold, e.g. nearest-neighbour distance, local density or another transparent metric.

Use this to create a **trust-region hybrid**:

- strong in-distribution support → use full ML residual correction;
- moderate support → shrink ML correction toward zero and widen uncertainty;
- weak/out-of-distribution support → fall back primarily to physics, flag LOW CONFIDENCE and recommend engineer review / reduced-voltage trial.

The UI must visibly distinguish:

- `Physics feasible`
- `ML in-distribution`
- `ML extrapolating`
- `Lab calibrated`

Never display a made-up “99.7% confidence” number unless it is mathematically defined and calibrated.

---

# 11. UNCERTAINTY

Add defensible prediction intervals using one or more of:

- split conformal prediction;
- bootstrap model ensemble;
- quantile regression;
- residual empirical intervals by impulse type.

Return an interval for:

- front/peak time;
- tail time;
- crest voltage.

Also calculate **robust compliance**:

- nominal PASS: point estimate is inside tolerance;
- robust PASS: prediction interval and configured parametric uncertainty stay inside tolerance;
- marginal: nominal passes but uncertainty overlaps a limit;
- fail: nominal prediction violates a hard limit.

This should be a major UI differentiator.

---

# 12. DISCRETE HARDWARE OPTIMIZER — HEART OF THE APPLICATION

Do not let the ML model output arbitrary resistor numbers and call them recommendations.

The optimizer must search only physical candidates constructible under the selected generator profile.

For each allowed stage count:

1. Compute charging voltage/stage.
2. Reject if stage/rating/energy limits fail.
3. Generate achievable front-resistor arrangements.
4. Generate achievable tail-resistor arrangements for the selected impulse type.
5. Include permitted series/parallel combinations.
6. Track exact component counts and inventory usage.
7. Reject prohibited connection modes.
8. Run reference physics.
9. Apply ML residual correction through OOD trust gating.
10. Estimate uncertainty.
11. Run compliance.
12. Run enhanced simulation on the best subset if full numerical simulation is expensive.
13. Rank all feasible candidates.

## 12.1 Resistor network search

Implement bounded combinatorial search / dynamic programming for resistor combinations.

For each network return:

- equivalent resistance;
- topology;
- list of component values;
- quantity required per stage / total;
- inventory feasibility;
- setup complexity.

Deduplicate near-identical equivalent values and cap topology depth to avoid combinatorial explosion.

## 12.2 Hard constraints

Hard-reject candidates for:

- voltage outside generator profile range;
- stage count outside allowed range;
- charge voltage above stage rating;
- energy above rating;
- unavailable resistor network;
- invalid component count;
- prohibited connection;
- nonphysical capacitance/inductance/efficiency;
- non-finite solver result.

Hard constraints must never be converted into merely a bad score.

## 12.3 Ranking

After hard filtering, rank with a transparent weighted objective using configurable terms such as:

- normalized front/peak deviation;
- normalized tail deviation;
- normalized crest deviation;
- uncertainty penalty;
- OOD penalty;
- operating-margin penalty;
- resistor/setup-complexity penalty;
- number of physical changes/components;
- robust-compliance margin.

Expose the score breakdown.

Return top 5 recommendations and a Pareto view for:

- waveform accuracy;
- setup simplicity;
- operating margin / robustness.

No opaque “AI score.”

---

# 13. ROBUST OPTIMIZATION AGAINST UNKNOWN PARASITICS

The PDF explicitly stresses that test-object capacitance, divider capacitance, stray capacitance, stray inductance, leads, physical layout and grounding can vary.

Allow the user to specify uncertainty ranges for these values.

For top candidates perform a small Monte Carlo / Latin Hypercube robustness simulation over the configured uncertainties.

Return:

- percentage of simulated scenarios that remain compliant;
- worst-case front/tail/crest deviations;
- most sensitive parameter;
- robustness ranking.

Do not invent uncertainty percentages and present them as standards. Use user-supplied/profile-labeled assumptions and make the assumptions visible.

---

# 14. BAD INPUT / BIL SANITY ASSISTANT

The briefing explicitly asks for protection against wrong test-voltage input.

Implement layered validation:

1. hardware-range validation;
2. numeric/unit sanity validation;
3. optional equipment/BIL reference validation;
4. ML OOD validation;
5. final user confirmation.

If an authoritative BIL catalog is not supplied, build the catalog framework but clearly label demo/sample records and source them. Do not invent standards data.

Never silently rewrite the requested voltage.

Examples:

- `Requested 2800 kV exceeds the selected 2400 kV profile. No recommendation generated.`
- `Requested voltage is within hardware range but far outside the ML training region. Physics-only/low-confidence recommendation shown.`
- `Entered test voltage differs from the selected equipment reference record. Confirm the applicable standard before proceeding.`

---

# 15. CLOSED-LOOP TRIAL-SHOT CALIBRATION — MAJOR DIFFERENTIATOR

Build a `Trial Shot Calibrator` workflow.

Flow:

1. Engineer generates recommendation.
2. Engineer performs the actual/reduced-voltage trial outside the software under normal lab procedures.
3. Engineer uploads analyzer CSV.
4. App maps time/voltage columns and units.
5. App extracts measured crest/front/tail.
6. App compares measured vs physics vs ML.
7. App stores measured residual with complete generator/test configuration.
8. App applies a transparent session/local calibration correction for the next recommendation.
9. App can queue the measurement for later approved model retraining.

Do not automatically retrain a production model from one shot.

Every dataset row/history item must carry:

`source_type = supplied_synthetic | generated_stress_test | measured_lab`

Metrics must never mix these invisibly.

Optional high-value extension: a **Next Best Adjustment** assistant that, after a measured miss, evaluates nearby feasible hardware candidates and recommends the smallest physical change most likely to bring the waveform inside tolerance.

---

# 16. EXPLAINABILITY

Every top recommendation must answer:

- Why this stage count?
- Why this charging voltage?
- Why these front/tail resistors?
- Which hard constraints were active?
- What did physics predict?
- How much did ML change each output?
- How trustworthy is that correction?
- What variable is the recommendation most sensitive to?
- Why was rank 1 chosen over rank 2?

For ML explanation use:

- coefficient view for linear model;
- SHAP for tree model if stable;
- permutation/local sensitivity fallback;
- nearest training cases for kNN/reference mode.

Also create a simple RLC educational sensitivity panel: vary one parameter at a time and show the predicted waveform effect, while clearly labeling it as a sensitivity view rather than a universal monotonic law.

---

# 17. BACKEND ARCHITECTURE

Use Python 3.11+ with:

- FastAPI
- Pydantic v2
- NumPy
- SciPy
- scikit-learn
- joblib
- SQLAlchemy/SQLModel + SQLite for demo
- optional XGBoost/CatBoost only if environment is stable

Suggested structure:

```text
backend/
  app/
    main.py
    api/
      routes_optimize.py
      routes_simulate.py
      routes_compliance.py
      routes_profiles.py
      routes_models.py
      routes_trials.py
      routes_runs.py
    core/
      config.py
      logging.py
    schemas/
    data/
      ingest_workbook.py
      validators.py
      provenance.py
    physics/
      reference_solver.py
      digital_twin_solver.py
      waveform_metrics.py
    compliance/
      standards.py
    ml/
      reference_knn.py
      features.py
      train.py
      evaluate.py
      registry.py
      uncertainty.py
      ood.py
      explain.py
    optimizer/
      resistor_networks.py
      candidate_generator.py
      constraints.py
      scoring.py
      robustness.py
      pareto.py
    services/
      recommendation_service.py
      trial_calibration_service.py
      report_service.py
    db/
      models.py
      repository.py
  tests/
  artifacts/
    models/
    metrics/
```

The backend is the single source of engineering truth. React must not reimplement formulas.

---

# 18. API CONTRACT

At minimum provide:

- `GET /api/health`
- `GET /api/source-status`
- `GET /api/generator-profiles`
- `GET /api/generator-profiles/{id}`
- `POST /api/simulate`
- `POST /api/optimize`
- `POST /api/compliance/check`
- `GET /api/models`
- `GET /api/models/{id}/metrics`
- `POST /api/explain`
- `POST /api/trials/upload`
- `POST /api/trials/{id}/calibrate`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/report`

Optimization response should include:

- exact profile/version;
- exact standards/challenge profile/version;
- exact ML model/version;
- input validation;
- top-N candidate list;
- settings and inventory plan;
- physics prediction;
- ML correction;
- final hybrid prediction;
- uncertainty;
- OOD support;
- compliance;
- robustness;
- score breakdown;
- explanation.

---

# 19. FRONTEND — ENGINEERING CONTROL ROOM

Use:

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- Plotly or ECharts for engineering plots
- Framer Motion only for restrained transitions

Avoid wasting time on a flashy 3D generator until the engineering workflow is complete.

The visual style should feel like a modern high-voltage control room: dark graphite/navy, clean instrumentation, readable units, restrained accent colors, and green/amber/red only for engineering status.

## Main Optimizer page

### Top bar

- ImpulseTwin AI
- generator profile selector
- challenge/standards profile selector
- model version/status
- backend/offline status
- demo preset selector

### Left — Inputs

Quick inputs:

- Lightning / Switching
- desired crest kV
- load C
- divider C
- stray C
- stray L
- efficiency

Advanced:

- uncertainty ranges
- connection mode
- resistor inventory override
- stage constraint
- profile details

Every input must show unit, range, provenance/default source.

### Center — Waveform canvas

Plot:

- target waveform
- physics waveform
- ML-corrected/hybrid waveform
- measured waveform when available
- tolerance corridor
- important front/peak/tail markers
- interactive cursor with time and kV

### Right — Ranked recommendations

Rank 1 card:

- PASS / MARGINAL / FAIL
- stages
- charge kV/stage
- front network
- tail network
- energy/voltage margin
- robust-compliance result
- confidence/OOD state
- concise explanation

Below show ranks 2–5 and comparison checkboxes.

### Bottom instrumentation

- front deviation
- tail deviation
- crest deviation
- voltage margin
- energy margin
- ML support/OOD
- robustness rate

## Other pages

- `/model-lab` — baseline vs candidate models, per-type metrics, residual plots
- `/profiles` — generator/profile/inventory management
- `/trial-calibrator` — measured waveform upload and feedback
- `/runs` — audit/history
- `/compare` — compare candidates

---

# 20. REPORT EXPORT

Generate a professional HTML/PDF-ready report containing:

- run id/date;
- generator profile/version;
- model/version;
- full inputs;
- top recommendation;
- alternate candidates;
- resistor component plan;
- waveform chart;
- compliance table;
- robustness/uncertainty;
- OOD state;
- explanation;
- disclaimer: decision support, engineer verification required;
- provenance of the challenge/source configuration.

---

# 21. TESTING AND QA

Tests are mandatory.

## Source parity tests

- workbook formulas reproduce expected outputs;
- weighted-kNN parity;
- default 1425 kV case parity.

## Unit tests

- units/conversions;
- waveform crossing interpolation;
- compliance boundaries;
- resistor equivalent calculations;
- inventory quantity checking;
- profile validation;
- hard constraints;
- OOD calculation;
- uncertainty interval formatting.

## Property/sanity tests

- no negative stage count;
- no negative resistance/capacitance;
- no recommendation above stage voltage rating;
- no unavailable inventory recommendation;
- finite simulation outputs;
- deterministic result for fixed inputs/model version;
- no hidden-test leakage.

## End-to-end tests

1. reference Lightning case;
2. Switching case;
3. out-of-range voltage rejected;
4. in-range but OOD case returns low-confidence physics-heavy result;
5. impossible inventory case explains failure;
6. trial CSV upload extracts waveform and calibration;
7. report export works.

---

# 22. REPRODUCIBILITY / DEV EXPERIENCE

Create one-command workflows:

- `make setup`
- `make ingest`
- `make train`
- `make test`
- `make dev`
- `make demo`

Pin dependencies.

Store model metadata:

- training dataset hash;
- feature list;
- hyperparameters;
- metrics;
- git commit where possible;
- created timestamp;
- source profile version.

The finale demo must run locally without dependence on external internet APIs.

---

# 23. PRIORITIES — DO NOT OVERBUILD THE WRONG THING

### P0 — must be finished first

- source reconciliation;
- exact workbook parity;
- generator profile separation;
- physics solver;
- exact kNN baseline;
- stronger ML benchmark with per-type metrics;
- discrete inventory-aware optimizer;
- compliance engine;
- OOD/trust gating;
- clean optimizer dashboard;
- top-5 recommendations;
- tests and offline run.

### P1 — winning differentiators

- uncertainty intervals;
- robust optimization over uncertain parasitics;
- trial-shot upload/calibration;
- model-lab comparison;
- audit history/report;
- bad-voltage/BIL sanity workflow.

### P2 — only after P0/P1 are stable

- next-best-adjustment/active-learning assistant;
- richer ODE simulation;
- advanced animated schematic/3D;
- more elaborate report styling.

Do not trade P0 engineering correctness for visual effects.

---

# 24. DEMO PRESETS

Create controlled demo presets with explicit source labels.

### Preset A — Workbook parity Lightning

Use the 1425 kV reference case and demonstrate that the app reproduces the supplied spreadsheet before improvements.

### Preset B — Switching

Use a switching case inside supplied data support and show 250/2500 compliance.

### Preset C — OOD but hardware-valid

Use a voltage/setup within the selected hardware profile but far outside the synthetic training region. The system must show:

- physics result;
- reduced/disabled ML correction;
- LOW CONFIDENCE/OOD warning;
- recommendation for trial validation.

### Preset D — impossible input

Use a requested voltage above the selected profile maximum. The system must refuse to optimize and explain why.

### Preset E — trial-shot correction

Use a sample measured waveform CSV clearly labeled as demo/synthetic unless actual data is provided. Show measured-vs-predicted error and next recommendation/calibration.

---

# 25. FINAL PRESENTATION STORY

The pitch should not start with model names.

Start with the lab problem:

> “Today, engineers calculate approximate impulse-generator settings, perform trial shots, inspect the waveform, and physically change resistor/stage settings until the waveform enters tolerance. Our system converts this into a physics-guided, hardware-aware optimization workflow.”

Then show:

1. supplied workbook reproduced exactly;
2. real generator profile and inventory constraints;
3. physics prediction;
4. ML residual correction and per-type validation;
5. top feasible hardware configurations;
6. waveform/tolerance compliance;
7. OOD/uncertainty protection;
8. trial-shot feedback closing the loop.

The final message is:

> “We are not replacing high-voltage engineering with a black box. We are encoding the engineer’s physics, hardware constraints and lab experience into a system that gives a much stronger first setup and learns from every measured shot.”

---

# 26. FINAL ACCEPTANCE CRITERIA

Do not declare the project complete until all of the following are true:

- the source reconciliation document exists;
- the workbook reference case passes numerical parity;
- exact weighted-kNN baseline is reproduced;
- model metrics are separated by impulse type and target;
- hidden test was not used for iterative tuning;
- at least one stronger model is fairly benchmarked;
- OOD/trust gating works;
- generator profiles are separate and provenance is visible;
- top recommendations are actually constructible from inventory;
- hardware constraints are hard filters;
- challenge waveform compliance is numeric and explainable;
- top 5 alternatives are ranked with visible score breakdown;
- waveform plot is based on numeric simulation/prediction;
- wrong/out-of-range inputs are handled safely;
- trial-shot calibration workflow works with a sample CSV;
- results are versioned/auditable;
- app runs locally/offline;
- unit and E2E tests pass;
- no fake lab-data claim;
- no fake precision/confidence;
- no TODO placeholders remain in the primary demo path.

---

# 27. HOW YOU MUST EXECUTE THIS BUILD

Do not respond with only a plan. Work through the repository and implement it.

At the end of each phase:

1. run tests;
2. show exactly what changed;
3. show the command to run it;
4. record unresolved assumptions in `docs/assumptions.md`;
5. update `PROJECT_STATE.md` with completed/in-progress/blocked items;
6. do not move on with silent test failures.

Execution phases:

- Phase 0: source inspection + reconciliation
- Phase 1: workbook parity + profile registry
- Phase 2: data audit + exact baseline
- Phase 3: advanced ML + honest evaluation
- Phase 4: physics/compliance engine
- Phase 5: inventory-aware constrained optimizer
- Phase 6: OOD + uncertainty + robustness
- Phase 7: trial-shot calibration
- Phase 8: frontend/control-room UX
- Phase 9: reports/history
- Phase 10: end-to-end QA + demo rehearsal

If a source fact is ambiguous, stop and record it instead of inventing it.

If a fancy feature threatens the stability of the core optimizer, defer the fancy feature.

The finished product should make a judge immediately see three things:

1. **You understood the real high-voltage engineering problem.**
2. **Your AI improves a physics baseline without becoming an unsafe black box.**
3. **Your application is designed to reduce actual laboratory trial-and-error, not merely produce an impressive metric.**
