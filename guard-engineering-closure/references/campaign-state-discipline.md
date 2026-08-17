# Campaign State Discipline

Use this protocol to keep a long engineering campaign aligned across Git changes, context compaction, handoffs, caches, concurrent activity, and delayed instructions. Keep it ephemeral; do not create another project task system or evidence ledger.

## Contents

- Freeze the Campaign Baseline Tuple
- Use Git without turning it into task management
- Bound context and tool output
- Recover after compaction or handoff
- Classify conflict and drift
- Reconcile without broad rediscovery
- Keep cache and campaign state separate
- Map non-Git projects
- Stop reasons

## Freeze the Campaign Baseline Tuple

Before mutation, recovery, delegation merge, or a long validation, capture only:

```text
target
stop_point
workspace_identity
repository_identity_or_manifest
HEAD_or_change_generation
dirty_path_set_identity
planned_allowed_path_set_identity
closure_item_ids
authority_revision
highest_validated_layer
active_process_identity
verification_key
execution_purpose
```

Use existing identities. Prefer repository path plus Git HEAD, changed-path tokens, and a predeclared allowed-path token set, or a project-native package, migration, dataset, or artifact manifest. Current dirty paths describe state; planned allowed paths describe mutation authority. Do not conflate them or introduce a new source identity merely for this tuple.

The tuple is a scheduling checkpoint, not canonical project evidence. Keep it in the in-memory Closure Card or an ephemeral guard snapshot outside the repository. Reuse it until a named state-changing event invalidates it.

## Use Git without turning it into task management

Use Git for:

- repository and worktree identity;
- clean blob/tree reuse;
- changed-path and bounded-diff inspection;
- detecting HEAD or worktree drift;
- separating current changes from unrelated user changes.

Do not use Git to:

- replace closure-item or authority state;
- create one commit per test, heartbeat, audit, or evidence event;
- infer scientific, migration, release, or production authority from a branch or commit message;
- auto-create a branch, commit, stash, reset, rebase, checkout, or clean operation without user authorization;
- hide a dirty worktree by committing unrelated user changes.

Inspect `git status`, `git diff`, and existing object IDs before reading full files. Preserve unrelated modifications. If branch isolation would materially reduce conflict, propose it before mutation; do not silently reorganize the user's repository.

Treat a changed HEAD as `WORKTREE_DRIFT` unless it is the planned checkpoint just completed. A newly dirty path is valid only when it was dirty at baseline or appears in the frozen planned set. Re-capture the baseline once after an authorized commit or source-generation transition. Do not continue with a stale baseline.

## Bound context and tool output

Keep the active Closure Card at 12 lines or fewer. Retain only facts needed for the next action:

```text
current item and status
allowed objects and changed symbols
baseline tuple identity
highest valid validation layer
active process
verification/reuse key
named invalidation reasons
reasoning outcome
consumed budgets
one next action
stop point
```

Use behavior budgets rather than an unreliable absolute token count:

```text
full_log_blocks_in_context = 0
full_payload_or_manifest_rows_in_context = 0
repeated_hash_values_in_context = 0
unchanged_file_restatements = 0
context_reconstruction_scans <= 1 per compaction
active_closure_card_lines <= 12
reasoning_capsule_rebuilds_without_invalidation = 0
```

Limit tool output at the call site. Keep counts, failed IDs, typed reasons, terminal markers, and short bounded diffs. Leave complete logs in their existing workspace; do not copy them into conversation or create a duplicate summary artifact.

Represent old or deferred work by item ID, disposition, and evidence location. Do not repeat the full rejected proposal, audit narrative, or historical event chain.

## Recover after compaction or handoff

Treat conversational context loss as an operational event, not a source invalidation.

1. Read the latest concise Closure Card or inherited summary.
2. Re-establish the workspace, active process, and baseline tuple using `FAST` checks.
3. Compare the tuple with existing Git/project identities.
4. Re-read only assertion-critical evidence whose conclusion is absent or invalidated.
5. Reuse the current Reasoning Capsule unless its signature, relevant evidence, or baseline changed.
6. Resume the one recorded next action.

