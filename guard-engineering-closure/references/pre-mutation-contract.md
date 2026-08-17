# Pre-Mutation Contract Completeness

Use this protocol before the first source mutation in a multi-stage or multi-axis workflow. Its purpose is to detect missing authority and execution semantics before code structure silently chooses them.

## Contents

- Scope layers
- Surface Economy
- Proof and authority states
- Topology completeness record
- Project mappings
- Decision procedure
- Stop reasons

## Scope layers

Classify every proposed item and object once:

### FROZEN_CORE

Include only mandatory roots, direct outcomes, and the stop point for the current campaign. Closing this denominator defines engineering completion.

### CONDITIONAL_DIRECT_FRONTIER

Predeclare predictable same-root propagation. Each entry must contain:

```text
parent_root
activation_trigger
bounded_objects
direct_consumers
authority_effect
validation_invalidation
```

Valid triggers include an exact ABI, signature, required-set, owner, schema, runtime, or generated-projection change. Activation keeps the same root only when the observed trigger and every affected object match the declaration.

Do not use this layer to pre-authorize a new scientific value, public contract, migration owner, data class, release policy, or production boundary.

### DEFERRED_ADJACENT

Place optional hardening, cleanup, platform work, rejected candidates, and post-stop-point improvements here. Authorization to perform this work later does not activate it now.

Anything that fits none of the three layers requires controlled boundary adjudication before mutation.

## Surface Economy

Before mutation, classify every in-scope file, gate, interface, and validator exactly once:

```text
KEEP | MERGE | INLINE | REMOVE | DEFER
```

- `KEEP`: one unique responsibility, active consumer, trust boundary, or compatibility obligation requires the surface.
- `MERGE`: two surfaces express the same authority or decision and one canonical owner can serve every active consumer.
- `INLINE`: the surface has one bounded caller and no independent trust or compatibility boundary.
- `REMOVE`: a duplicate authority, gate, validator, or unreachable interface directly obstructs the frozen closure.
- `DEFER`: the change is adjacent cleanup, speculative abstraction, or future capability rather than a requirement of the current root.

Reject a new surface unless the current root cannot close through an existing canonical path and the new responsibility is finite, directly consumed, and covered by the frozen verification ladder. In `RESCUE`, default to `DEFER`; only `MERGE`, `INLINE`, or `REMOVE` a duplicate authority/gate/validator when doing so directly closes the current root. Use the existing allowed-path and allowed-object identities to detect growth. Do not add a surface counter, public schema, or another gate merely to enforce this decision.

## Proof and authority states

Track two independent axes.

```text
proof_state:
  UNINSPECTED
  EVIDENCE_FOUND
  IMPLEMENTED_VERIFY_ONLY
  PASS_BY_TEST
  PASS_BY_WAIVER
  CLOSED

authority_state:
  NOT_APPLICABLE
  UNRESOLVED
  PROPOSED
  APPROVED
  ACTIVATED
```

Apply these rules:

- Reading evidence cannot produce `IMPLEMENTED_VERIFY_ONLY`.
- Existing code cannot produce `PASS_BY_TEST` without an executed applicable test.
- A proposal, reviewer recommendation, or user permission to explore is not `ACTIVATED` authority.
- `APPROVED` means the decision is accepted; `ACTIVATED` means the canonical owner and all required projections are current.
- If activation requires source mutation, permit one explicitly approved authority-only tranche limited to the canonical owner and required projections. It must not also change an executor, planner, validator, or governed runtime path.
- `PASS_BY_WAIVER` proves only the waived requirement and remains distinguishable from technical PASS.
- `CLOSED` requires applicable proof, complete topology, activated authority, and no open direct consumer.

Define `AUTHORITY_COMPLETE=true` only when every governed field is `NOT_APPLICABLE` or owned by an `ACTIVATED` authority.

## Topology completeness record

Prove every applicable field before mutation:

1. requested outcome and stop point;
2. input, population, object universe, exclusions, and protected boundaries;
3. ordered coordinate axes and the owner of each axis;
4. exact denominator formula and expected cardinality;
5. operation sequence and multiplicity;
6. reuse, refit, retry, resume, caching, and recovery semantics;
7. producer outputs and exact direct-consumer inputs;
8. aggregation order, weighting, missing-value behavior, ties, and failure handling;
9. terminal count, ownership, statuses, and completion conditions;
10. selection, admission, migration, publication, release, or deployment effects;
11. sole validator and changed-interface mutation cases;
12. cheapest real boundary smoke and observable success criteria.
13. exact allowed logical objects plus protected-content identity outside them;
14. scoped waivers, their invalidation conditions, and non-transferability.

Do not infer a missing field from loop bounds, test fixtures, previous artifacts, local constants, library defaults, current results, or the shape of an incomplete planner.

An already dirty file is not blanket mutation authority. When the requested edit touches a pre-dirty file, identify the allowed symbols/rows/hunks and preserve an identity for unrelated content.

`TOPOLOGY_COMPLETE=true` requires every applicable field to be unique, authority-backed where governed, and internally cardinality-consistent.

## Project mappings

Map the generic record to the project without adding unused concepts:

| Project type | Typical coordinate axes | Typical aggregation or terminal questions |
|---|---|---|
| Build/compiler | targets, platforms, profiles, generated variants | output set, package/index aggregation, build terminal |
| Data pipeline | partitions, windows, shards, retries | deduplication, watermark, partial-failure terminal |
| Migration | tenant, shard, batch, schema version | commit order, rollback, applied/partial terminal |
| Scientific workflow | cohort, fold, seed, imputation, model family | pooling, multiplicity, estimability, selection effect |
| Release/deployment | artifacts, environments, rollout units | admission, promotion, rollback, release terminal |

Do not force scientific or release fields onto projects where they are not applicable.

## Decision procedure

Before editing:

1. require a current Reasoning Capsule; run its predeclared finite diagnostic tranche first when it returns `BOUNDED_DIAGNOSTIC_REQUIRED`;
2. classify all items and objects into the three scope layers;
3. assign proof and authority states;
4. fill the topology record from existing canonical evidence;
5. derive the denominator mechanically;
6. verify producer-to-consumer cardinality and terminal ownership;
7. name the real boundary smoke;
8. return `AUTHORITY_ACTIVATION_ONLY` when explicit approval exists but canonical activation is pending, and freeze its exact owner/projection paths;
9. return `IMPLEMENTATION_MUTATION_ADMITTED` only when the capsule is `ACTION_JUSTIFIED` and both `TOPOLOGY_COMPLETE` and `AUTHORITY_COMPLETE` are true.

If code already changed before this check, do not invent missing values to preserve the patch. Mark the affected implementation `IMPLEMENTED_VERIFY_ONLY`, stop further mutation, and obtain the missing authority or retire the unsupported code.

## Stop reasons

Use the narrowest applicable reason:

- `TOPOLOGY_AUTHORITY_INCOMPLETE`: a governed field lacks activated authority.
- `DENOMINATOR_UNRESOLVED`: axes, domains, or operation counts are non-unique.
- `AGGREGATION_UNRESOLVED`: pooling, weighting, ties, or missing behavior is non-unique.
- `TERMINAL_SEMANTICS_UNRESOLVED`: terminal cardinality, ownership, or status effects are non-unique.
- `CONDITIONAL_FRONTIER_MISMATCH`: the observed propagation exceeds its predeclared trigger or objects.

An allowed-path expansion, successful parse, mocked test, or absent runtime failure cannot clear these stops.
