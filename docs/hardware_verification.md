# Hardware verification

`/hardware-verification/` exposes value, status, source, profile version and source interpretation for voltage, stages, capacitance, energy, stock, basic capacitance and auxiliary components. Pulse ratings, permitted mounting and physical connection constraints remain **UNKNOWN**. A supplied source is **SOURCE PROVIDED**, not independently **VERIFIED**. Missing source dates stay null.

Workbook ratings derived from `0.5 C V²` remain **DERIVED** mathematical values. Workbook application minimums and default base capacitance are **ASSUMED**. The PDF's 545 pF is source-provided with a prominent interpretation review; including it must not silently double-count divider capacitance.

The source conflict is preserved: workbook 15 stages / 3 µF per stage versus PDF 12 stages / 0.125 µF per stage. See [source reconciliation](source_reconciliation.md) for exact cells, figure and transcript sections. The incomplete briefing profile remains disabled. No profile borrows missing values from another.

`stock_for` still requires explicit counts and provenance when source quantities are unknown. Each proposed network uses counted stock and hard voltage/energy filters. This checks arithmetic constructibility, not pulse heating, mechanical fit, permitted mounting or laboratory approval. Obtain those facts from CPRI before physical use.
