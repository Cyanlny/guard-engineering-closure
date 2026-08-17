# Generic Closure Facts

Use this internal, ephemeral contract when a project has more state than Git paths alone can express. Do not add it to the project, public schema, release artifact, or scientific identity.

## Select one mode

- `LIGHT`: one small closure item, no expensive multi-stage work, and no evidence chain.
- `STANDARD`: multiple modules, an integration boundary, a migration, a data pipeline, or a release candidate.
- `RESCUE`: scope is already drifting, expensive work has repeated, or the mutation/evidence surface is large.

Changing mode after the baseline requires re-baselining.

## Supply only applicable facts

`closure_guard.py --profile generic --facts <json>` accepts:

```text
project_id
change_generation
closure_item_ids / closure_item_count
open_item_ids / open_item_count / closed_item_count
blocker_ids
planned_mutation_count / completed_mutation_count
validation_level / validation_rank
control_event_count
active_mutator_count
active_expensive_run_count / expensive_start_count
delegated_task_ids / delegated_task_count / subagent_spawn_count
active_subagent_count / active_subagent_mutator_count
active_subagent_expensive_run_count / recursive_delegation_count
final_boundary_start_count
authority_status / authority_revision_count
independent_authority_review_required
capabilities
```

Lists must contain unique nonempty strings. Counts must be nonnegative integers and monotonic counters may not regress. When supplied together, `open_item_ids` must be a subset of `closure_item_ids`, and `closure_item_count = open_item_count + closed_item_count`. Unknown fields and capabilities fail closed. IDs are converted to opaque tokens in snapshots.

The guard infers capabilities from populated facts. An explicit capability is useful when a valid zero value must remain protected, such as zero blockers or zero final-boundary starts.

Supported capabilities are:

```text
authority
blockers
closure_items
control_events
delegation
expensive_operations
final_boundary
mutations
mutators
validation_ladder
vcs
```

Do not invent a capability merely because the guard supports it. For example, a local library bug may have no authority branch, event log, remote boundary, or evidence chain.

Supply `delegation` only when subagents are explicitly authorized and actually relevant. Freeze `delegated_task_ids` before launch. Every delegated task must follow [subagent-containment.md](subagent-containment.md); the script rejects delegated mutators, delegated expensive runs, recursive delegation, task-set growth, and mode-specific concurrency excess. In `RESCUE`, two independent reviewers require the baseline fact `independent_authority_review_required=true`; otherwise the machine limit is one.

If the normalized project facts do not expose delegation state, enforce the same limits in the in-memory Closure Card. Do not expand the project's canonical schema merely to feed this guard.

## Normalize project-specific state

Keep project adapters private and read-only. Map the project's existing canonical state into this exact generic contract before invoking the guard; do not add a project name, private field mapping, or one-off profile to the reusable script. The adapter may select and aggregate existing facts, but it must not infer authority, terminal state, writer absence, or PASS from naming conventions. Validate the normalized facts with `--profile generic --facts <json>` and retain the project source identity separately in the Closure Card.

## Map common projects

- Code/build: closure items=bugs or failing contracts; validation rank=static, focused, integration, acceptance.
- Data pipeline: generation=input/schema version; closure items=broken transforms; final boundary=publish or promote.
- Migration: generation=migration set; validation rank=parse, dry-run, shadow, apply-ready.
- Scientific workflow: authority fields are active; final boundary may be formal compute or release admission.
- Release/deployment: generation=source/artifact version; final boundary=publish, deploy, or production transaction.

Use existing identities such as Git objects, migration checksums, image digests, dataset versions, or artifact manifests. Do not create a new project identity system for this contract.

Use [campaign-state-discipline.md](campaign-state-discipline.md) for Git/worktree drift, context recovery, cache-state separation, and instruction conflicts. Keep those ephemeral controls out of project schemas unless the project already owns equivalent fields.

## Interpret outcomes

- `CONTINUE`: stay on the frozen path.
- `REBASE_REQUIRED`: project, profile, mode, capability, item, or path scope changed.
- `BLOCKED`: a frozen budget or monotonic invariant was violated.

The human/agent may additionally choose `DEFER_ADJACENT_WORK`, `RETIRE_AND_REWRITE`, or completion at the requested boundary. The script never mutates state or makes that policy decision itself.

Snapshots use schema V3, include a self-verifying snapshot hash, and are ephemeral. Re-capture an older V1/V2 baseline; do not build compatibility infrastructure for temporary guard snapshots. When Git paths will be edited, freeze the newline-delimited planned set with `--allowed-paths-from`; a new dirty path is admitted only when it was already dirty at baseline or belongs to that frozen set.
