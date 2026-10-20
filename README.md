# GridContainmentWitness

An AI-assisted prototype for exact point classification in a frozen **synthetic abstract integer grid** region with holes. It provides source-bound INSIDE/OUTSIDE/BOUNDARY receipts and a separate owner activation/revocation lifecycle for each requested point. It is not geography, a geofence for real travel, surveying, navigation, property title or a safety decision.

**Local only:** no deployment, publication, live consensus or audit. Zero constructor arguments fix the deployer as owner. Source: `grid_containment_witness.py`. Synthetic fixture `test_url` is an unpublished HTTP mock; `public_url` remains null.

## Strict geometry

Source is exactly `{ "outer": [[x,y],...], "holes": [ring,...] }`. Outer has3..16 unique vertices,0..2 holes each3..8, total<=32. Every coordinate is an exact integer in±1e6, never boolean/float. Rings omit the repeated closing vertex; closing edges are implicit. Duplicate vertices, zero area, non-adjacent crossing/touch and adjacent overlapping backtracking are rejected. Straight-through collinear intermediate vertices are permitted.

Holes must be strictly inside the outer ring. Checking vertices alone is insufficient for a concave outer region: every hole edge is also checked against every outer edge. Holes cannot cross/touch the outer boundary, cross/touch each other, or nest. A separate test has all three triangle-hole vertices inside a U-shaped outer ring but an edge crossing the notch; it is rejected. Pairwise nesting and side-interior touch counterexamples are included.

All orientation, on-segment tests, inclusive segment intersections and signed shoelace areas are exact integers. Ray crossing uses a half-open y test and compares orientation/dy signs without floating-point division. Any outer or hole edge/vertex is BOUNDARY. Outer exterior or hole interior is OUTSIDE. All remaining points are INSIDE. Boundary classification is orientation-independent.

Canonical outer orientation is counterclockwise, holes clockwise; each ring starts at its lexicographically smallest coordinate; holes sort by full canonical ring tuples. Reversal, starting vertex and hole order cannot change the canonical geometry hash. This is not general geometric simplification: adding a redundant straight-through vertex can change the canonical geometry hash. Different source formatting/order still has a different exact byte SHA and a distinct source/domain-bound certificate even when canonical geometry matches.

## Consensus and authority

The validator independently retrieves fresh source bytes, verifies SHA256/strict JSON, validates complete topology, canonicalizes all rings and recomputes point classification and canonical geometry hash. It compares the full canonical packet and immutable call binding, not a leader's schema or classification label. Captures bind protocol, chain, contract, owner, region/query IDs, source URL/hash, exact point, registration/request/classification timestamps and actual classifier. No LLM is used.

Registration locks the source declaration; it does not claim that source is valid or available. Classification is permissionless execution **after owner reservation of a point/query ID**. This extra reservation prevents strangers from consuming the owner's finite history slots. A caller cannot substitute a different point. Permissionless execution does not grant activation authority. Each query has its own certificate and lifecycle; withdrawing one does not affect other points.

## Interface

| Method | Effect |
|---|---|
| `register_region(region_id,source_url,source_sha256)` | Owner only, unused immutable region ID; at most8 lifetime regions. |
| `request_query(region_id,query_id,x,y)` | Owner only; locks unused per-region query ID/point; REQUESTED revision0. At most32 lifetime queries per region. |
| `classify(region_id,query_id,x,y) -> str` | Anyone, exact pending reserved point; independently fetches/validates/classifies; CERTIFIED1; returns certificate ID. |
| `activate(region_id,query_id,expected_revision,certificate_id)` | Owner only; exact CERTIFIED1 certificate -> ACTIVE2. |
| `revoke(region_id,query_id,expected_revision,reason)` | Owner only; any non-revoked query -> terminal REVOKED at revision+1; reason1..200 trimmed public characters. Works offline. |
| `get_region(region_id)`, `get_query(region_id,query_id)` | Locked source, canonical geometry after first classification, fixed point, attestation, state/revision/history and timestamps. |
| `is_active(region_id,query_id,certificate_id,expected_revision)` | Current ACTIVE matching certificate/revision. Unknown query reverts. |
| `get_configuration()` | Owner/protocol, all finite limits and synthetic coordinate-domain notice. |

IDs are ASCII `[A-Za-z0-9_-]{1,32}`. Byte digest is lowercase64-hex. URL is exact `https://raw.githubusercontent.com/<owner>/<repo>/<40 lowercase hex>/<path>`, with no queries/credentials/ports/mutable refs or empty/dot file-path segments. Source body1..16384 bytes. Duplicate JSON keys, NaN/Infinity, extra fields and invalid bounds fail.

Record/query IDs never reset or recycle, even after revocation. Queries have at most4 phase events. Expected revision is an exact integer; a stale revision or another query's certificate cannot activate. First successful classification also locks canonical geometry under the region's already-fixed source hash; later point receipts must match it. Each query classifies once. Source failure preserves REQUESTED state, permitting later valid execution or owner offline withdrawal.

