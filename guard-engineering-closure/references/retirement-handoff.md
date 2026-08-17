# Retirement and Handoff

Use this protocol when bounded salvage ends in retire/rewrite, when a project is migrated into a new repository or environment, or when an implementation is preserved for selective reuse.

## Freeze the retirement boundary

Record the retired source identity, validation status, stop reason, protected contracts, retained scientific/owner decisions, and the exact point at which old execution authority ends. Preserve append-only history and evidence; do not delete, rewrite, or promote incomplete work.

Classify every retained object:

```text
VALIDATED_BASELINE
UNVALIDATED_REUSE_SOURCE
PROVENANCE_ONLY
DEFERRED_CANDIDATE
EXCLUDED_PROTECTED_OR_RUNTIME_STATE
```

Never let unvalidated source, old receipts, cached PASS results, active transactions, or generated identities become acceptance evidence in the successor project.

## Build the smallest reusable handoff

Include only material required to reproduce or re-evaluate the protected contract:

- protocol and activated decisions with explicit status;
- source snapshots with origin and content identity;
- reusable scientific/engineering code and applicable tests;
- architecture and request/result/terminal contracts;
- exclusions and invalidation rules;
- one start prompt or agent instruction file when requested;
- a file manifest and deterministic integrity verifier.

Exclude protected data, held-out/formal results, credentials, active run state, mutable workspaces, old transactions, canonical production evidence, and model/result bundles unless an explicit migration authority requires them.

## Start the successor safely

Use a fresh repository, workspace, run/request/runtime/transaction identity, and validation generation. The first actions are package verification, a new Closure Card, authority reconciliation, and a no-protected-data boundary design or smoke. Do not connect remote compute or ingest protected data merely because the package unpacked successfully.

Migrate source file by file or bounded component by bounded component. Preserve old relative paths only when useful; never overwrite the validated baseline with unvalidated source. Let the successor Git history record each admitted migration.

## Verify the handoff

- parse all machine-readable and source files;
- verify the exact file set, sizes, and hashes before and after archive extraction;
- scan for excluded data, credentials, absolute mutable paths, and runtime state;
- run only bootstrap/control-plane tests, not retired scientific acceptance;
- prove that the retired repository was not mutated by packaging;
- report which objects are validated, unvalidated, deferred, rejected, or waiver-backed.

Successful package verification proves handoff integrity only. It does not validate the migrated science, implementation, or final project.
