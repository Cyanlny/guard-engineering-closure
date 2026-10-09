#!/usr/bin/env python3
"""Read-only cumulative-control guard for engineering closure."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# The active Skill is read-only at runtime; importing it must not create cache
# files beside the published sources.
sys.dont_write_bytecode = True

from closure_guard_core import (  # noqa: E402
    MODES,
    V7_SCHEMA_ID,
    V8_SCHEMA_ID,
    GuardInputError,
    _activation_identity,
    _campaign_budget_report,
    _campaign_control_violations,
    _control_economy_report,
    _control_economy_violations,
    _load,
    _recommended_outcome,
    _rebaseline_violations,
    _validate_snapshot,
    _violation,
    capture,
    compare,
)


def _add_capture_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--repo",
        type=Path,
        help="repository identity; use alone with git/LIGHT or alongside generic facts",
    )
    parser.add_argument(
        "--allowed-paths-from",
        help="newline-delimited planned repository paths; freeze only when taking a baseline",
    )
    parser.add_argument(
        "--facts",
        help="JSON project assertions for generic capture; may be combined with --repo",
    )
    parser.add_argument(
        "--profile",
        choices=("auto", "git", "generic"),
        default="auto",
        help="git rejects facts; generic requires facts; auto selects generic when facts are supplied",
    )
    parser.add_argument(
        "--mode",
        choices=tuple(MODES),
        default="STANDARD",
        help="behavioral risk mode; mode alone does not justify running V9",
    )


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    take = commands.add_parser("snapshot")
    _add_capture_args(take)
    take.add_argument("--predecessor", help="validated V7/V8 import source or V9 accepted-rebaseline predecessor")
    take.add_argument("--accept-rebaseline", action="store_true")
    check = commands.add_parser("compare")
    check.add_argument("--baseline", required=True)
    _add_capture_args(check)
    check.add_argument("--max-control-event-delta", "--max-event-delta", dest="max_event_delta", type=int)
    check.add_argument("--max-mutation-delta", "--max-hotfix-delta", dest="max_hotfix_delta", type=int)
    check.add_argument("--max-expensive-start-delta", type=int)
    check.add_argument("--allow-final-start", action="store_true")
    commands.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        from closure_guard_selftest import run_self_test

        run_self_test()
        return 0
    if args.command == "snapshot":
        if bool(args.predecessor) != bool(args.accept_rebaseline):
            parser.error("--predecessor and --accept-rebaseline must be used together")
        predecessor = _load(args.predecessor) if args.predecessor else None
        current = capture(
            args.repo,
            args.facts,
            args.profile,
            args.mode,
            allowed_paths_from=args.allowed_paths_from,
            accepted_predecessor=predecessor,
        )
        control_violations = _campaign_control_violations(current["facts"])
        control_violations.extend(_control_economy_violations(current["facts"]))
        if (predecessor or {}).get("schema_id") in {V7_SCHEMA_ID, V8_SCHEMA_ID}:
            control_violations = [row for row in control_violations if row["code"] != "CONTROL_FINDINGS_REQUIRED"]
        if control_violations:
            raise GuardInputError(
                control_violations[0]["code"],
                "campaign control is invalid",
                violations=control_violations,
            )
        if predecessor is not None:
            violations = _rebaseline_violations(predecessor, current)
            if violations:
                raise GuardInputError(
                    violations[0]["code"],
                    "accepted rebaseline violates predecessor",
                    violations=violations,
                )
        print(json.dumps(current, indent=2, sort_keys=True))
        return 0
    baseline = _load(args.baseline)
    _validate_snapshot(baseline, "baseline")
    inherited_allowed = None
    if args.allowed_paths_from is None and isinstance(baseline.get("repo"), dict):
        inherited_allowed = baseline["repo"].get("allowed_path_tokens")
    current = capture(
        args.repo,
        args.facts,
        args.profile,
        args.mode,
        allowed_paths_from=args.allowed_paths_from,
        inherited_allowed_path_tokens=inherited_allowed,
        inherited_dirty_records=(baseline.get("repo") or {}).get("dirty_records"),
        inherited_lineage=baseline["lineage"],
        comparison_base_head=(baseline.get("repo") or {}).get("head"),
        inherited_control_event_origin=((baseline.get("facts", {}).get("control_economy") or {}).get("legacy_control_event_count", 0)),
    )
    defaults = MODES[args.mode]
    budgets = (
        defaults["events"] if args.max_event_delta is None else args.max_event_delta,
        defaults["mutations"] if args.max_hotfix_delta is None else args.max_hotfix_delta,
        defaults["expensive"] if args.max_expensive_start_delta is None else args.max_expensive_start_delta,
    )
    if any(x < 0 for x in budgets):
        parser.error("guard budgets must be nonnegative")
    violations = compare(
        baseline,
        current,
        max_event_delta=budgets[0],
        max_hotfix_delta=budgets[1],
        max_expensive_start_delta=budgets[2],
        allow_final_start=args.allow_final_start,
    )
    active_subagent_limit = defaults["subagents"]
    if args.mode == "RESCUE" and baseline.get("facts", {}).get("independent_authority_review_required") is True:
        active_subagent_limit = 2
    report = {
        "status": "BLOCKED" if violations else "PASS",
        "recommended_outcome": _recommended_outcome(violations),
        "mode": args.mode,
        "budgets": {
            "control_events": budgets[0],
            "mutations": budgets[1],
            "expensive_starts": budgets[2],
            "active_subagents": active_subagent_limit,
        },
        "decision_scope": "MACHINE_NO_VETO_ONLY" if not violations else "MACHINE_VETO",
        "violation_count": len(violations),
        "violations": violations,
        "current_snapshot_sha256": current["snapshot_sha256"],
    }
    invalidated = sorted({violation["code"] for violation in violations if any(token in violation["code"] for token in ("DRIFT", "CHANGED", "INVALID", "MISMATCH"))})
    if invalidated:
        report["invalidated_evidence"] = invalidated
    if violations:
        report["minimum_legal_next_action"] = violations[0]["minimum_legal_next_action"]
        if violations[0].get("prohibited_actions"):
            report["prohibited_actions"] = violations[0]["prohibited_actions"]
    campaign_budget = _campaign_budget_report(current["facts"])
    if campaign_budget is not None:
        report["campaign_budget"] = campaign_budget
    control_report = _control_economy_report(current["facts"])
    if control_report is not None:
        report.update(control_report)
    if not violations:
        report["activation_identity"] = _activation_identity(baseline, current, budgets, args.allow_final_start)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2 if violations else 0


def main() -> int:
    try:
        return _main()
    except GuardInputError as exc:
        guidance = {key: value for key, value in _violation(exc.code).items() if key != "code"}
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "reason_code": exc.code,
                    "message": str(exc),
                    **guidance,
                    **exc.details,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "reason_code": "GUARD_INPUT_OR_CAPTURE_INVALID",
                    "message": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
