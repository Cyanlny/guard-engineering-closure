---
name: guard-engineering-closure
description: Enforce root-cause-first action, bounded monotonic closure, controlled scope expansion, exact-key verification reuse, context economy, worktree drift control, and mid-flight rescue. Use for multi-stage, expensive, evidence-bound, or already drifting builds, compilers, validation pipelines, scientific workflows, migrations, and releases; repeated patch/validation loops; large dirty worktrees; identity chains; concurrent writers; hidden interfaces; scope creep; blockers; or explicit requests to think before acting and prevent endless closure. Do not auto-apply the full guard to an isolated low-risk one-file fix unless the user invokes it or a listed risk is present.
---

# Guard Engineering Closure

Close the frozen target. Do not turn it into a platform-building program.

Choose the smallest applicable mode:

- `LIGHT`: one bounded code/configuration fix, no long run or evidence chain;
- `STANDARD`: multi-module integration, pipeline, migration, or release candidate;
- `RESCUE`: repeated failure, moving scope, large dirty surface, or exhausted budgets.

Apply `karpathy-guidelines` whenever reading, designing, reviewing, or changing source: surface assumptions, choose the smallest sufficient design, change only necessary lines, and define observable success. Never use simplification to weaken an active data, scientific, identity, migration, release, or production boundary.

## Load only applicable detail

- Additional or project-specific facts: normalize them through [references/closure-facts.md](references/closure-facts.md); keep private adapters outside this reusable core.
- Repeated reads, hashes, PASS reuse, or caches: [references/verification-economy.md](references/verification-economy.md).
- Git drift, context recovery, concurrent writers, or instruction conflict: [references/campaign-state-discipline.md](references/campaign-state-discipline.md).
- Canonical run state, event/projection replay, leases, terminal recovery, or retry evidence: [references/run-state-integrity.md](references/run-state-integrity.md).
- Long/native execution, writer proof, validation credibility, artifact admission, or final release: [references/execution-boundary-integrity.md](references/execution-boundary-integrity.md).
- Missing scope or proposed expansion: [references/boundary-adjudication.md](references/boundary-adjudication.md).
- Multi-axis topology, authority, denominator, aggregation, or terminal semantics: [references/pre-mutation-contract.md](references/pre-mutation-contract.md).
- Retire/rewrite, migration bootstrap, or handoff package: [references/retirement-handoff.md](references/retirement-handoff.md).
- Authorized delegation: [references/subagent-containment.md](references/subagent-containment.md).

Read each selected reference completely before the action it governs. Do not load unrelated references for reassurance.

## Follow one closure workflow

1. **Freeze intent.** Record the exact target, stop point, failure signature, closure items, allowed objects, protected boundaries, highest valid layer, and one next action.
2. **Capture state once.** Establish workspace, repository/change generation, current dirty paths, predeclared allowed paths, active writers/runs, authority revision, and verification key.
3. **Reason before acting.** Produce one bounded outcome from the current evidence.
4. **Prove the direct topology.** Follow authority/input → producer → all direct consumers → sole validator → terminal → affected tests. Derive denominators mechanically where applicable.
5. **Act once.** Run one discriminating diagnostic tranche or one consolidated mutation tranche for the stable root.
6. **Validate cheaply to expensively.** Escalate once through the frozen ladder; run final acceptance only after planned mutations reach zero.
7. **Stop at the requested boundary.** Defer adjacent improvements and report unresolved authority separately.

Do not create a task database, cache service, evidence ledger, validator, schema, gate, receipt, or automation merely to operate this Skill.

## Keep one concise Closure Card

Keep at most 12 in-memory lines:

```text
target + stop point
stable root/failure signature + closure items
allowed paths/symbols + conditional direct frontier
protected authority/data/schema/public identities
workspace + HEAD/change generation + dirty/allowed path identities
highest valid validation layer + execution purpose
active writer/expensive process/delegated read-only tasks
verification key + named invalidation reasons
read/hash/test/cache/delegation budgets
reasoning outcome + one next action
```

This card is scheduling state, not project evidence. Keep full logs, payloads, manifests, repeated hashes, and historical narratives out of context.

## Run the machine guard at meaningful checkpoints

Use `scripts/closure_guard.py` only at intake, terminal, accepted rebaseline, pre-mutation, pre-long-validation, source-stability barrier, or trust boundary.

- `snapshot` records Git/project facts, freezes planned paths/objects, and may bind an accepted rebaseline to one predecessor snapshot.
- `compare` inherits that allowed-path set, verifies the V5 baseline hash and lineage, enforces monotonic facts, and reports `status=PASS|BLOCKED` plus `recommended_outcome=CONTINUE|REBASE_REQUIRED|BLOCKED`.
- `self-test` exercises integrity, scope, monotonicity, delegation, authority, and release rules without touching a project.

