# Recommendation evidence levels

Classification is deterministic and separate from ranking. The level describes the highest recorded evidence activity, **not a cumulative safety score**. All individual checks remain visible. In particular, a measured calibration does not erase circuit disagreement or establish good accuracy.

| Level | Exact condition |
|---|---|
| 0 Physics estimate | Default; no stronger condition met |
| 1 Synthetic ML supported | Full runtime synthetic support (`trust_weight == 1`) |
| 2 Dual-model agreement | Primary and independent circuit nominal checks both pass |
| 3 Scenario challenged | Both nominal checks pass and all recorded fixed-setting challenges pass, with more than one distinct scenario |
| 4 Locally calibrated (measured) | A matching scoped correction actually applied from a measured-lab source with a calibration ID |
| 5 Independent measured evaluation available | A saved evaluation contains this exact run/candidate and passes a fresh raw-file/quality/ancestry evaluation check |

Levels 2–3 do not require ML: an OOD physics configuration can have dual-model simulation evidence. Generated corrections never unlock level 4. Level 5 means errors were measured, not that errors were acceptable, the sample was randomized, or the model is generally validated. Review the evaluation's metrics and scope.

New recommendations save a classification after post-ranking challenge. Judge Mode overlays current intact evaluation links without changing the original run or reranking. Old records with missing facts remain unknown. Raw bytes, source type, exact run/candidate and model/layout groups prevent a generic measured count from unlocking the highest level.
