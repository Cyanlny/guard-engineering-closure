# Guard Engineering Closure

A reusable Codex skill for keeping complex engineering work bounded, root-cause-first, and verifiably convergent.

It is designed for multi-stage builds, scientific pipelines, migrations, releases, large dirty worktrees, repeated patch-and-validation loops, and other tasks where scope drift or expensive revalidation can prevent closure.

## What it enforces

- Think and classify before mutation.
- Freeze a bounded closure card and explicit stop point.
- Expand scope only through controlled, evidence-backed rebaselining.
- Repair the producer-to-consumer-to-validator chain in one bounded tranche.
- Reuse unchanged audit conclusions and focused verification by exact identity.
- Keep Git, context, cache, worktree drift, and sub-agent activity contained.
- Run trust-boundary acceptance once per stable source epoch.

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

The installable skill is in [`guard-engineering-closure/`](guard-engineering-closure/). Publishing documentation stays at the repository root so the skill directory itself remains a valid Codex skill package.

## Validation

The release is checked with the Codex skill validator, its two bundled self-test suites, Python bytecode compilation, and a scan for local paths, credentials, private keys, and generated cache files.

## License

No open-source license is included yet. Copyright remains with the repository owner until a license is added.