Snapshots are ephemeral V5 objects outside repositories and canonical evidence. Re-capture older schemas; do not build compatibility code for temporary guard state. A nonzero comparison is a stop condition. Reuse one result when the state signature is unchanged instead of checking again for commentary.

Distinguish enforcement:

- `MACHINE_ENFORCED`: facts supplied to and checked by the scripts;
- `BEHAVIORAL_INVARIANT`: agent conduct such as bounded reasoning and surgical edits;
- `PROJECT_ASSERTION`: authority, writer absence, or terminal facts supplied by the project.

Never claim the script proved an assertion that the caller merely supplied.

## Reason before mutation, retry, validation, or expansion

Form one six-line-or-fewer Reasoning Capsule:

```text
observation + stable signature
primary causal/design hypothesis
strongest live alternative
existing evidence + exact unknown
smallest discriminating/corrective action
success + stop + expansion conditions
```

Keep only the concise rationale, assumptions, and confidence; never expose or persist private chain-of-thought. Return exactly one outcome:

- `ACTION_JUSTIFIED`: one bounded action is supported inside the frozen closure;
- `BOUNDED_DIAGNOSTIC_REQUIRED`: one predeclared finite diagnostic tranche is needed to distinguish live hypotheses;
- `CONTROLLED_REBASE_REQUIRED`: the target is unreachable without bounded expansion;
- `STOP_NO_JUSTIFIED_ACTION`: evidence, authority, benefit, or safety is insufficient.

Reuse the capsule until its signature, assertion-critical evidence, or Campaign Baseline Tuple changes. Deep thought improves action selection; it never grants authority or scope.

## Freeze scope and topology before source mutation

Classify every object once:

- `FROZEN_CORE`: mandatory work defining the requested outcome;
- `CONDITIONAL_DIRECT_FRONTIER`: predeclared same-root consumers, fixtures, generated projections, and tests activated only by an exact ABI, required-set, owner, schema, or runtime trigger;
- `DEFERRED_ADJACENT`: nonblocking science, platform hardening, cleanup, or post-stop-point work.

Require `TOPOLOGY_COMPLETE` when axes or execution semantics matter: exact object/population universe, ordered coordinates, denominator, multiplicity, retry/reuse semantics, outputs, consumers, aggregation, terminal ownership, authority sources, and one real boundary smoke.

Require `AUTHORITY_COMPLETE` only for governed fields. It means every applicable field is `NOT_APPLICABLE` or owned by an `ACTIVATED` authority. Code, a fixture, a candidate, or approval without canonical activation is insufficient. Adding an allowed path never resolves an authority gap.

Track proof and authority separately:

```text
proof = UNINSPECTED | EVIDENCE_FOUND | IMPLEMENTED_VERIFY_ONLY
        | PASS_BY_TEST | PASS_BY_WAIVER | CLOSED
authority = NOT_APPLICABLE | UNRESOLVED | PROPOSED | APPROVED | ACTIVATED
```

Never relabel a waiver, skip, zero-test module, or absent failure as technical PASS.

## Enforce monotonic closure

Require:

```text
open_items(next) ⊆ open_items(now)
changed_objects ⊆ baseline_dirty ∪ predeclared_allowed_paths
planned_mutations(next) ≤ planned_mutations(now)
completed/event/start/authority counters never regress
active_mutators ≤ 1
active_expensive_runs ≤ 1
delegated_mutators = delegated_expensive_runs = recursive_delegation = 0
```

Map same-producer/interface/authority symptoms to one root and close all direct consumers in one tranche. Freeze an audit cutoff before mutation. If two consecutive checkpoints close no item and advance no validation layer, stop with `CONTROL_PLANE_GROWTH_WITHOUT_CLOSURE_PROGRESS`.

## Reuse verification precisely

Use `scripts/verification_economy.py` and the R0–R4 policy in the reference.

- Require nonempty immutable epoch, validator, dependency-closure, and purpose identities.
- Reuse only an exact verification key; invalidate only changed objects and their declared downstream closure.
- Treat metadata as a same-epoch writer-free optimization, not identity. The planner verifies ctime and pre/post read state before reuse or hashing.
- Require a named invalidation reason before repeated reads, hashes, tests, or cache misses.
- Keep caches disposable and non-authoritative.
- Freshly seal commit, freeze, transaction, transfer, admission, deployment, final no-delta, and final acceptance boundaries.

