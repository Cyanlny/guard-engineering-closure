# Verification Economy

Use this policy for every project unless a stricter active authority requires more. Reduce repeated checking without weakening trust boundaries.

## Contents

- Separate three proofs
- Use five reuse classes
- Prefer existing identities
- Use three verification levels
- Key verification results
- Freeze a verification budget
- Invalidate precisely
- Reuse deterministic diagnostic work carefully
- Limit repeated file reads
- Keep caches disposable
- Use the planner
- Report compactly

## Separate three proofs

Do not treat every hash as the same proof:

1. **Content identity:** establish what bytes or Git object exist.
2. **Validation result:** establish that a validator passed for an exact input identity.
3. **Trust-boundary seal:** freshly establish identity when committing, transferring, freezing, or admitting an object.

Reuse content identity and validation results inside their valid scope. Recompute the trust-boundary seal at the boundary.

## Use five reuse classes

Classify every proposed reuse before relying on it:

| Class | Reusable object | Minimum condition |
|---|---|---|
| `R0_CONCLUSION` | file/symbol audit conclusion | content and declared dependency closure unchanged |
| `R1_IDENTITY` | Git OID, manifest identity, or dirty-file hash | identity remains inside its valid writer-free scope |
| `R2_VALIDATION` | focused/static/integration PASS | complete verification key matches |
| `R3_DIAGNOSTIC_ARTIFACT` | immutable deterministic intermediate or sealed diagnostic prefix | bytes, transitive closure, owner/schema/runtime/input, terminal, and purpose match |
| `R4_ACCEPTANCE` | final trust-boundary result | fresh-only unless an existing project authority explicitly defines otherwise |

Do not promote an object from one class to another because it is expensive to recompute. A cached artifact is not a validation PASS; a validation PASS is not a fresh trust-boundary seal.

## Prefer existing identities

Use the least expensive identity that already proves the required fact:

1. Git blob/tree ID for clean tracked source;
2. canonical descriptor/manifest identity for a sealed artifact;
3. one SHA-256 read for a dirty mutable file at a writer-free checkpoint;
4. an aggregate digest over those component identities for a closure.

Do not independently recalculate two hash algorithms over the same bytes, hash an existing hash to create a new authority, or generate a new identity artifact solely to confirm an existing canonical one.

## Use three verification levels

### FAST

Use for planning, status checks, commentary, and read-only monitoring.

- Read repository status, writer state, counters, and identity tokens.
- Do not reopen file contents or recompute full hashes.
- Reuse a prior PASS when its verification key is unchanged.

### INCREMENTAL

Use after a bounded source mutation or typed failure.

- Rehash only new or metadata-changed mutable files.
- Revalidate only changed objects and their direct dependency closure.
- Reuse clean Git blob IDs and unchanged sealed artifact identities.
- Re-read direct callers only when ABI, required-set, signature, owner, schema, or runtime dependencies change.

### SEAL

Use at source freeze, artifact commit, transaction creation, cross-machine transfer, remote admission, and final no-delta.

- Recompute the strong content identity required by the existing canonical boundary.
- Re-run the boundary's sole validator.
- Do not reuse a mutable workspace, old transaction, or diagnostic result as acceptance evidence.

## Key verification results

Reuse a PASS only when this key is exact:

```text
project_id
+ source_or_dirty_epoch
+ object_identity
+ dependency_closure_identity
+ validator_implementation_identity
+ test_list_and_implementation_identity
+ protected owner/schema/runtime/input identities
+ execution_purpose
```

Every key component must be a nonempty immutable content or implementation identity, not a mutable label such as `current` or `latest`.

Treat execution purpose as exact. Diagnostic, test, calibration, migration, remote, release, and production results are not interchangeable even when their source bytes match.

Do not recompute a hash solely for reassurance. Before every recheck, emit one invalidation reason code.

## Freeze a verification budget

Use these defaults unless a stricter active contract says otherwise:

```text
broad_repository_inventory_scans <= 1 per campaign
full_tree_content_hash_scans = 0 before a SEAL boundary
unchanged_full_file_reads <= 1 per exact verification key
focused_validation_runs <= 1 per exact verification key
final_acceptance_runs <= 1 per stable source epoch
```

An exceeded budget is a scheduling defect unless it is justified by `CONTENT_CHANGED`, `DEPENDENCY_CHANGED`, `VALIDATOR_CHANGED`, `AUTHORITY_CHANGED`, `WRITER_AMBIGUITY`, `CRASH_RECOVERY`, or `TRUST_BOUNDARY`. Record the reason, not another copy of the hash.

## Invalidate precisely

