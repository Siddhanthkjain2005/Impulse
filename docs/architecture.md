# Architecture

```mermaid
flowchart TD
  A[Test request + equipment reference] --> B[Versioned generator profile + explicit inventory]
  B --> C[Reject voltage / energy / stock violations]
  C --> D[Workbook or independent RLC physics]
  D --> E[Bounded counted resistor / stage search]
  E --> F[Runtime support gate]
  F --> G[Supported synthetic residual correction or physics fallback]
  G --> H[Nominal limits + uncertainty / scenario shortlist ranking]
  H --> I[Saved ranked candidates]
  I --> J[Independent circuit + fixed-setting challenges]
  J --> K[Deterministic evidence card + Judge Mode]
  I --> L[Raw trial CSV + source / SHA-256 + acquisition review]
  L --> M[Scoped additive calibration]
  M --> E
  L --> N[New independent measured shots vs saved predictions]
  N --> O[Grouped error / decision metrics + immutable evaluation]
  O --> K
```

`backend/app/optimization/engine.py` owns feasibility, inference integration and ranking; the post-ranking verification never changes the ordering. `physics/` owns circuit/compliance/extraction. `ml/registry.py` loads frozen artifacts and gates correction. `storage.py` retains immutable local JSON records in SQLite; `IMPULSETWIN_DB` selects a different history.

`trial_provenance.py`, `trial_quality.py`, `trial_evaluation.py` and `evidence.py` separate origin, admission quality, independent scoring and presentation. `test_objects.py` checks catalog/operator references independently of generator capability. `hardware_integrity.py` presents source confidence without claiming verified hardware.

Next.js exports local assets served by FastAPI. Existing engineering screens and Judge Mode share one workspace and API. Timeline/search pages read executed artifacts; they never retrain in a request. Reports retain the original detailed engineering path. Release verification checks protected hashes, configuration/model consistency, automated tests, assets and a fresh isolated database with external network blocked.
