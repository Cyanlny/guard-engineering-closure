# Project instruction bootstrap

Use only for project `AGENTS.md` or `AGENTS.override.md`. It owns durable instructions, not operation state, Guard arbitration, or acceptance.

## Discover and freeze

- `DRAFT_ONLY` returns a draft/diff without writing; the entry route decides whether the simple no-write exception applies.
- `APPLY_PROJECT_INSTRUCTIONS` changes future guidance. Freeze root, current directory, target/identity, effective chain, scope, write authority, writer state, and validation before arbitration.

Discover without guessing. Under the Codex home, use the first non-empty override, otherwise `AGENTS.md`. From project root to working directory, each directory contributes at most one non-empty override, `AGENTS.md`, or configured fallback, in that order; nearer guidance wins. Do not invent a Git root; without a project root, inspect only the current directory. Unresolved root/fallback is a decision fact. The default 32 KiB limit applies to the combined instruction chain, not Guard.

Ordinary project guides are not automatically discovered. A loaded instruction file must name the decision-changing trigger and local path for any conditional guide it requires. Missing, unreadable, or misrouted guidance is an instruction-load defect, not proof that the project subject failed.

## Promote durable rules

Use attributable instructions, README, manifests, CI/tests, scripts, and data/research protocols. Text is evidence, not automatic authority. Ask only about decision-changing unknowns.

Promote a rule only when it remains valid across future tasks, has authority or a verified native source, changes decisions, and has one proven owner. Otherwise leave it in the plan, handoff, approval package, or unresolved list. Root owns project-wide rules; local contracts belong nearest.

Classify rules as `retain`, `clarify`, `move-to-nested`, `move-to-reference`, `remove-as-duplicate`, or `unresolved`. Preserve user meaning. Never silently remove an unproved rule; overrides and shadowed files are not duplicates without proof.

Keep the durable safety core directly in the effective instruction chain: project outcome and acceptance authority; permission/mutation boundaries; source of truth; canonical workflow and verification; concurrency/subagent isolation; retry/attempt/stop; READY/PASS boundaries; and exact triggers/paths for conditional guides. A guide may own low-frequency migration/cutover, protected transfer, remote/preassembly, or scientific-QC detail, but critical prohibitions cannot exist only there. Simple drafts do not create companion guides mechanically.

Near the configured combined-size limit, remove proven duplication, place genuinely local rules at their nearest directory, and move only low-frequency detail to routed guides. Preserve the inline safety core; do not enlarge global configuration or confuse the project instruction budget with Guard package size.

Never persist Closure Cards, live generations/counters, V9 snapshots/hashes, secrets, hosts/run IDs, temporary approvals, one-off operations, copied Guard rules, a second ledger, unverified commands, or no-veto-as-PASS claims.

## Deliver, write, and verify

Return chain, evidence/unknowns, target structure, complete draft/diff, each material rule's source/reason/owner, unresolved decisions, and write/verification plan. Select only relevant durable domains: outcome/acceptance, authority, mutation, workflow, verification, concurrency, retries, protected effects, completion, recovery. Omit every section unsupported by attributable project evidence; never force generic boilerplate headings.

Apply only an explicitly authorized minimal project patch; instructions cannot grant authority. Global instructions, Codex configuration, and external files need separate authority. Never overwrite dirty/concurrent changes.

Validate Markdown, links, command existence/authority, precedence, conflicts, duplicates, ownership, and combined bytes. This session can validate content and simulate discovery, not prove reload. A fresh run from the target directory must list loaded files and restate effective rules. Neither step is project acceptance.

Supply the decision owner with the requested instruction effect, decisive unknowns, target/owner/scope changes, authority, and no-change evidence. Draft, write, and proof permission never grant a later mutation, terminal, or acceptance capability.
