# Bounded search quality

Run `python -m scripts.benchmark_search_quality` from the repository root. Development fixtures use `--split development`; their output is separate. Fixed fixtures and the predeclared scope live in `config/search_quality_cases.json`. These are generated engineering inputs, not supplied ML outcomes. No optimizer settings were tuned against the benchmark results.

The comparator independently enumerates every bridge-free series/parallel binary tree up to three parts from each counted stock. Rational arithmetic retains count vectors before reducing equal electrical equivalents to minimum-part representatives. All declared stage choices use the same production charging rule, physics, ML-off support policy, hard filters, objective, scenario envelope and final rank keys. Every exhaustive candidate receives scenario ranking; production retains its bounded shortlist. Post-ranking challenges remain separate and do not choose winners.

This comparison is exhaustive only in those declared discrete spaces. It does not enumerate bridge networks, arbitrary mechanical connections, continuous charging choices or every production-sized inventory. Physics-only mode isolates search behavior. Full default hybrid/agreement/circuit modes are outside this benchmark's claim.

The executed four-case report in `artifacts/search_quality/summary.json` records top-1 and top-3 matches, exhaustive rank of the bounded winner, objective gap, waveform error/metric differences, part-count differences, timing, evaluated counts and waveform margin loss. All four bounded winners matched; objective gaps were zero. This modest sample is not a global guarantee or laboratory success rate. Some controlled cases fail waveform checks in both searches, and the per-case report retains those failures.

Objective gap is subordinate to the nominal/robust rank keys; a negative scalar gap would not alone mean a better final rank. Runtime depends on machine and cache effects. API `/api/search-quality` reads the saved report or returns **PENDING**, never invented numbers. The UI repeats the scope and exposes case counts/results.