| Event | Content hash | Validation result | Downstream |
|---|---|---|---|
| Unrelated clean Git file changes | Reuse | Reuse | None |
| File metadata changes in same epoch | Rehash that mutable file | Revalidate only if content changed | Direct closure only |
| Content or Git blob changes | Recompute | Invalidate | Direct closure |
| Validator/test implementation changes | Reuse content identity | Invalidate | Validator's declared scope |
| Execution purpose changes | Reuse content identity | Invalidate | Purpose-bound consumers |
| ABI/required-set/schema/owner/runtime changes | Recompute affected identities | Invalidate | All direct callers and downstream rows |
| Writer opens the object or epoch changes | Recompute mutable identities | Invalidate affected scope | Affected closure |
| Crash leaves sealing ambiguous | Recompute | Invalidate | Affected transaction |
| Copy, unpack, bundle, cross-run, or cross-machine transfer | Fresh boundary hash | Fresh boundary validation | Destination transaction |
| Freeze, final no-delta, or remote admission | Fresh canonical proof | Fresh canonical validation | Final chain |

Treat mtime, ctime, size, inode, and mode only as same-epoch cache guards under a proven writer-free interval. For a mutable content read, compare `lstat` before and after hashing and the opened descriptor state; reject `WRITER_CHANGED_DURING_CAPTURE` on any mismatch. Never use metadata as a final identity or across trust boundaries.

## Reuse deterministic diagnostic work carefully

Allow `R3_DIAGNOSTIC_ARTIFACT` only when an existing sole validator can prove every condition:

- the artifact or stage already has a sealed terminal;
- bytes, size, member set, and canonical hashes are complete;
- transitive implementation, task/plan, owner, science, schema, runtime, fixture, and input identities match;
- output identity is independent of an old host, mutable cache, run, request, or transaction;
- the new consumer uses a separate diagnostic identity and does not claim acceptance;
- reuse saves more expensive work than the implementation, validation, and identity risk it introduces.

If any proof is absent, reject reuse and run the cheapest current diagnostic path. Do not implement cross-epoch adoption during a rescue campaign merely to avoid one final run.

Never use diagnostic-prefix reuse to replace a required fresh full chain, migration apply, freeze, deployment, remote admission, publication, release, or production acceptance.

## Limit repeated file reads

- Read changed hunks before full files.
- Cache the conclusion for an unchanged symbol/file SHA in the in-memory Closure Card.
- Do not reopen unchanged files to restate an already recorded conclusion.
- Search the repository only for a named symbol, ABI, field, or direct caller; do not rescan broad categories after the audit cutoff.
- Re-read a file when its content identity, declared dependency, validator, or relevant authority changes.
- Count file reads and hash reads as cost. Two consecutive checkpoints with no new invalidation reason must show zero repeated reads.
- Coalesce checks that occur at the same state signature. A terminal that is also a pre-mutation checkpoint needs one capture, not one capture per label.

## Keep caches disposable

- Store only reproducible, non-authoritative objects in a cache.
- Key every reusable entry by the complete verification key and reuse class.
- Keep mutable outputs, transactions, canonical evidence, protected inputs, and final bundles out of a generic cache.
- Verify content after copy, unpack, or cross-machine transfer before use.
- Treat a cache miss as a scheduling event, not evidence of source change.
- Treat a cache hit with an incomplete key as `CACHE_IDENTITY_MISMATCH`, not a reason to weaken validation.
- Do not add a public schema, gate, receipt, or cache service unless it is independently required by the user's current outcome and passes boundary adjudication.

## Use the planner

Use `scripts/verification_economy.py`:

- `snapshot` records path tokens, Git blob/content identities, the verification key, and PASS status without exposing path names;
- snapshots are V3 self-verifying objects; the planner recomputes both snapshot and verification-key hashes before reuse;
- `--execution-purpose` binds the snapshot and PASS to one declared diagnostic, validation, migration, remote, release, or production purpose;
- a `PASS` snapshot requires `--writer-free`; the tool refuses to create one from an ambiguous live state;
- `plan --writer-free` reuses same-epoch hashes only after the caller independently proves no writer; without that flag, dirty files are reread;
- `--trust-boundary` forces fresh content hashing and boundary revalidation;
- `reuse_decision` reports `R2_VALIDATION_REUSE`, `R1_IDENTITY_REUSE_WITH_REVALIDATION`, or `R4_FRESH_SEAL_REQUIRED`; `R3` remains subject to the project's existing artifact validator;
- `self-test` checks reuse, content change, validator change, and trust-boundary behavior.

For `--paths-from`, select only tracked or currently untracked repository objects. Reject `.git`, intermediate symlinks, path escapes, and special files; never follow an untrusted path outside the repository to create a cache identity.

Keep snapshots ephemeral and outside repositories, canonical evidence, and scientific identities. Do not claim reuse from a baseline whose `verification_status` is not `PASS`.

Run the planner once per meaningful checkpoint, not once per message. For a small or clean Git change, ordinary `git diff` plus existing blob IDs may already be sufficient; do not invoke the planner merely because it exists.

The planner targets Git worktrees. For a non-Git project, apply the same key and budget using its existing canonical manifest or package-lock identities; do not add a new manifest solely to make this script applicable.

## Report compactly

Report only:

```text
verification_key
reused_checks
revalidated_checks
fresh_content_hash_reads
metadata_guarded_hash_reuses
git_oid_reuses
invalidation_reason_codes
reuse_decision
trust_boundary=yes|no
```

Do not print full path lists, file contents, payloads, or repeated hashes.
