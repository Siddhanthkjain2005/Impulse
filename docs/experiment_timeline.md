# Model experiment timeline

`/experiment-timeline/` reads saved registry, protocol and summary artifacts through `/api/experiment-timeline`. It shows model identity, hypothesis, comparator, dataset hash, protocol, measured development change, promotion criterion and decision. Each saved artifact carries its SHA-256; development protocols are checked against their recorded hash.

V1 remains the promoted/default model, with the original saved synthetic Hidden Test report. V2 remains explicitly experimental despite passing its development gate. V3, V4 and V5 remain rejected/non-promoted, with their unsuccessful results preserved. No V6 was created and no Hidden Test predictions were rerun for this feature.

V2–V5 percentages compare different development procedures and must not be added to V1's synthetic final-test improvement. The timeline labels those as **SYNTHETIC DEVELOPMENT CV**. For full statistical limitations see the original `accuracy_v*_results.md` documents. When an old protocol lacks a dedicated hypothesis field, the saved experiment name is displayed rather than manufacturing a research narrative.
