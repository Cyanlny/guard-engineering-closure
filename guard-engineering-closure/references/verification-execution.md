# Verification and Execution

## Select the cheapest sufficient proof

| Tier | Sufficient use |
|---|---|
| `R0` | reuse qualified current authoritative evidence; no new object-level verification or scientific computation |
| `R1` | deterministic syntax, schema, identity, or freshness |
| `R2` | focused behavior or synthetic test |
| `R3` | real consumer, transport, integration, or boundary |
| `R4` | fresh seal, independent rerun, project acceptance |

R0 sets verification workload, not formal result. Qualified evidence does not require exploratory subject rereads or hashes; additional verification access needs an independent, current, authorized proof obligation. Escalate only for invalidation, negative, boundary/scientific, or contract need. Keys bind validator/version, generation/digest, decisive environment/trust/authority, freshness/expiry. Use native protected seals. Discover and assess control material before subject access; do not batch unread instructions with gated operations unless the native operation enforces the prerequisite. Before a check, name its required predicate; after it, before dependent operations, confirm that predicate and its bound identity actually hold.

`verification_economy.py` only plans selected-object reuse: it runs no project validator, proves no writer-free state or permission, and grants no acceptance. `R2_VALIDATION_REUSE` is not a newly run test; `R4_FRESH_SEAL_REQUIRED` is not an existing seal. Internal `BLOCKED→REUSE_ALL` cannot unlock action (the public plan CLI captures `UNVERIFIED`); an empty object set cannot erase `global_reasons` or validate a changed global contract.

## Prove the represented subject

Negative claims bind subject, representation, search surface, validator, coverage, and limits; field names or projections do not prove absent values, writers, or effects.

Before verdict qualify validator identity/version/input/environment. Attribution retains consumer chain, role, lock/lease, operation; terminal checks add target, phase, expected/observed, classification, transport, time, and needed type/size/digest/status/writer/run-state. Preserve decisive facts and `UNKNOWN`s.

For failures, cite available native execution/phase, input/version, exception type/message/stack, return code, and decisive resource/authority/consumer observations. Do not mandate new logs or copy sensitive inputs.

Separate read/processed work, successfully committed results, and unmeasured portions. Prefer native batch progress/checkpoints at natural boundaries, not per-item persistence. Mid-run failure or forced termination supports the last trustworthy record or lower bound; missing final measurement is UNKNOWN, not zero or an invented exact total. Label any justified reconstruction as derived, not measured; preserve committed results without repeating costly computation to fill accounting gaps.

`UNAVAILABLE` is uninvokable; `VALIDATOR_DEFECT` is pre-verdict failure; neither proves subject failure. Selecting a non-active copy without effect is attribution defect. Record `validator identity + generation + subject protocol + failure class` with native causal-root evidence for recurrence arbitration.

## Isolate parallel validation

Cross-audit science/efficiency only for independent critical-path benefit under frozen context, validator, shared budget, evidence and stop. Do not duplicate computation. Read-only agents never write; test writes require authorized disposable/native isolation. Shared worktree/database/lease/transaction/cache/artifact/port mutation needs that protocol; only the closure owner writes canonical/shared state, seals and accepts. Agents return evidence, not PASS/retry/V9 authority. LIGHT needs none; RESCUE stays read-only. Classify environmental defects first.

## Require scientific vertical closure

Require attributable, compatible evidence for the scientific chain: contract-required data/configuration and computational scope; mocks, reduced budgets, or unapproved method changes cannot substitute. Reuse real results only while scientific dependencies, identity, provenance, and acceptance remain valid; preserve failure, unreliable, and not-estimable meanings.

After lowest sufficient checks, run the authorized production path: parse real inputs, compute what valid results do not cover, publish authoritative outputs, then have the actual downstream reopen and process them there. Require observable consumption evidence, not an available interface, path, or mock. Missing inputs/authority/results/consumption means explicitly incomplete under existing outcomes—not expanded permission.

Use native indices, selective/streaming reads and direct consumption. Keep intermediates only for necessary consumers/recovery/reproducibility/retention, then retire them. Compact representations require unchanged science and real-consumer compatibility before retiring old representations; no extra fits or backup chains. Check actual request/transfer size and termination protocol. Small tests cannot replace real-input acceptance.

## Bound capacity and reclaim dynamically

Before dispatch/prefetch/expansion/large writes, jointly budget effective host/cgroup limits, working set, concurrent peaks/reserve, cache/parser/prefetch byte caps, and disk space/quota/inodes with overlapping input/temp/publication/checkpoint peaks. Native coordinated admission prevents overcommit; host totals, idle CPU and single RSS/PSS samples do not prove capacity.

Use native hooks before admission/materialization; after last-consumer release, task completion or stage change; on invalidation/pressure crossings: observe → qualify → reclaim bounded batches → verify release → readmit/wait. Native budgets define thresholds, cadence, target and hysteresis. Stop at sufficient headroom; no new service or full rescans.

Separate working set, application cache, shared mappings and reclaimable OS cache: cache is neither waste nor guaranteed headroom. Throttle prefetch/new admission first, then evict authorized unpinned reconstructible cold cache. LRU/TTL ranks qualified objects only. No default global `drop_caches`, sysctl tuning or swap disabling.

