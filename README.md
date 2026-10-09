# Guard Engineering Closure

A project-agnostic Codex skill for bounded, root-cause-first closure of complex engineering and scientific work.

Current release: **V9_OPTIMIZED_STABLE**. The machine schema remains `ENGINEERING_CLOSURE_GUARD_SNAPSHOT_V9`.

## What it does

- Keep ordinary isolated, reversible, low-impact work on the native-only LIGHT route.
- Classify the current legal action separately from later execution permission and project acceptance.
- Audit broadly, then limit changes to the smallest proven causal delta and necessary direct consumers.
- Require scientific closure through **real input → necessary scientific computation → real result → actual downstream consumption**.
- Reuse qualified evidence and valid scientific results; rebuild, reseal, and revalidate only affected dependencies.
- Preserve authority, active-object identity, healthy running generations, bounded recovery, and safe retirement.
- Check resource admission and reclaim eligible cache through existing project-native workflows.
- Load specialized references only when their risk changes the decision; support explicitly requested project-instruction drafting and governance.

Guard is not a scheduler, cache service, project state database, or scientific validator. Necessary deliverables are not automatically new control mechanisms. V9 PASS/CONTINUE means no machine veto, not permission or project PASS; project-native authority and validators remain decisive.

## Install with Codex

Ask Codex:

```text
Use $skill-installer to install guard-engineering-closure from this GitHub repository, using the path guard-engineering-closure.
```

Or use the bundled installer directly:

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo Cyanlny/guard-engineering-closure \
  --path guard-engineering-closure
```

Restart Codex after installation so it discovers the new skill.

## Repository layout

The installable skill is in [`guard-engineering-closure/`](guard-engineering-closure/): **13 files, 7 conditional references, and 4 scripts**. Publishing documentation stays at the repository root.

Start with [SKILL.md](guard-engineering-closure/SKILL.md). Read the [V9 machine contract](guard-engineering-closure/references/v9-machine-contract.md) before invoking machine checks. Risk, complexity, or Git alone does not activate V9; required project control facts must come from attributable authority, not invented caller assertions.

The verification-reuse helper plans selected-object reuse only. It does not run a project validator, establish permission, or grant acceptance. Keep project-specific adapters and state outside this reusable package.
