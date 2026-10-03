# Test-object references

`config/test_objects.json` is a versioned catalog with equipment class, system voltage, impulse type, optional requested test level, source/version and status. The two 400 kV insulator placeholders have **unknown** test levels. Neither the 1425 kV workbook example nor the 1550 kV briefing example is silently promoted to an equipment standard.

`POST /api/test-objects/validate` and optimization use the same validation function:

1. Reject disabled profiles, hardware voltage-range violations and requests exceeding active-stage/charging capability at the entered efficiency.
2. For a supplied reference, show the source and require explicit confirmation when the requested level differs by more than 3%. This is an application review threshold, not an IEC tolerance.
3. Without a reference, preserve the request and explain that only generator feasibility can be evaluated.

An operator-entered reference is **OPERATOR PROVIDED** and takes precedence for that request. It does not edit the catalog or become source-verified. A catalog impulse mismatch or unknown ID is rejected. Judge Mode exposes the reference, warning and confirmation checkbox; advanced inputs support operator source text. Existing engineering input validation remains available.