Separately report application-cache reduction, admission headroom, logical bytes and attributed physical release. Unlink/hardlinks/open handles/filesystem retention may retain blocks; free-space changes alone prove no attribution. Unproved release is `UNKNOWN`. Reuse qualified small receipts/indexes with original producer/operation; count each release once, without rereading/hashing/copying large science.

## Seal the terminal path first

Freeze acceptance tuple, consumer/validator, actual targets, earliest safe path, stop, and native attempt contract before component checks. Terminal evidence connects adjacent identities through the production consumer/controller; each layer proves only itself.

Separate supervisor pre-start, formal GO/dispatch, and first compute. Declare the budgeted event, proof, and whether recovery remains one attempt. Guard counts discovery, classification, staging, R3 barriers, same-operation reconcile, or pre-verdict repair only when project authority does; renaming never resets budget.

## Use two gates for protected transfer

When protected payload cannot cross before approval, use:

`PRE_APPROVAL_R3A → protected authorization → POST_APPROVAL_R3B → terminal seal → GO/start`

- **R3A** uses final code/config, production transport/controller, real targets/capacity, and a non-sensitive fixture or native dry-run; mock alone is R2. It proves technical reachability, not manifest, READY, transfer authority, or acceptance.
- **Protected authorization** binds subject, targets/purpose/effect, authority/expiry, R3A evidence, follow-on steps, and stop. If it permits in-envelope R3B and GO after its seal, do not re-ask per atom; otherwise seek terminal-start approval after R3B.
- **R3B** installs the real subject, enumerates targets, proves every required object's final identity/location/access/compatibility, reopens final bytes through the production consumer, and checks lease/writer/run state plus the all-target barrier. Only its complete seal supports terminal admission. Projects without preapproval restriction may merge R3A/R3B.

## Make preassembly recoverable

For partial mutation, residue, or crash risk, use one native operation:

`classify every attributable target → preserve or conditionally repair/materialize → all-target barrier → terminal package → start`

Keep operation/transaction identity through recovery. Preserve/quarantine unexpected, wrong, or unknown objects; never overwrite/delete without evidence. Steps repeat idempotently without duplicate dispatch.

Use a bounded native lifecycle; `ABSENT → PREPARED → READY → GO|ABORT → TERMINAL → RETIRED` is only an example. Retire validated terminal/abort roots before new work; mixed/unowned roots fail closed. Prefer absent staging, complete manifest validation, durability, atomic promotion, or native transaction/commit-marker equivalence. Authoritative replacement/durability also needs crash-cutover proof. Guard creates no manifest family, state machine, or recovery controller.

## Bind freshness and seal the search surface

- `STABLE`: immutable code, payload, runtime, or protocol identity; reuse exact evidence when allowed.
- `TRANSITION_BOUND`: staging, publication, installation, or promotion evidence; valid for its transition.
- `TERMINAL_FRESH`: consumer resolution, active path/native identity, search manifest, targets/members, control root, lease/writer/run state, location, capacity, or external transaction; revalidate near terminal under project contract.

Before build/load/terminal consumption, resolve current generation from production compiler/loader/consumer plus native manifest. Prove source, generated output, object/module/link cache, shared build root, index, and runtime contain only current plus explicit compatible dependencies; any reachable retired input blocks.

A native cache key binds source/dependency generation/graph, toolchain, flags/config, ABI/environment, and trust. Repair the earliest invalidated dependency; incrementally rebuild/reseal/revalidate only affected targets. Unproved correspondence or contamination requires bounded isolation, not global clean. After contamination prove one current-only `sources → generated/cache/object → link/package → real consumer` chain before reuse. Complete native hermetic keys suffice, including LIGHT builds; create no Guard cache/build system.

Prefer current manifests/isolated roots; file counts do not prove reachability. Refresh affected terminal seals. Superseded implementations leave active consumption through existing safe retirement, not indiscriminate cleanup.

## Freeze QC and completion claims

Before high-risk compute, freeze native QC validator/schema, inputs/denominator, outcome meanings, downstream effect, acceptance owner, and invalidation. Never invent decision-changing QC after results. Positive tests prove allowed behavior; causal negatives reject bad assembly then pass the real path, not error wording.

`READY_FOR_VALIDATION`, `READY_FOR_TERMINAL_ACTION`, and `PROJECT_ACCEPTED` respectively require defined proof inputs, R3B/native terminal seal, and R4/sole project acceptance. Build success, process exit, V9 no-veto, synthetic/component PASS, file presence, idle lease, or generated instructions cannot substitute; cite seal identity.

An authorized, specified, in-envelope classify/reconcile/proof is executable; it grants no terminal admission before barrier, authority, and acceptance. Finish with terminal state, leases, writers, artifacts reconciled.

After build, necessary computation and consumption, audit the full chain and known in-scope defects once. For a gap, minimally repair the earliest failed dependency, revalidate affected paths, then audit closure again; preserve valid upstream results/evidence. Apply existing recurrence/RESCUE limits. When the chain passes, stop: no unchanged rechecks or unrelated improvements. Backup/archive changes the completion boundary only when the native contract requires it.
