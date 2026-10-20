# GridContainmentWitness design and test plan

AI-assisted local prototype over synthetic abstract integer coordinates. Zero constructor arguments; immutable deployer owner. Not real geography, travel advice, surveying, delivery or asset custody.

## Region and geometry

Fixed public source is strict JSON {outer:[[x,y],...],holes:[ring,...]}. Outer3..16 unique vertices;0..2 holes of3..8 vertices, total<=32. Coordinates are exact integers ±1e6, never booleans. No repeated closing vertex, duplicate vertices, zero area, non-adjacent self-cross/touch, or adjacent overlapping backtrack. Straight-through collinear vertices may remain. All holes must be strictly inside the outer ring, with no boundary intersection/touch, mutual boundary intersection/touch or nesting. Concave outer rings are supported. All calculations use integer orientation, segment intersection, shoelace area and half-open ray crossing; no float division.

Canonical outer orientation is CCW, holes CW. Rotate each ring to its lexicographically smallest coordinate, then sort holes by the complete canonical ring tuple. Thus rotation/reversal/hole order cannot change canonical geometry. Byte SHA still binds the exact source; equivalent geometry in differently formatted files has a distinct source-bound certificate.

## API, state and finite history

`register_region(region_id,source_url,source_sha256)` owner-only locks unused immutable source (max8 regions). `request_query(region_id,query_id,x,y)` owner-only reserves one of32 immutable per-region query IDs/points. This reservation prevents permissionless callers from exhausting another owner's bounded query history. `classify(region_id,query_id,x,y)->certificate_id` is permissionless but must match a pending reservation exactly. Leader and validator each fresh-fetch/hash/fully validate/canonicalize the region and independently derive the point result. Outer or any hole boundary means BOUNDARY; outer exterior or hole interior means OUTSIDE; the remainder means INSIDE.

Every query moves REQUESTED revision0 -> CERTIFIED1 -> ACTIVE2 -> REVOKED3, with one possible early terminal revocation. `activate(region_id,query_id,expected_revision,certificate_id)` and `revoke(region_id,query_id,expected_revision,reason)` owner-only use CAS. Region registration is never reset; a new point requires a new reserved query ID. Independent queries can have independent current certificates. `get_region`, `get_query`, `is_active`, `get_configuration` expose bounded immutable point/source/domain/history data. Certificate binds chain/contract/owner/region/query/point/source bytes and classified time. Classifier identity is recorded, not treated as physical authority. Activation refers to historical bytes; revoke remains offline.

## Plan and tests

1. Prepare synthetic fixture/test-only mock URL and real SDK tests against an empty contract, preserving genuine red output.
2. Check literal inside/outside/outer edge+vertex/hole edge+vertex, reversed/rotated canonical equality, negative/large integer coordinates and concave ray cases. Reject bowties, non-adjacent touch, zero area, closing duplicate, adjacent overlap, out-of-range/bool/NaN/duplicate JSON, hole outside/crossing/outer touch, holes overlap/touch/nest and vertex caps.
3. Verify fresh source404/drift rejection, fully shaped forged classification/point packets, query access/CAS/certificate binding, permissionless execution without slot squatting, replay/terminal state and bounded query capacity. No host-side substitute geometry implementation in tests.
4. Run entire package direct pytest on exact official GenVM v0.2.12, full lint/semantic/schema and zero-argument constructor, then docs/evidence/contribution manifest/safe ZIP and root frozen-source review. Live/deployment/publication remain null.
