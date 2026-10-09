# Crash-Consistent Cutover

Owns crash/durability closure for authoritative replacement: barrier-dependent rename/replace/link/commit, multi-location staging, or its `RUNNING`/`UNKNOWN` recovery.

## Require project-native recovery proof before mutation

Reuse conforming project-native proof; never rebuild it for Guard. Otherwise the owner validates a `CUTOVER_RECOVERY_MATRIX` before mutation. Guard prescribes no format or authority.

Enumerate the operation and persisted checkpoints. Each reachable crash state has exactly one native row containing:

`case_id`, `checkpoint`, `authoritative_generation`, `old_presence`, `staging_presence`, `new_presence`, `exact_identity`, `path_safety`, `writer_lease`, `run_state`, `only_legal_action`, `durability_action`, `terminal_invariant`, `validator`, `fail_closed_reason`.

`exact_identity` may be digest, manifest, device-plus-inode, or other native identity; `only_legal_action` is singular and guess-free.

## Prove state, branch, test, and durability coverage

Prove bidirectionally by automation or attributable audit:

- each reachable crash state maps to exactly one row;
- each recovery branch maps to exactly one row;
- each row has at least one direct fault-injection and recovery test.

For each rename/replace/link/commit marker and decisive file/parent barrier, fail before mutation, after mutation before durability, and after durability. Repeatedly recover every state; lists and aggregate counts cannot prove idempotence.

Fail closed on path escape/symlink, unknown roles or bytes/identity/generation/writer/lease/transaction, mixed authoritative identities, competing active authorities in one consumer context, conflicting writers/leases, unmapped branch, or multiple legal actions. Physical coexistence alone is not conflict: native role and identity proof may retain rollback/evidence copies only when execution-forbidden and unreachable by active consumers. Directory names prove neither role nor isolation.

`RUNNING`/`UNKNOWN` permit only read-only reconciliation of the original transaction/object; never dispatch/recompute while it may exist.

## Admit only a legal terminal

Terminal is the uniquely selected native authority—legal old/new generation or another authorized state—not a single physical copy. Its validator jointly proves authority generation, identity, location and consumer selection, writer/lease, run state, durability, and seal.

Missing, list-only, incomplete, non-bidirectional, or durability-untested proof freezes mutation. Supply the decision owner with any finite plan, proof/validator-contract, or authorization-envelope change and its identifiable authority; effects need not expand. Expose unknown authority or unbounded safety as a stopping fact.

A cutover mutation is not an executable in-envelope route until necessity, authority, complete matrix, passing fault/idempotence tests, terminal validation, and fresh seal hold. Before then, an authorized, fully specified in-envelope validation can be the current executable route while mutation stays frozen; the decision owner arbitrates its formal result.
