# Judge Mode: a 4–6 minute walkthrough

Open `/judge/` after starting the local application. The existing engineering pages remain available.

1. **Problem:** explain analytical estimate → physical adjustment → trial → inspection → repeat.
2. **Request:** choose impulse, crest, source profile and object capacitance. Optional catalog references remain unknown until sourced. Advanced settings include parasitics, layout, explicit operator reference and counted inventory overrides. Confirm reference mismatches explicitly.
3. **Configuration:** show active stages, charge/stage, exact counted front/tail constructions, total components, energy and waveform metrics. Failed candidates remain diagnostic alternatives.
4. **Evidence:** inspect deterministic evidence level, support, model disagreement, fixed-setting challenges and uncertainty intervals.
5. **Alternatives:** compare actual minimum waveform-error cost, fewest parts and largest stage-voltage margin within the returned shortlist. Labels can share a candidate. Fewest parts is not fewest hardware changes; the existing Compare planner handles changes from a saved setup.
6. **Trial:** load a backend-generated demonstration for the selected candidate or upload an actual CSV. Generated feedback has a large explicit banner. Judge uploads assume `time_us`, `voltage_kv`, zero baseline/onset; use Trial calibrator for other acquisition mappings. Raw uploads and quality checks are the same backend workflow.
7. **Summary:** show actual run checks, measured count and matching evaluation availability. Finish with the engineering report and next laboratory evidence needed.

The browser uses `/api/optimize`, saved `/api/runs/{id}/judge`, and the existing upload/demo endpoints. No frontend predictions are hardcoded. Changing the request disables later steps until a new recommendation succeeds. Trial curves are filtered to the selected candidate. The backend labels alternative trade-offs from deterministic saved metrics.

Recommended next rehearsal: confirm source profile and inventory, demonstrate model disagreement and agreement search, show the generated-data badge, then explain the pending measured evaluation. Do not present software tests or model agreement as hardware certification.
