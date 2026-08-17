# Controlled Boundary Adjudication

Use this protocol to decide whether a frozen engineering closure may expand. Deep reasoning is permitted; unbounded discovery is not.

## Contents

- Trigger
- Preconditions and audit budget
- Build one Boundary Proposal
- Admission test
- Outcomes
- Mode policy

## Trigger

Run one adjudication only when at least one condition holds:

- a reproduced direct blocker lies outside the frozen item or object set;
- the current requested outcome is impossible under the frozen contract;
- the user explicitly proposes an expansion whose closure impact is unknown;
- salvage and retire/rewrite cannot be compared without a bounded architectural review.

Enter through a current `CONTROLLED_REBASE_REQUIRED` Reasoning Capsule, including when the trigger is an explicit user proposal. Reuse that capsule; do not rebuild the diagnosis merely to justify expansion.

Do not trigger it for elapsed time, uncertainty, commentary, delegated suggestions, adjacent hardening, speculative risk, or a desire to make the platform more general.

## Preconditions and audit budget

Before reviewing:

- reach a writer-free checkpoint and preserve any active process;
- lock the current target, stop point, failure signature, change generation, and latest valid verification key;
- perform no mutation, validation run, evidence append, identity rebuild, or rebaseline;
- state the exact questions the review must answer and a time/read budget.

Use these defaults unless the user authorizes stricter project-specific values:

```text
boundary_adjudications_per_failure_signature <= 1
accepted_boundary_expansions_per_campaign <= 1
new_repository_wide_scans = 0
new_full_tree_hash_scans = 0
unchanged_file_rereads = 0
new_reads are limited to the named direct dependency/impact frontier
```

Reuse the Closure Card, Git identities, recorded file conclusions, validator identities, and prior PASS keys. Request a new file read, hash, or test only with a named invalidation reason. Do not collect more facts merely to make the proposal look exhaustive.

## Build one Boundary Proposal

Keep the proposal in memory unless an existing authority requires a durable decision. Include only:

1. requested outcome and stop point;
2. reproduced trigger and stable failure signature;
3. current causal/design hypothesis and proof that the frozen scope cannot close it;
4. proposed item, object, capability, authority, and public-surface deltas;
5. exact producer-to-consumer-to-validator-to-test frontier;
6. alternatives: work inside scope, defer, bounded rebase, retire/rewrite;
7. complexity tax;
8. protected-boundary and identity effects;
9. validation levels invalidated or newly required;
10. recommendation, confidence, and required approval.

Express the complexity tax compactly:

```text
delta_items
delta_objects
delta_capabilities
planned_mutation_tranches
expected_expensive_runs
identity_invalidations
estimated_critical_path
```

Do not count symptoms, files, tests, or repeated terminals as separate roots when they share the same producer, interface, authority, or failure signature.

## Admission test

Accept an expansion only when every applicable condition is true:

- it is mandatory for the user's current outcome, not merely desirable hardening;
- the root is genuinely independent rather than an unclosed consumer of an existing item;
- the affected objects and all direct consumers are finite and known;
- one canonical authority exists for each changed contract or value;
- the change fits one consolidated mutation tranche and the existing validation ladder;
- it does not use protected, held-out, formal, production, or release results to choose a governed value;
- a cheap real boundary smoke can run before any expensive acceptance;
- expected closure benefit exceeds the complexity tax and invalidation cost;
- the requested stop point remains reachable without another anticipated expansion.

Public contracts, governed scientific values, protected-data use, migration ownership, release policy, and production boundaries always require the applicable explicit authority. Pre-authorization for engineering repair does not imply authorization for those dimensions.

## Outcomes

Return exactly one outcome:

- `REJECT_EXPANSION`: evidence does not establish necessity, independence, authority, or boundedness.
- `DEFER_ADJACENT_WORK`: useful work is real but not required before the current stop point.
- `ACCEPT_BOUNDED_REBASE`: the mandatory delta passes every admission condition and all required approvals are present.
- `RETIRE_AND_REWRITE`: bounded repair costs more or carries more uncertainty than replacing the current implementation behind the same protected contract.

For `ACCEPT_BOUNDED_REBASE`:

1. update the in-memory Closure Card;
2. capture one new guard baseline;
3. freeze the accepted items, objects, mutation count, and validation impact;
4. invalidate only the declared dependency closure;
5. execute one mutation tranche and one real boundary smoke;
6. resume ordinary monotonic closure.

Do not recursively adjudicate the adjudication. A rejected proposal cannot return without new invalidating evidence. If the accepted delta fails its first real smoke or reveals another independent root, stop and compare the existing salvage path with `RETIRE_AND_REWRITE`; do not grant a second automatic expansion.

## Mode policy

- `LIGHT`: normally reject expansion; recapture as `STANDARD` only for a small same-root direct closure.
- `STANDARD`: permit one adjudication and, by default, one accepted bounded rebase.
- `RESCUE`: default to defer or retire/rewrite; accept only a mandatory, explicitly rebaselined delta proven cheaper than those alternatives.

Deep thought should improve the decision, not increase file, hash, event, validator, or evidence counts.
It does not itself grant authority, approve a public surface, or rebaseline the campaign.