Do not build cross-epoch adoption or a generic cache platform during rescue merely to avoid one final run.

## Make surgical changes and expose hidden failures early

Before mutation, apply Surface Economy to every in-scope file, gate, interface, and validator:

```text
KEEP | MERGE | INLINE | REMOVE | DEFER
```

Keep a surface only when a unique responsibility, active consumer, trust boundary, or compatibility obligation proves it necessary. A new surface is admissible only when the current root cannot close through an existing canonical path. In `RESCUE`, defer adjacent cleanup by default; remove only a duplicated authority, gate, or validator that directly blocks closure. Enforce growth through the existing allowed-path and allowed-object guard rather than adding a surface-count schema or another gate.

- Touch only frozen files and symbols; preserve unrelated user changes.
- Migrate all direct producers before enabling a stricter shared validator.
- Do not refactor adjacent code or add speculative flexibility.
- Run a cheap real producer → consumer → sole-validator → terminal smoke as soon as the implementation is coherent.
- Cover positive, missing, extra, swapped, wrong-context, and self-consistent re-sign cases.
- Reject wildcard sidecars, hidden defaults, identity laundering, fixed-BLOCKED paths, return-code-only PASS, all-skipped modules, and producer mocks at the changed boundary.

Use this neutral ladder, omitting inapplicable levels:

1. `V0`: bounded diff, parse, formatting, schema/plan checks;
2. `V1`: exact changed interface and mutations;
3. `V2`: affected-module union and declared graph closure;
4. `V3`: one minimal real boundary smoke;
5. final acceptance: complete project denominator once in a stable generation.

Focused PASS guides scheduling but never replaces an applicable integration, boundary, freeze, migration apply, deployment, remote, release, or production acceptance.

## Control expansion and rescue

Enter `MID_FLIGHT_RESCUE` when at least two apply: repeated expensive runs without source stability, changed surface disproportionate to scope, ≥80% mutation budget consumed, three control events without compute/validation progress, rejected authority before governed work, or a long run exposing a pre-call interface defect.

In rescue, freeze denominators, forbid adjacent platform work, choose `TIMEBOXED_SALVAGE` or `RETIRE_AND_REWRITE`, and require a real smoke inside the timebox. Do not automatically revise a rejected authority branch.

Only `CONTROLLED_REBASE_REQUIRED` may enter [boundary adjudication](references/boundary-adjudication.md). Permit one bounded adjudication per stable signature and normally one accepted expansion per campaign. Expansion must be mandatory, finite, authority-backed, one-tranche executable, smoke-testable, and cheaper than deferral or rewrite.

## Contain delegation

Delegation is never implied by this Skill. Use it only when higher-level instructions permit it.

- Main agent remains sole writer, test orchestrator, state/evidence writer, and sealer.
- Delegate a finite read-only question on an existing frozen item, with file/symbol and read/hash/test budgets.
- Share one campaign budget; do not multiply scans or hashes by agent count.
- Treat findings as proposals and deduplicate before action.
- Default active limits: `LIGHT=0`, `STANDARD≤2`, `RESCUE≤1`.
- Allow `RESCUE=2` only when an already frozen authority explicitly requires two independent reviewers and the baseline declares `independent_authority_review_required=true`.
- Forbid delegated mutation, expensive/native runs, protected-data reads, signals, credentials, and recursive delegation.

## Preserve campaign and context integrity

Use Git for identity and diff-first inspection, not as task management. Never auto-commit, stash, reset, rebase, or hide unrelated changes. Treat unexplained HEAD/path changes as drift; inspect only changed hunks and direct dependants.

After context compaction or handoff, reconstruct once from the Closure Card and existing identities. Do not restart repository discovery, rehash unchanged bytes, rerun validation, or restart a live process because conversation state was lost.

While long work is alive, monitor read-only. Relocate by workspace/PID tree if a handle is lost; never restart merely because monitoring was interrupted. On terminal failure, inventory once before editing.

## Stop and complete precisely

Stop with the narrowest typed reason when scope needs an unapproved expansion, governed authority is absent, protected/formal results would be needed to choose a value, concurrent writers make state ambiguous, a second expensive repair cycle is required, the real smoke misses its rescue timebox, or resources cannot be solved inside scope.

Declare `ENGINEERING_BASELINE_STABLE` only when every frozen engineering item is closed, open items and planned mutations are zero, applicable validation passes in one generation, protected diffs match the allowlist, and no writer or validation is active.

Do not call that final project PASS while authority or final acceptance remains pending. Execute the final chain once and stop at the user-defined boundary.
