# Run-State Integrity

Use this protocol when a project has canonical run/stage state, an append-only event log, projections, checkpoints, retries, leases, or crash recovery. Keep the contract project-neutral; do not create a state platform merely to satisfy this guard.

## Contents

- Classify every state object
- Select one state authority
- Bind transitions and replay
- Make reads and writes atomic
- Migrate without inventing history
- Close terminal and recovery semantics
- Verify mutations

## Classify every state object

Assign exactly one role to every state-bearing object:

```text
AUTHORITY | PROJECTION | TERMINAL_EVIDENCE | LEASE
```

- `AUTHORITY` decides current state. Exactly one authority is permitted for a run.
- `PROJECTION` is deterministically rebuilt from the authority and never wins a conflict.
- `TERMINAL_EVIDENCE` is immutable evidence referenced by an authoritative event; it does not arbitrate current state.
- `LEASE` provides mutual exclusion only. It expires or is released and never represents a business state.

A status file, PID, mtime, newest receipt, request/result bundle, checkpoint, review, or decision cannot silently become a second authority. If an object's role is absent, ambiguous, or changes by reader, return `RUN_STATE_ROLE_UNRESOLVED`.

## Select one state authority

Choose exactly one:

- an append-only event chain is authoritative and current state is a deterministic projection; or
- one generationed compare-and-swap state document is authoritative and any history/index is derived.

Never allow an event log, current projection, checkpoint, receipt, PID file, and process exit code to become competing authorities. Record the authority kind, run/stage identity, generation or event head, transaction purpose, and sole transition validator.

When SQLite carries an append-only event authority, use one database per run unless an existing project contract owns a stronger partition. Keep one `state_events` chain with a global sequence, unique event hash, previous-event hash, run/scope identity, event type, and strict canonical payload. Reject `UPDATE` and `DELETE` with database triggers. Project-specific current-state tables remain projections.

If the authoritative field is absent or ambiguous, return `RUN_STATE_AUTHORITY_UNRESOLVED`. Do not infer current state from filenames, event names, mtimes, the newest receipt, or process-name matches.

## Bind transitions and replay

Require every transition to bind:

```text
run + stage + action + execution purpose
previous generation/event hash
next generation/event hash
source/request/runtime/transaction identities where applicable
one legal prior state and one legal next state
writer lease identity
typed terminal effect
```

For an event authority, require contiguous sequence numbers, previous-hash linkage, canonical event hashing over every event field except its own hash, unique event IDs, and deterministic replay. The payload binds expected/next state, generation, transaction, request/result/decision/terminal identities, and typed reason when applicable. Reject deletion, insertion, reordering, duplication, cross-run/scope swap, wrong previous hash, and self-consistent full re-signing outside the active authority.

For a state-document authority, require generation compare-and-swap and exact history consistency. A stale writer, repeated transition, terminal-to-running transition, or generation rollback must fail closed.

The current projection must equal a full replay of the authoritative state. A projection mismatch is not repaired by choosing whichever representation appears newer.

## Make reads and writes atomic

- Hold one exclusive lease from the pre-transition read through durable publication.
- Use a shared lock or equivalent consistent snapshot for readers.
- For SQLite writers, use `BEGIN IMMEDIATE`; append the event and update every affected projection in one transaction.
- For SQLite readers, use a read-only connection and replay the event chain before comparing projections. A status/read command must not create tables, migrate, set write PRAGMAs, or change database bytes, schema, or mtime.
- Prefer rollback journaling plus full synchronous durability when sidecar-free portable state is required; otherwise bind the chosen journal/durability policy as an engineering contract.
- Publish non-database evidence in the project-defined order: durable bytes, atomic replace, parent-directory durability, authority reference, terminal marker last.
- Do not expose a terminal marker before its referenced bytes and directory entry are durable.
- Bind writer proof to workspace, PID/start time or lease, run/stage, and execution purpose. Process-name absence alone is not writer proof.

The guard may validate supplied identities and counters; lock ownership and durability remain project assertions unless a project validator proves them.

## Migrate without inventing history

When converting a legacy authority, make the first controlled write append one `MIGRATION_BASELINE` event that binds the exact legacy bytes or deterministic legacy projection hash and declares replay valid only from that event forward. Do not synthesize historical events from mutable snapshots.

Commit the baseline and initial projections atomically. Preserve the original legacy authority bytes as immutable legacy material after the new authority is durable; do not overwrite or delete them. Readers must choose the new authority deterministically after commit, and crash recovery must either complete the archival step or expose a typed incomplete migration—never two competing authorities.

## Close terminal and recovery semantics

- One declared action produces exactly one terminal outcome.
- `BLOCKED`, `FAILED_TYPED`, `INCOMPLETE`, and `RECOVERY_REQUIRED` cannot be checkpointed as `COMPLETED`.
- Child, controller, checkpoint, ledger, and outer terminal states must agree.
- A vanished process with no durable terminal becomes typed incomplete/failure; it never becomes PASS.
- Monitoring loss never authorizes process restart or old-transaction resume.
- Duplicate start and old-resume counts remain zero unless an active project contract explicitly defines otherwise.

Retry evidence is append-only and attempt-addressed. Derive retry usage from authoritative replay; a mutable retry projection cannot reset a budget. After any durable side effect, retry requires the existing project recovery contract or a fresh transaction.

## Verify mutations

Cover at least:

- legal forward transition;
- stale generation, concurrent writer, and duplicate start;
- event deletion, reorder, duplicate, wrong previous hash, cross-run/scope swap, and full re-sign;
- projection tamper and event/projection transaction interruption;
- legacy migration identity and crash recovery;
- reader during writer critical section;
- failure between each durability step;
- child typed failure and vanished process reconciliation;
- terminal-to-running and blocked-to-completed rejection;
- retry evidence deletion/reset/overwrite;
- replay/projection equality;
- read-only status preserving database bytes, schema, and mtime.

Do not claim run-state closure from return code, PID absence, one projection read, or an unreplayed event count.
