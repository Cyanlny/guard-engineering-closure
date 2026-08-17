# V21 Dynamic Rescue Profile

Use this profile only for V21 work. Historical event numbers, HEAD values, dirty-path counts, inventories, deadlines, and candidate states are not authority. Derive the live anchor from the current canonical project state at each meaningful checkpoint.

## Contents

- Capture the live anchor
- Decide whether rescue is active
- Freeze the rescue denominator
- Select salvage or retirement
- Preserve V21-specific boundaries
- Measure progress

## Capture the live anchor

At a writer-free checkpoint, read only the minimum canonical fields needed for the next action:

```text
workspace/run identity
repository HEAD or current source generation
dirty tracked/untracked path identities
RUN_STATE current status and event count
active closure inventory identity and open/closed counts
mutation usage/budget
source-stability and highest valid validation layer
active authority projection and revision
active writer/validation process identity
fit/calibration/remote/production/old-resume counters
one current next action and stop point
```

Prefer the canonical current projection over event-name inference. Scan historical events only when replay is required to resolve a declared mismatch. Do not paste hashes or the event chain into context; retain one aggregate identity and named invalidation reasons.

Use `closure_guard.py --profile v21 --run-state ...` only for fields its adapter actually maps. Treat writer absence, allowed paths, active authority, scientific denominators, and terminal semantics as project assertions unless separately proven.

## Decide whether rescue is active

Apply the generic rescue trigger from `SKILL.md`. V21 is in `MID_FLIGHT_RESCUE` when any two applicable conditions hold, such as:

- repeated expensive validation without source stability;
- changed-object surface disproportionate to the active engineering denominator;
- mutation usage at or above 80% of its frozen budget;
- repeated control events without root closure or validation progress;
- rejected authority before governed compute begins;
- a long native run exposing a pre-call ABI or manifest defect.

Do not carry a prior rescue classification forward when the live facts no longer satisfy it. Conversely, do not continue normal scheduling merely because an old next-action field says so.

## Freeze the rescue denominator

Create one current Closure Card from live state:

- keep only already authorized mandatory engineering roots;
- preserve same-root direct consumers through the conditional frontier;
- freeze the planned allowed-path set before mutation;
- keep scientific authority, platform hardening, and final acceptance as separate work classes;
- do not create a new inventory, public profile, validator, schema, or authority branch merely because a broad audit found one;
- preserve every active waiver as `PASS_BY_WAIVER`, never technical PASS.

New findings are proposals. Same producer/interface/authority symptoms merge into an existing root. A genuinely independent blocker requires controlled boundary adjudication and explicit rebaseline before it becomes current work.

## Select salvage or retirement

Choose exactly one:

### TIMEBOXED_SALVAGE

Admit only when the current engineering denominator is finite, one consolidated mutation tranche remains plausible, and one real producer-to-terminal smoke can run before another expensive acceptance.

Freeze:

```text
timebox
root and allowed-path denominators
maximum remaining mutation tranches
one boundary smoke
one final validation chain
stop point
```

### RETIRE_AND_REWRITE

Recommend retirement when the bounded repair is less predictable or more expensive than replacing the implementation behind the same protected contract, or when the first post-rebase boundary smoke reveals another independent root. Preserve history and evidence; do not delete the old version without explicit authorization.

Do not automatically switch paths after elapsed time. Report the failed salvage condition and obtain the required user decision.

## Preserve V21-specific boundaries

- Never read patient, held-out, formal, publication, or release results to choose a scientific value.
- Never restart or resume an old transaction to recover monitoring or save time.
- Never use a full 338/6/25 or multi-hour native vertical as an interface debugger.
- Do not rebuild generated projections, freeze, or identities while planned source mutations remain.
- Do not start calibration or scientific compute while its active authority or execution profile is unresolved.
- Keep remote validation fresh and unique when required; stop at the user-defined pre-production boundary.
- Defer generic retry, cache platforms, cross-epoch adoption, process frameworks, privacy frameworks, and delivery hardening unless a reproduced direct blocker makes one mandatory and it passes adjudication.

## Measure progress

At each meaningful checkpoint require:

```text
new_unapproved_path_count = 0
new_root_count = 0
new_unapproved_authority_branch_count = 0
duplicate_expensive_run_count = 0
open_items decrease OR highest_validated_layer advances
monotonic counters never regress
```

If two consecutive checkpoints add control state without root closure or validation progress, stop with `CONTROL_PLANE_GROWTH_WITHOUT_CLOSURE_PROGRESS`. Reuse unchanged conclusions, identities, and exact-key focused PASS results; perform final trust-boundary validation freshly once.
