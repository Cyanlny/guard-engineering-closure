# Execution-Boundary Integrity

Use this protocol before a long/native operation, cross-process or cross-machine dispatch, validation acceptance, artifact admission, freeze, publish, deploy, or release. It defines required proofs, not a new supervisor, artifact bus, validator, or public gate.

## Contents

- Prove writer and process ownership
- Admit long execution
- Require credible validation
- Seal exact artifacts
- Release only through a predicate

## Prove writer and process ownership

Bind writer/process proof to the applicable workspace, cwd, PID tree or lease, start time, run/stage/action, execution purpose, and transaction. Process-name matching is only a discovery hint.

Before mutation or a trust boundary, require:

```text
active_mutators <= 1
active_expensive_runs <= 1
the target workspace has no conflicting writer
the controller/sealer identity is unique
```

Treat `writer_free=true` as `PROJECT_ASSERTION` unless an existing lease/process validator proves it. Do not signal an unrelated process merely because its executable name matches.

## Admit long execution

Before start, freeze the execution purpose, immutable source/runtime/input/request identities, expected outputs, one terminal owner, resource policy, liveness policy, retry semantics, and stop point.

Resource admission measures the actual filesystems and runtime limits used by staging, scratch, archive, checkpoint, and outputs. Dynamic observations belong to execution evidence, not scientific identity. Insufficient mandatory resources produce a typed resource failure; do not lower the workload or governed denominator.

For registered leaf-native processes, require a scope-owned hard deadline or an explicit proof that another bounded supervisor owns liveness. Unknown scope cannot inherit a broad default. Bind monotonic clock, signal/grace/reap behavior, stream hashes/counts, partial-output quarantine, and `retryable` to execution identity. Aggregate controllers must not silently inherit a leaf timeout.

Timeout, signal, crash, or lost child produces one typed terminal, admits no partial PASS, and never resumes the old transaction. Keep controller and unrelated process groups alive.

## Require credible validation

Do not infer validation PASS from module/process return code alone. For every accepted validation unit require:

```text
discovered = executed + skipped
executed = passed + failed + errors + xfail + xpass
executed > 0
failed = errors = skipped = xfail = xpass = 0
validator and test-list implementation identities are exact
one durable outer terminal exists
```

Use the project's explicit convention if it counts skipped tests as executed, but freeze that convention before the run and still reject all-skipped or zero-test acceptance. Partial progress receipts remain diagnostic and cannot be promoted to final PASS.

## Seal exact artifacts

At an artifact or transfer boundary, require the existing sole validator to prove:

- strict canonical serialization at the trust boundary;
- exact declared member/output set and cardinality;
- safe relative paths and containment;
- no undeclared sidecars, path escape, symlink, hardlink, or special-file laundering;
- exact artifact ID, path, bytes, size, hash, classification, owner, and identity echo;
- producer-selected classification cannot override compiler/owner classification;
- staging, durable file, atomic replace, parent durability, and terminal marker last;
- fresh verification after copy, unpack, cross-run, or cross-machine transfer.

Privacy, data-grain, and secret rules remain project-owned. Opaque public output fails closed unless an existing route-specific validator proves its permitted structure and classification.

## Release only through a predicate

An explicit request to start a final boundary is necessary but not sufficient. Before allowing it, require every applicable condition:

```text
open items = 0
remaining planned mutations = 0
blockers = 0
writer/process proof is current
active mutators = active expensive runs = 0
authority is ACTIVATED or NOT_APPLICABLE
real boundary smoke PASS matches current generation
validation execution evidence is complete and clean
run-state replay/projection is consistent
fresh transaction/purpose identity is required
```

If a project has no authority, run state, protected data, or long process, mark that field `NOT_APPLICABLE`; do not invent it. A command-line allow flag cannot replace the predicate.
