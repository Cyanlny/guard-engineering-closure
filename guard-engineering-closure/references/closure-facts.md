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
campaign_id / rescue_deadline_at
change_generation
closure_item_ids / closure_item_count
open_item_ids / open_item_count / closed_item_count
blocker_ids
planned_mutation_count / completed_mutation_count / remaining_mutation_count
validation_level / validation_rank
validation_discovered_count / validation_executed_count / validation_passed_count
validation_failed_count / validation_error_count / validation_skipped_count
validation_xfail_count / validation_xpass_count / validation_evidence_identity
validation_outer_terminal_status
control_event_count
active_mutator_count
writer_free / writer_proof_identity
active_expensive_run_count / expensive_start_count
delegated_task_ids / delegated_task_count / subagent_spawn_count
active_subagent_count / active_subagent_mutator_count
active_subagent_expensive_run_count / recursive_delegation_count
final_boundary_start_count
authority_status / authority_revision_count / authority_revision_identity
independent_authority_review_required
changed_object_ids / allowed_object_ids / protected_content_identity
boundary_smoke_status / boundary_smoke_identity
run_state_head_identity / run_state_terminal_count
run_state_replay_verified / run_state_projection_matches_replay
duplicate_start_count / old_transaction_resume_count
waiver_ids / waiver_scope_identity
capabilities
```

Lists must contain unique nonempty strings. Counts must be nonnegative integers and monotonic counters may not regress. When supplied together, `open_item_ids` must be a subset of `closure_item_ids`, and `closure_item_count = open_item_count + closed_item_count`. Unknown fields and capabilities fail closed. IDs are converted to opaque tokens in snapshots.

The guard infers capabilities from populated facts. At the initial baseline, explicitly declare every capability that will become applicable later in the same campaign; otherwise its later appearance is a scope change and requires accepted rebaseline. This lets a not-yet-run validation declare `validation_execution` without inventing result counts. An explicit capability is also useful when a valid zero value must remain protected, such as zero blockers or zero final-boundary starts.

Supported capabilities are:

```text
authority
boundary_smoke
blockers
campaign_lineage
closure_items
control_events
delegation
expensive_operations
final_boundary
mutations
mutators
object_scope
run_state
validation_ladder
validation_execution
vcs
waivers
writer_proof
```

For `generic` facts, `STANDARD` requires `closure_items`, `mutations`, `validation_ladder`, and `mutators`. `RESCUE` additionally requires `campaign_lineage`, `expensive_operations`, `writer_proof`, and `boundary_smoke`. Use `LIGHT` or the Git-only profile when those concepts genuinely do not apply; do not claim full STANDARD/RESCUE enforcement from an incomplete capability set.

Use authority states exactly:

```text
NOT_APPLICABLE | UNRESOLVED | PROPOSED | APPROVED | ACTIVATED | REJECTED
```

Do not infer authority from event names. A waiver is a separate scoped capability, not an authority state or technical PASS.

Validation counts use:

```text
discovered = executed + skipped
executed = passed + failed + errors + xfail + xpass
```

If a framework uses a different convention, normalize it before supplying facts. A PASS boundary requires executed greater than zero and every non-pass count equal to zero.

Do not invent a capability merely because the guard supports it. For example, a local library bug may have no authority branch, event log, remote boundary, or evidence chain.

Supply `delegation` only when subagents are explicitly authorized and actually relevant. Freeze `delegated_task_ids` before launch. Every delegated task must follow [subagent-containment.md](subagent-containment.md); the script rejects delegated mutators, delegated expensive runs, recursive delegation, task-set growth, and mode-specific concurrency excess. In `RESCUE`, two independent reviewers require the baseline fact `independent_authority_review_required=true`; otherwise the machine limit is one.

If a project-specific profile does not expose delegation facts, enforce the same limits in the in-memory Closure Card. Do not expand the project's canonical schema merely to feed this guard.

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

Snapshots use schema V5, include a self-verifying snapshot hash and campaign lineage, and are ephemeral. Re-capture an older baseline; do not build compatibility infrastructure for temporary guard snapshots. When Git paths will be edited, freeze the newline-delimited planned set with `--allowed-paths-from`; a new dirty path is admitted only when it was already dirty at baseline or belongs to that frozen set. Use the explicit predecessor option for one accepted rebaseline instead of resetting the campaign.
