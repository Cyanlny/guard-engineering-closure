# V9 Machine Contract

V9 is a snapshot veto, never authority or project acceptance.

## Preserve the public surface

Keep unchanged:

- `schema_id = ENGINEERING_CLOSURE_GUARD_SNAPSHOT_V9`;
- `closure_guard.py`, `closure_guard_core.py`, `closure_guard_selftest.py`, and `verification_economy.py`;
- snapshot/compare/self-test/accepted-rebaseline and V7/V7.1/V8 one-time import;
- commands/aliases, JSON/exit semantics, ordered violations/details, hash/activation/lineage, monotonicity, budgets, blocker/frontier, stage audit.

Judge applicability, whether a check is required now, and executable profile separately. Invoke only when the next action needs a V9 predicate and attributable facts bind stable closure/decision identity. Risk/complexity/repository identity/Git alone is insufficient. STANDARD/RESCUE control facts require project authority, not invented requests. First snapshots need no predecessor; later lineage requires a same-closure/campaign predecessor with valid hash/activation/lineage.

| Required check input | Invocation |
|---|---|
| Repository capture, not a substitute for required project control facts | `git` with `--repo` only |
| Project facts, optionally repository-bound | `generic` with `--facts`, optional `--repo` |
| Facts-select-generic, repo-only-select-git | `auto` |

`git` rejects `--facts`; `generic` requires them. Creating a new decision record adds its `DECISION` cost; exact decision reuse does not add it again.

Read and resolve the native control contract before governed subject access; read-only preview, parsing or hashing is not exempt from its prerequisites. Before dependent operations, confirm the required predicate in the actual output: command success, a valid snapshot, or no-veto alone is insufficient. If a required DECISION is absent, mismatches consumer/generation/authority, or has a veto, freeze the dependent operation. A later proof cannot authorize an earlier bypass. `NO_DECISION_REQUEST` is a gap only when the project requires that decision; it does not activate V9 for ordinary tasks. Snapshot/compare sequencing follows the predicate and lineage, not a mandatory extra compare.

## Keep proof sources explicit

| Source | Established meaning |
|---|---|
| `MACHINE_OBSERVED` | bytes, repo identity, CLI-read flags |
| `CALLER_ASSERTED` | caller-supplied authority, writers, operations, costs, blockers, stages |
| `V9_DERIVED` | normalization, hash, activation, lineage, delta, violation, recommendation |
| `PROJECT_ACCEPTED` | domain correctness, scientific validity, release/migration/production acceptance |

`MACHINE_ENFORCED` may veto; `BEHAVIORAL_INVARIANT` is not machine-proved; `PROJECT_ASSERTION` stays attributable. Caller facts require project authority; prompts or agent inference are not observations.

## Preserve lineage and interpret outputs narrowly

A snapshot binds normalized facts, schema, activation/hash, lineage, counters, blocker/frontier, authority, and applicable controls. Import preserves its one-time source; rebaseline carries history.

Retain one lineage per active decision key until closure. An unrelated post-veto baseline violates behavior even if both files validate.

- `ERROR`: malformed, incomplete, incompatible, or unevaluable input; correct once or stop.
- `BLOCKED`: an enforced invariant vetoes transition; obey its minimum legal next action and reconcile the boundary behaviorally.
- `PASS`/`CONTINUE`: no machine veto; still select one behavioral result.

Activate only capabilities supported by real facts. V9 may enforce budgets/attempts, monotonicity, blockers/frontier, authority/writer/operation, final release, control/stage shape, reuse/seal, and import/rebaseline limits.

## Prove every implementation change

For private refactors, compare valid/invalid V7/V7.1/V8/V9 stimuli. Preserve stdout/stderr, exit/status, recommendation, ordered violations/details, minimum action, exceptions, hashes, activation, lineage, import, and rebaseline. Run self-tests/golden corpus; keep baseline unless equivalence and reachable-code coverage are proved.
