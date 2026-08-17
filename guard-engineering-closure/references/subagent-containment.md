# Subagent Containment

Use this protocol whenever engineering closure may employ subagents, parallel reviewers, side-thread auditors, or delegated exploration. Delegation is an optimization surface, not a new discovery program or authority source.

## Contents

- Eligibility and mode limits
- Freeze a delegated task charter
- Permission boundary
- Shared audit and verification budget
- Compact output contract
- Main-agent merge procedure
- Conflicts, retries, and stop reasons
- Typical admissible and inadmissible tasks

## Eligibility and mode limits

Delegate only when all conditions are true:

- the user or a higher-level applicable instruction explicitly permits delegation;
- the runtime exposes subagents and does not impose a stricter prohibition;
- the question is concrete, bounded, independent, and tied to an existing frozen item;
- the answer can reduce the critical-path uncertainty or verify a declared direct closure;
- the main agent can continue as sole writer, test orchestrator, and sealer;
- the task has a finite file/symbol frontier and a compact answer contract.

Do not delegate to make an audit look more independent, to keep all concurrency slots busy, or to search broadly for more problems. If local reasoning can answer the question with the same or lower read budget, work locally.

Default limits:

```text
LIGHT: active_readonly_subagents <= 0
STANDARD: active_readonly_subagents <= 2
RESCUE: active_readonly_subagents <= 1
active_subagent_mutators = 0
active_subagent_expensive_runs = 0
recursive_delegation = 0
```

An active scientific, migration, release, or security authority may explicitly require two independent reviewers in `RESCUE`. Treat that as a frozen authority requirement, not permission for a general audit. Do not exceed two.

## Freeze a delegated task charter

Before launch, record the following in the in-memory Closure Card:

```text
task_id
parent_closure_item
baseline_verification_key
one_exact_question
allowed_files_or_symbols
prohibited_reads
maximum_new_file_reads
maximum_new_content_hashes
allowed_commands
expected_output_fields
stop_condition
```

Use a stable task ID. Rephrasing or transferring the same question does not create a new task or reset its budget.

Allowed files must be a finite list or a named direct-caller frontier. A repository, directory tree, file type, architectural layer, or phrase such as "look deeply for related issues" is not a bounded allowlist.

State the question so that completion is observable. Prefer questions such as:

- "Enumerate every direct caller of this changed signature and classify compatibility."
- "Check whether these three emitters satisfy this exact output contract."
- "Cross-check these existing test IDs against the declared mutation matrix."

Do not use open-ended prompts such as "deep audit the system" or "find anything else that might break."

## Permission boundary

The main agent remains the only agent permitted to:

- modify project source, tests, configuration, generated files, manifests, or schemas;
- write project state, decisions, evidence, receipts, checkpoints, or transactions;
- orchestrate shared-workspace tests or validation;
- start or seal a long native, R, FIT, acceptance, remote, migration, deployment, or production operation;
- make or activate a scientific, public-contract, migration, release, or production decision;
- send signals, kill processes, write to live stdin, or recover a running transaction.

Subagents are read-only by default. They must not access credentials, patient rows, protected records, held-out/formal results, running scientific logs, partial artifacts, or mutable cache members unless an active contract explicitly permits that exact read. They must not spawn further subagents.

A subagent may run a cheap read-only static command only when listed in the charter and guaranteed not to write the repository or shared validation workspace. If a command may create caches, compiled files, test artifacts, locks, or receipts, the main agent must run it later in an isolated location or omit it.

## Shared audit and verification budget

All agents consume one campaign budget. Do not allocate a fresh scan/read/hash/test allowance per subagent.

```text
sum(repository_inventory_scans across all agents) <= frozen campaign limit
sum(unchanged_file_rereads per verification key) <= 1
sum(content_hash_reads per unchanged object) <= 1
sum(focused_validation_runs per verification key) <= 1
duplicate_delegated_task_starts = 0
```

Pass recorded Git object IDs, verification keys, changed hunks, and prior conclusions instead of asking every reviewer to rediscover them. Do not pass the intended conclusion or hidden answer when independence matters.