**ACTIVE does not mean INSIDE.** Any of the three correct classification results can have an active witness. Integrators must check exact region/source/point, current status/revision/certificate **and** the classification required by their own policy. Activation accepts the historical observed-byte receipt; it does not refetch continuously or create real-world access authorization. Revocation keeps history but invalidates current active status. Corrected source requires a new region ID; old point receipts need explicit revocation if the owner wants to retire them.

Typical calls: owner registers published region -> owner `request_query("r","q",2,2)` -> anyone `classify("r","q",2,2)` -> owner reads exact result and `activate("r","q",1,certificate)` -> integrator checks current witness plus classification. The demo square0..10 with a square hole3..7 classifies(2,2) INSIDE,(5,5) OUTSIDE,(3,5) BOUNDARY, and(0,0) BOUNDARY.

## Reproduce locally

Python3.12, isolated environment, no browser/wallet/RPC:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe tools\verify.py
```

Verifier resolves official GenVM **v0.2.12**, runner `1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`, stdlib `11rhn002yfajawsz7fai6mykznbxkxs6l91iskj5cm82c92qhy3v`, runs the entire actual direct suite, full official lint/semantic and ABI schema extraction. Dependencies pin genlayer-test0.29.2, genvm-linter0.11.0, cloudpickle3.1.2. Public SDK artifacts may download on first setup. `tests/conftest.py` contains only Windows fd0 cleanup and official warp-metadata compatibility; it replaces no geometry, state or validator code.

HTTP responses are explicit synthetic/adversarial mocks; actual source/storage/calldata/authorization/clock and captured validator closures execute. Literal expected classifications and metamorphic reversal/rotation checks do not run a host substitute geometry engine. Evidence preserves35 initial actual assertion failures on an empty deployable API. The initial canonicalization test then correctly rejected an old fixture response because official mock_web appends responses; the test transport now clears the prior mock before changing bytes (`tdd-transport-fixture-red.log`). Deliberately relaxing hole-count and hole-vertex bounds caused2 real regression failures; the original source was restored before full verification. Final suite/version/source hash and full lint/schema results are under `evidence/verification.json` and logs. No live gas, deployment or network-consensus results are invented.

`fixtures/region.json` is original MIT synthetic data. `fixtures/source.json` reports test-only unpublished URL, exact local digest and `public_url:null`, `live_source_verified:false`. Root must publish a fixture and use its actual immutable public URL and exact published bytes before any live demo. No source publication occurred here.

## Threat and scope limits

Input authors can choose misleading abstract shapes; hashes verify bytes, not property boundaries, real locations, survey accuracy, consent or travel safety. All coordinates and reasons are public; no private/precise real location data should be submitted. Integer bounds, SHA collision resistance, chain observation time and GenLayer consensus are assumptions. Response-size checks occur after fetch; pinned SDK exposes no pre-download cap or final-URL/redirect control. Source disappearance can prevent future classifications, while activation/revocation remain historical local state operations. Finite owner-only reservations are permanent even when withdrawn; capacity is not recycled. Worst-case live VM gas is unmeasured. This independent IC shares only basic SDK/testing/JSON primitives, not another counted contribution's business core.

## Verified local result

Final full-package actual SDK suite: **38 passing tests**. Full official lint/semantic and schema extraction exit0; ABI constructor has no parameters. Source hash is recorded in evidence/verification.json and CONTRIBUTION.json. Read-only frozen-source review by `/root` closed with no important reproducible findings; scope and limits are in `evidence/independent-review.json`. Closing the review changed only documentation and packaging, without rerunning tests or changing source. This is local prototype review, not an audit or live verification. No deployment/publication/live evidence is claimed.


## Commit locator namespace repair (2026-10-21)

The prior local source SHA256 `832ba181d2c115b72d32864409ed62e8a3764949475a535fd4b0a9014923cf26` is superseded by `a6804d583ac461e92398a7f37bb6cc6b575cabb1f56745fa9f1326f5415487b1`. Literal repository `.` and `..` segments are now rejected before registration or fetching, alongside the existing path restrictions. Legitimate `.github`, `repo.name` and `_repo` names remain accepted. The previous defect concerned the declared repository/commit locator under dot-segment URL normalization; exact expected SHA256 byte checks remained effective. No arbitrary-byte bypass is claimed.

The actual public SDK API regression first produced 2 failures and 3 valid-name passes. The repaired full suite has 43 passing tests, full semantic validation and schema extraction succeed on GenVM v0.2.12, and the extracted public schema is byte-identical. See `evidence/namespace-fix.json`, `namespace-red.log` and the current `verification-*.log`. Previous counts/reviews describe their frozen historical candidates; Root independently reviewed this narrow correction and closed it after the fix; see `evidence/namespace-final-review.json`. No deployment or live exploit is claimed.


## Recorded Studio constructor deployment

Deployment.json records FINALIZED/SUCCESS on free GenLayer Studio61999, NORMAL full consensus, value0 and exact source-byte readback. This is constructor verification only; the public-source containment assessment/activate/revoke lifecycle has not been exercised live. Earlier deployment/null notes and logs refer to the frozen local candidate. No portal submission, acceptance, real geographic results or audit is claimed.