Do not rerun validation, rehash unchanged bytes, reopen every file, restart a process, or generate a new inventory because context was compacted or an assistant turn changed.

If no trustworthy tuple or summary exists, return `CONTEXT_RECONSTRUCTION_REQUIRED` and perform one bounded reconstruction along the frozen producer-to-consumer frontier. Never use reconstruction as permission for repository-wide discovery.

## Classify conflict and drift

Use the narrowest applicable class:

- `WORKTREE_DRIFT`: repository, HEAD, worktree, or changed-path identity differs from baseline;
- `CONCURRENT_WRITER`: another writer or ambiguous active process can alter the same state;
- `SCOPE_DRIFT`: item, object, capability, public surface, or validation denominator expands;
- `AUTHORITY_DRIFT`: governed owner, value, protocol, policy, or revision changes;
- `VALIDATION_DRIFT`: validator, test list/implementation, runtime, or highest valid layer changes unexpectedly;
- `CONTEXT_RECONSTRUCTION_REQUIRED`: no trustworthy compact state can support the next action;
- `CACHE_IDENTITY_MISMATCH`: a cache or prior PASS does not match the exact reuse key;
- `INSTRUCTION_DRIFT`: a delayed, delegated, or new instruction conflicts with the frozen target or stop point.

Do not resolve conflict by majority vote, latest file mtime, longest audit, or another full scan. A later direct user instruction may supersede an earlier target, but first state the scope, identity, and validation consequences and obtain any required rebaseline.

## Reconcile without broad rediscovery

At a writer-free checkpoint:

1. identify the exact tuple fields that changed;
2. name the event or actor that changed them when known;
3. inspect only changed hunks and declared direct dependants;
4. invalidate only affected conclusions, caches, tests, and downstream rows;
5. preserve unrelated PASS results whose exact keys still match;
6. update the Closure Card once;
7. continue, controlled-rebaseline, defer, or stop.

If the origin of a change is ambiguous, do not mutate. Stop with `CONCURRENT_WRITER` or `WORKTREE_DRIFT` until ownership is clear.

Require controlled boundary adjudication when reconciliation would add a root, path family, authority, capability, public contract, validation denominator, or another planned mutation tranche.

## Keep cache and campaign state separate

Treat cache as a disposable performance aid. Treat the Campaign Baseline Tuple as scheduling state. Neither is authority, evidence, or acceptance.

- A cache hit never updates proof state by itself.
- A cache miss never proves source drift.
- Context loss never invalidates a canonical artifact.
- A Git commit never activates authority.
- A sealed artifact identity may support reuse only through its existing sole validator.
- Trust boundaries always perform the required fresh canonical seal.

Use [verification-economy.md](verification-economy.md) for reuse classes, keys, invalidation, and diagnostic-prefix conditions.

## Map non-Git projects

Do not require Git where it is absent or non-authoritative. Substitute the project's existing identity:

- package lock or build manifest for a compiler/build;
- migration set and schema revision for a migration;
- dataset/schema version for a data pipeline;
- image digest and deployment spec for a deployment;
- artifact descriptor and transaction identity for a scientific or release workflow.

Keep the same tuple and drift logic. Do not create a manifest solely to satisfy this guard.

## Stop reasons

Use the narrowest reason:

- `WORKTREE_DRIFT_REBASE_REQUIRED`;
- `CONCURRENT_WRITER_STATE_AMBIGUOUS`;
- `SCOPE_DRIFT_REQUIRES_ADJUDICATION`;
- `AUTHORITY_DRIFT_REQUIRES_ACTIVATION`;
- `VALIDATION_KEY_DRIFT`;
- `CONTEXT_RECONSTRUCTION_BUDGET_EXHAUSTED`;
- `CACHE_REUSE_REJECTED`;
- `INSTRUCTION_CONFLICT_REQUIRES_REBASE`.

Do not create a project event or receipt merely because this ephemeral guard reports one of these reasons. Use the project's existing mandatory transition only when state must actually change.