A subagent may request an additional read only with one named invalidation reason: `CONTENT_CHANGED`, `DEPENDENCY_CHANGED`, `VALIDATOR_CHANGED`, `AUTHORITY_CHANGED`, `WRITER_AMBIGUITY`, `CRASH_RECOVERY`, or `TRUST_BOUNDARY`. The main agent grants or rejects the request; the subagent does not silently expand its frontier.

## Compact output contract

Require only these fields when applicable:

```text
task_id
baseline_verification_key
question_answered=yes|no
status=CLOSED|SAME_ROOT_PROPAGATION|INDEPENDENT_CANDIDATE|OUT_OF_SCOPE|AMBIGUOUS
claims
evidence_locations
direct_consumers
affected_existing_tests
new_reads
reused_reads
new_hashes
invalidation_reason_codes
unresolved_question
```

Evidence locations should identify a file/symbol or existing canonical record, not reproduce long contents, logs, payloads, secrets, or repeated hash values. Keep claims distinguishable from observations and proposals.

A subagent cannot report `PASS_BY_TEST`, `PASS_BY_WAIVER`, authority activation, or final acceptance unless the main agent supplied and the subagent verified the applicable canonical evidence. In ordinary read-only review, `CLOSED` means only that the delegated question found the declared direct closure satisfied; the main Closure Card still controls project closure.

## Main-agent merge procedure

After all eligible subagents finish:

1. confirm the project is still at the chartered verification key or name the invalidation;
2. deduplicate findings by producer, interface, authority, and failure signature;
3. verify only the assertion-critical evidence not already covered by an unchanged canonical identity;
4. classify each finding as same-root propagation, independent candidate, deferred adjacent work, or invalid/out-of-scope;
5. merge same-root direct consumers into the existing item without increasing the root denominator;
6. route an independent candidate through controlled boundary adjudication before any mutation;
7. reject findings outside the allowlist or based on stale identity;
8. update the Closure Card once, not once per subagent message.

Reviewer agreement is not proof by vote. Two agents repeating the same claim do not increase its authority or permit another file read. A disagreement triggers one bounded comparison of the conflicting assertion-critical evidence; it does not trigger a third general reviewer.

## Conflicts, retries, and stop reasons

Do not automatically restart or replace a subagent that fails, times out, loses context, or returns an incomplete report. Continue locally if possible. Retry only when the original task remains necessary, its budget has not been consumed, and the failure was operational rather than substantive.

Stop delegated work with the narrowest applicable reason:

- `DELEGATION_NOT_AUTHORIZED`: no user or higher-level authority permits subagents;
- `DELEGATION_FRONTIER_UNBOUNDED`: the question lacks a finite file/symbol frontier;
- `DELEGATION_BUDGET_EXHAUSTED`: shared reads, hashes, scans, or task starts reached the frozen limit;
- `DELEGATED_MUTATION_PROHIBITED`: the task requires a subagent to write or seal state;
- `DELEGATED_EXPENSIVE_RUN_PROHIBITED`: the task requires long/native/acceptance execution;
- `DELEGATION_IDENTITY_STALE`: the baseline changed before merge;
- `DELEGATED_FINDING_REQUIRES_REBASE`: a genuinely independent blocker lies outside frozen scope;
- `DUPLICATE_DELEGATION_REJECTED`: another active or completed task already answers the question;
- `DELEGATED_CONFLICT_UNRESOLVED`: assertion-critical evidence remains inconsistent after one bounded comparison.

## Typical admissible and inadmissible tasks

Admissible:

- diff-first enumeration of direct callers for one changed ABI;
- read-only cross-check of one producer-consumer-validator chain;
- verification that an existing test union covers a frozen mutation matrix;
- independent review required by an already active authority, within a fixed source basis.

Inadmissible:

- repository-wide architecture or security audit after the cutoff;
- asking multiple agents to find additional roots;
- source, test, state, evidence, schema, or generated-file edits;
- running a shared pytest suite, R/native pipeline, acceptance vertical, freeze, remote, or production operation;
- reading protected data or results to select a value;
- creating another agent, automation, validator, gate, inventory, or evidence framework.
