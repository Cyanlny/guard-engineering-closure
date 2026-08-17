#!/usr/bin/env python3
"""Read-only, capability-aware scope guard for engineering closure."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCHEMA_ID = "ENGINEERING_CLOSURE_GUARD_SNAPSHOT_V3"
MODES = {
    "LIGHT": {"events": 0, "mutations": 1, "expensive": 1, "subagents": 0},
    "STANDARD": {"events": 4, "mutations": 1, "expensive": 1, "subagents": 2},
    "RESCUE": {"events": 2, "mutations": 1, "expensive": 1, "subagents": 1},
}
LIST_FIELDS = (
    "closure_item_ids", "open_item_ids", "blocker_ids", "delegated_task_ids",
    "capabilities",
)
INT_FIELDS = (
    "closure_item_count",
    "open_item_count",
    "closed_item_count",
    "planned_mutation_count",
    "completed_mutation_count",
    "validation_rank",
    "control_event_count",
    "active_mutator_count",
    "active_expensive_run_count",
    "expensive_start_count",
    "delegated_task_count",
    "subagent_spawn_count",
    "active_subagent_count",
    "active_subagent_mutator_count",
    "active_subagent_expensive_run_count",
    "recursive_delegation_count",
    "final_boundary_start_count",
    "authority_revision_count",
)
TEXT_FIELDS = ("project_id", "change_generation", "validation_level", "authority_status")
BOOL_FIELDS = ("independent_authority_review_required",)
FACT_FIELDS = set(LIST_FIELDS + INT_FIELDS + TEXT_FIELDS + BOOL_FIELDS)
CAPABILITIES = {
    "authority",
    "blockers",
    "closure_items",
    "control_events",
    "delegation",
    "expensive_operations",
    "final_boundary",
    "mutations",
    "mutators",
    "validation_ladder",
    "vcs",
}
AUTHORITY_TOKENS = (
    "CANDIDATE_AUTHORIZED",
    "PROTOCOL_AUTHORIZED",
    "AUTHORITY_DECISION_ACTIVATED",
    "PATH_SELECTED",
)


def _run(argv: list[str], cwd: Path) -> bytes:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ).stdout


def _digest(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"nonfinite JSON value is prohibited: {value}")


def _strict_json_text(text: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _tokens(kind: str, values: list[str]) -> list[str]:
    return sorted(hashlib.sha256(f"{kind}:{v}".encode()).hexdigest() for v in values)


def _paths(payload: bytes) -> list[str]:
    return sorted(x.decode("utf-8") for x in payload.split(b"\0") if x)


def _normalize_repo_path(repo: Path, value: str) -> str:
    candidate = Path(value)
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(repo.resolve())
        except ValueError as exc:
            raise ValueError(f"allowed path escapes repository: {value}") from exc
    normalized = Path(str(candidate).replace("\\", "/"))
    if str(normalized) in ("", ".") or ".." in normalized.parts or ".git" in normalized.parts:
        raise ValueError(f"invalid allowed repository path: {value}")
    return normalized.as_posix()


def _allowed_path_tokens(repo: Path, source: str | None) -> list[str]:
    if source is None:
        return []
    text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    paths = {
        _normalize_repo_path(repo, line.strip())
        for line in text.splitlines()
        if line.strip()
    }
    return _tokens("path", sorted(paths))


def _git(
    repo: Path,
    *,
    allowed_paths_from: str | None = None,
    inherited_allowed_path_tokens: list[str] | None = None,
) -> dict[str, Any]:
    repo = repo.resolve()
    tracked = _paths(_run(["git", "diff", "HEAD", "--name-only", "-z"], repo))
    untracked = _paths(
        _run(["git", "ls-files", "--others", "--exclude-standard", "-z"], repo)
    )
    tracked_tokens = _tokens("tracked", tracked)
    untracked_tokens = _tokens("untracked", untracked)
    changed_path_tokens = _tokens("path", sorted(set(tracked) | set(untracked)))
    allowed_tokens = (
        _allowed_path_tokens(repo, allowed_paths_from)
        if allowed_paths_from is not None
        else sorted(inherited_allowed_path_tokens or [])
    )
    return {
        "repo_token": _tokens("repo", [str(repo)])[0],
        "head": _run(["git", "rev-parse", "HEAD"], repo).decode().strip(),
        "tracked_changed_count": len(tracked),
        "untracked_count": len(untracked),
        "tracked_path_tokens": tracked_tokens,
        "untracked_path_tokens": untracked_tokens,
        "changed_path_tokens": changed_path_tokens,
        "allowed_path_tokens": allowed_tokens,
        "allowed_path_count": len(allowed_tokens),
        "changed_paths_sha256": _digest([tracked_tokens, untracked_tokens]),
    }


def _nonnegative(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a nonnegative integer or null")
    return value


def _strings(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ValueError(f"{field} must be a list of strings")
    if any(not x.strip() for x in value):
        raise ValueError(f"{field} contains an empty string")
    if len(value) != len(set(value)):
        raise ValueError(f"{field} contains duplicates")
    return sorted(value)


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("closure facts must be a JSON object")
    unknown = set(raw) - FACT_FIELDS
    if unknown:
        raise ValueError(f"unknown closure facts: {sorted(unknown)}")
    for field in TEXT_FIELDS:
        if raw.get(field) is not None and not isinstance(raw[field], str):
            raise ValueError(f"{field} must be a string or null")
        if isinstance(raw.get(field), str) and not raw[field].strip():
            raise ValueError(f"{field} must be nonempty when supplied")
    for field in BOOL_FIELDS:
        if raw.get(field) is not None and not isinstance(raw[field], bool):
            raise ValueError(f"{field} must be a boolean or null")

    raw_ids = {
        field: _strings(raw.get(field), field)
        for field in LIST_FIELDS[:-1]
    }
    ids = {field: _tokens(field, values) for field, values in raw_ids.items()}
    counts = {field: _nonnegative(raw.get(field), field) for field in INT_FIELDS}
    for id_field, count_field in (
        ("closure_item_ids", "closure_item_count"),
        ("open_item_ids", "open_item_count"),
        ("delegated_task_ids", "delegated_task_count"),
    ):
        if ids[id_field]:
            size = len(ids[id_field])
            if counts[count_field] not in (None, size):
                raise ValueError(f"{count_field} disagrees with {id_field}")
            counts[count_field] = size

    if "closure_item_ids" in raw and "open_item_ids" in raw:
        outside = set(raw_ids["open_item_ids"]) - set(raw_ids["closure_item_ids"])
        if outside:
            raise ValueError("open_item_ids must be a subset of closure_item_ids")
    closure_count = counts["closure_item_count"]
    open_count = counts["open_item_count"]
    closed_count = counts["closed_item_count"]
    if all(isinstance(value, int) for value in (closure_count, open_count, closed_count)):
        if closure_count != open_count + closed_count:
            raise ValueError(
                "closure_item_count must equal open_item_count plus closed_item_count"
            )

    capabilities = set(_strings(raw.get("capabilities"), "capabilities"))
    inference = {
        "closure_items": counts["closure_item_count"] is not None
        or counts["open_item_count"] is not None
        or counts["closed_item_count"] is not None,
        "blockers": bool(ids["blocker_ids"]),
        "mutations": counts["planned_mutation_count"] is not None
        or counts["completed_mutation_count"] is not None,
        "validation_ladder": counts["validation_rank"] is not None,
        "control_events": counts["control_event_count"] is not None,
        "delegation": bool(ids["delegated_task_ids"])
        or counts["delegated_task_count"] is not None
        or counts["subagent_spawn_count"] is not None
        or counts["active_subagent_count"] is not None
        or counts["active_subagent_mutator_count"] is not None
        or counts["active_subagent_expensive_run_count"] is not None
        or counts["recursive_delegation_count"] is not None,
        "mutators": counts["active_mutator_count"] is not None,
        "expensive_operations": counts["active_expensive_run_count"] is not None
        or counts["expensive_start_count"] is not None,
        "final_boundary": counts["final_boundary_start_count"] is not None,
        "authority": raw.get("authority_status") is not None
        or counts["authority_revision_count"] is not None
        or raw.get("independent_authority_review_required") is not None,
    }
    capabilities.update(name for name, present in inference.items() if present)
    unknown_caps = capabilities - CAPABILITIES
    if unknown_caps:
        raise ValueError(f"unknown capabilities: {sorted(unknown_caps)}")
    delegated_count = counts["delegated_task_count"]
    subagent_spawns = counts["subagent_spawn_count"]
    active_subagents = counts["active_subagent_count"]
    if isinstance(delegated_count, int):
        if isinstance(subagent_spawns, int) and subagent_spawns > delegated_count:
            raise ValueError("subagent_spawn_count exceeds delegated_task_count")
        if isinstance(active_subagents, int) and active_subagents > delegated_count:
            raise ValueError("active_subagent_count exceeds delegated_task_count")
    project = raw.get("project_id")
    return {
        "project_token": _tokens("project", [project])[0] if project else None,
        "change_generation": raw.get("change_generation"),
        **ids,
        **counts,
        "blocker_count": len(ids["blocker_ids"]),
        "validation_level": raw.get("validation_level"),
        "authority_status": raw.get("authority_status"),
        "independent_authority_review_required": raw.get(
            "independent_authority_review_required", False
        ),
        "capabilities": sorted(capabilities),
    }


def _max(events: list[Any], field: str) -> int:
    values = [
        event[field]
        for event in events
        if isinstance(event, dict)
        and isinstance(event.get(field), int)
        and not isinstance(event[field], bool)
    ]
    return max(values, default=0)


def _identifier(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return next(
            (value[k] for k in ("blocker_id", "id", "reason_code") if isinstance(value.get(k), str)),
            "OBJECT_WITHOUT_ID",
        )
    return str(value)


def _v21(path: Path) -> dict[str, Any]:
    state = _strict_json_text(path.read_text(encoding="utf-8"), "V21 run state")
    events = state.get("event_chain") if isinstance(state.get("event_chain"), list) else []
    types = [str(e.get("event_type", "")) for e in events if isinstance(e, dict)]
    blockers = state.get("BLOCKERS") if isinstance(state.get("BLOCKERS"), list) else []
    inventory = state.get("active_rcg18_execution_output_abi_runtime_control_inventory")
    inventory = inventory if isinstance(inventory, dict) else {}
    consumed = inventory.get("consumed_hotfix_ordinals")
    consumed = consumed if isinstance(consumed, list) else []
    stability = str(inventory.get("source_stability", ""))
    rank = 2 if stability in {"POST", "STABLE", "SOURCE_STABLE", "CLEAN"} else 0
    rank = max(rank, 3 if state.get("ENGINEERING_READY") is True else 0)
    rank = max(rank, 4 if state.get("CLEAN_VALIDATED") is True else 0)
    authority_status = next(
        (
            str(state[key])
            for key in (
                "AUTHORITY_STATUS",
                "authority_status",
                "active_authority_status",
                "scientific_authority_status",
            )
            if isinstance(state.get(key), str) and str(state[key]).strip()
        ),
        None,
    )
    if authority_status is None:
        authority_status = "OTHER"
        for event_type in reversed(types):
            if "REJECTED" in event_type:
                authority_status = "REJECTED"
                break
            if any(token in event_type for token in AUTHORITY_TOKENS):
                authority_status = "ACTIVE"
                break
    return _normalize(
        {
            "project_id": state.get("run_id", "V21"),
            "change_generation": str(_max(events, "source_mutation_count")),
            "closure_item_count": inventory.get("root_cause_count"),
            "blocker_ids": sorted(_identifier(x) for x in blockers),
            "completed_mutation_count": len(consumed),
            "validation_level": stability or None,
            "validation_rank": rank,
            "control_event_count": len(events),
            "expensive_start_count": _max(events, "fit_start_count")
            + _max(events, "threshold_calibration_run_count"),
            "final_boundary_start_count": _max(events, "remote_start_count")
            + _max(events, "production_start_count"),
            "authority_status": authority_status,
            "authority_revision_count": sum(
                any(token in event_type for token in AUTHORITY_TOKENS)
                for event_type in types
            ),
        }
    )


def _load(value: str) -> dict[str, Any]:
    text = sys.stdin.read() if value == "-" else Path(value).read_text(encoding="utf-8")
    return _strict_json_text(text, "guard JSON input")


def _validate_snapshot(snapshot: Any, label: str) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        raise ValueError(f"{label} must be a JSON object")
    required = {"schema_id", "profile", "mode", "repo", "facts", "snapshot_sha256"}
    if set(snapshot) != required:
        raise ValueError(f"{label} fields do not match schema V3")
    if snapshot.get("schema_id") != SCHEMA_ID:
        raise ValueError(f"{label} schema is incompatible; capture a fresh V3 baseline")
    if snapshot.get("profile") not in {"git", "generic", "v21"}:
        raise ValueError(f"{label} has an invalid profile")
    if snapshot.get("mode") not in MODES:
        raise ValueError(f"{label} has an invalid mode")
    facts = snapshot.get("facts")
    fact_fields = (
        set(LIST_FIELDS[:-1])
        | set(INT_FIELDS)
        | {
            "project_token", "change_generation", "blocker_count", "validation_level",
            "authority_status", "independent_authority_review_required", "capabilities",
        }
    )
    if not isinstance(facts, dict) or set(facts) != fact_fields:
        raise ValueError(f"{label} facts are malformed")
    capabilities = facts.get("capabilities")
    if (
        not isinstance(capabilities, list)
        or not all(isinstance(value, str) for value in capabilities)
        or not set(capabilities) <= CAPABILITIES
    ):
        raise ValueError(f"{label} capabilities are malformed")
    for field in LIST_FIELDS[:-1]:
        if not isinstance(facts.get(field), list):
            raise ValueError(f"{label} {field} is malformed")
    for field in INT_FIELDS + ("blocker_count",):
        value = facts.get(field)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ValueError(f"{label} {field} is malformed")
    if not isinstance(facts.get("independent_authority_review_required"), bool):
        raise ValueError(f"{label} authority-review fact is malformed")
    repo = snapshot.get("repo")
    if repo is not None:
        repo_fields = {
            "repo_token", "head", "tracked_changed_count", "untracked_count",
            "tracked_path_tokens", "untracked_path_tokens", "changed_path_tokens",
            "allowed_path_tokens", "allowed_path_count", "changed_paths_sha256",
        }
        if not isinstance(repo, dict) or set(repo) != repo_fields:
            raise ValueError(f"{label} repository facts are malformed")
        for field in (
            "tracked_path_tokens", "untracked_path_tokens", "changed_path_tokens",
            "allowed_path_tokens",
        ):
            if not isinstance(repo.get(field), list):
                raise ValueError(f"{label} repository token list is malformed")
    expected = snapshot.get("snapshot_sha256")
    payload = {key: value for key, value in snapshot.items() if key != "snapshot_sha256"}
    if not isinstance(expected, str) or expected != _digest(payload):
        raise ValueError(f"{label} snapshot hash mismatch")
    return snapshot


def capture(
    repo: Path | None,
    run_state: Path | None,
    facts_path: str | None,
    profile: str,
    mode: str,
    allowed_paths_from: str | None = None,
    inherited_allowed_path_tokens: list[str] | None = None,
) -> dict[str, Any]:
    profile = (
        "v21" if profile == "auto" and run_state else
        "generic" if profile == "auto" and facts_path else
        "git" if profile == "auto" else profile
    )
    if profile == "v21" and not run_state:
        raise ValueError("v21 profile requires --run-state")
    if profile == "generic" and not facts_path:
        raise ValueError("generic profile requires --facts")
    if profile == "v21" and facts_path:
        raise ValueError("v21 profile does not consume --facts")
    if profile == "generic" and run_state:
        raise ValueError("generic profile does not consume --run-state")
    if profile == "git" and (run_state or facts_path):
        raise ValueError("git profile consumes only --repo")
    if not any((repo, run_state, facts_path)):
        raise ValueError("provide --repo, --run-state, or --facts")
    facts = (
        _v21(run_state.resolve()) if profile == "v21" else
        _normalize(_load(facts_path)) if profile == "generic" else
        _normalize({"capabilities": ["vcs"]})
    )
    snapshot = {
        "schema_id": SCHEMA_ID,
        "profile": profile,
        "mode": mode,
        "repo": _git(
            repo,
            allowed_paths_from=allowed_paths_from,
            inherited_allowed_path_tokens=inherited_allowed_path_tokens,
        ) if repo else None,
        "facts": facts,
    }
    snapshot["snapshot_sha256"] = _digest(snapshot)
    return snapshot


def _violation(code: str, **details: Any) -> dict[str, Any]:
    return {"code": code, **details}


def _increase(out: list[dict[str, Any]], before: Any, after: Any, code: str) -> None:
    if isinstance(before, int) and isinstance(after, int) and after > before:
        out.append(_violation(code, before=before, after=after))


def _regression(out: list[dict[str, Any]], before: Any, after: Any, code: str) -> None:
    if isinstance(before, int) and isinstance(after, int) and after < before:
        out.append(_violation(code, before=before, after=after))


def compare(
    baseline: dict[str, Any],
    current: dict[str, Any],
    *,
    max_event_delta: int,
    max_hotfix_delta: int,
    max_expensive_start_delta: int = 1,
    allow_science_revision: bool,
    allow_final_start: bool,
) -> list[dict[str, Any]]:
    if not isinstance(baseline, dict):
        return [_violation("BASELINE_SNAPSHOT_INVALID", reason="baseline must be an object")]
    if not isinstance(current, dict):
        return [_violation("CURRENT_SNAPSHOT_INVALID", reason="current snapshot must be an object")]
    if baseline.get("schema_id") != SCHEMA_ID:
        return [_violation("BASELINE_SCHEMA_INCOMPATIBLE", expected=SCHEMA_ID)]
    try:
        _validate_snapshot(baseline, "baseline")
    except ValueError as exc:
        return [_violation("BASELINE_SNAPSHOT_INVALID", reason=str(exc))]
    try:
        _validate_snapshot(current, "current snapshot")
    except ValueError as exc:
        return [_violation("CURRENT_SNAPSHOT_INVALID", reason=str(exc))]
    out: list[dict[str, Any]] = []
    for field, code in (("profile", "GUARD_PROFILE_CHANGED"), ("mode", "GUARD_MODE_CHANGED")):
        if baseline.get(field) != current.get(field):
            out.append(_violation(code, before=baseline.get(field), after=current.get(field)))

    before_repo, after_repo = baseline.get("repo"), current.get("repo")
    if isinstance(before_repo, dict) != isinstance(after_repo, dict):
        out.append(_violation("PROJECT_IDENTITY_SOURCE_CHANGED"))
    elif isinstance(before_repo, dict):
        if before_repo.get("repo_token") != after_repo.get("repo_token"):
            out.append(_violation("PROJECT_CHANGED"))
        if before_repo.get("head") != after_repo.get("head"):
            out.append(
                _violation(
                    "WORKTREE_HEAD_CHANGED",
                    before=before_repo.get("head"),
                    after=after_repo.get("head"),
                )
            )
        before_allowed = set(before_repo.get("allowed_path_tokens", []))
        after_allowed = set(after_repo.get("allowed_path_tokens", []))
        if before_allowed != after_allowed:
            out.append(_violation("ALLOWED_PATH_SET_CHANGED"))
        outside = sorted(
            set(after_repo.get("changed_path_tokens", []))
            - set(before_repo.get("changed_path_tokens", []))
            - before_allowed
        )
        if outside:
            out.append(
                _violation("FROZEN_PATH_SET_EXPANDED", count=len(outside), path_tokens=outside)
            )

    before, after = baseline["facts"], current["facts"]
    if before.get("project_token") != after.get("project_token"):
        out.append(_violation("PROJECT_CHANGED"))
    old_caps, new_caps = set(before["capabilities"]), set(after["capabilities"])
    added_caps = sorted(new_caps - old_caps)
    removed_caps = sorted(old_caps - new_caps)
    if added_caps:
        out.append(_violation("CAPABILITY_SET_EXPANDED", capabilities=added_caps))
    if removed_caps:
        out.append(_violation("CAPABILITY_SET_REDUCED", capabilities=removed_caps))

    if "closure_items" in old_caps | new_caps:
        new_items = sorted(set(after["closure_item_ids"]) - set(before["closure_item_ids"]))
        if new_items:
            out.append(_violation("CLOSURE_ITEM_SET_EXPANDED", count=len(new_items)))
        reopened = sorted(set(after["open_item_ids"]) - set(before["open_item_ids"]))
        if reopened:
            out.append(_violation("OPEN_ITEM_SET_EXPANDED", count=len(reopened)))
        for field, code in (
            ("closure_item_count", "CLOSURE_ITEM_DENOMINATOR_INCREASED"),
            ("open_item_count", "OPEN_ITEM_COUNT_INCREASED"),
        ):
            _increase(out, before.get(field), after.get(field), code)
        b, a = before.get("closed_item_count"), after.get("closed_item_count")
        if isinstance(b, int) and isinstance(a, int) and a < b:
            out.append(_violation("CLOSED_ITEM_COUNT_REGRESSED", before=b, after=a))
    if "blockers" in old_caps | new_caps:
        new_blockers = sorted(set(after["blocker_ids"]) - set(before["blocker_ids"]))
        if new_blockers:
            out.append(_violation("BLOCKER_SET_CHANGED", count=len(new_blockers)))
        _increase(out, before["blocker_count"], after["blocker_count"], "BLOCKER_DENOMINATOR_INCREASED")
    if "mutations" in old_caps | new_caps:
        _increase(
            out, before.get("planned_mutation_count"), after.get("planned_mutation_count"),
            "PLANNED_MUTATION_COUNT_INCREASED",
        )
        b, a = before.get("completed_mutation_count"), after.get("completed_mutation_count")
        _regression(out, b, a, "COMPLETED_MUTATION_COUNT_REGRESSED")
        if isinstance(b, int) and isinstance(a, int) and a - b > max_hotfix_delta:
            out.append(_violation("MUTATION_BUDGET_DELTA_EXCEEDED", delta=a - b, allowed=max_hotfix_delta))
    if "control_events" in old_caps | new_caps:
        b, a = before.get("control_event_count"), after.get("control_event_count")
        _regression(out, b, a, "CONTROL_EVENT_COUNT_REGRESSED")
        if isinstance(b, int) and isinstance(a, int) and a - b > max_event_delta:
            out.append(_violation("CONTROL_EVENT_BUDGET_EXCEEDED", delta=a - b, allowed=max_event_delta))
    if "delegation" in old_caps | new_caps:
        new_tasks = sorted(
            set(after.get("delegated_task_ids", []))
            - set(before.get("delegated_task_ids", []))
        )
        if new_tasks:
            out.append(_violation("DELEGATED_TASK_SET_EXPANDED", count=len(new_tasks)))
        _increase(
            out, before.get("delegated_task_count"), after.get("delegated_task_count"),
            "DELEGATED_TASK_DENOMINATOR_INCREASED",
        )
        _regression(
            out,
            before.get("subagent_spawn_count"),
            after.get("subagent_spawn_count"),
            "SUBAGENT_SPAWN_COUNT_REGRESSED",
        )
        limit = MODES.get(current.get("mode"), {}).get("subagents", 0)
        if (
            current.get("mode") == "RESCUE"
            and before.get("independent_authority_review_required") is True
        ):
            limit = 2
        active = after.get("active_subagent_count") or 0
        if active > limit:
            out.append(_violation("ACTIVE_SUBAGENT_LIMIT_EXCEEDED", active=active, allowed=limit))
        if (after.get("active_subagent_mutator_count") or 0) > 0:
            out.append(_violation("DELEGATED_MUTATION_PROHIBITED"))
        if (after.get("active_subagent_expensive_run_count") or 0) > 0:
            out.append(_violation("DELEGATED_EXPENSIVE_RUN_PROHIBITED"))
        if (after.get("recursive_delegation_count") or 0) > 0:
            out.append(_violation("RECURSIVE_DELEGATION_PROHIBITED"))
    if "validation_ladder" in old_caps | new_caps and before.get("change_generation") == after.get("change_generation"):
        b, a = before.get("validation_rank"), after.get("validation_rank")
        if isinstance(b, int) and isinstance(a, int) and a < b:
            out.append(_violation("VALIDATION_LEVEL_REGRESSED", before=b, after=a))
    if "mutators" in new_caps and (after.get("active_mutator_count") or 0) > 1:
        out.append(_violation("CONCURRENT_MUTATORS", active=after["active_mutator_count"]))
    if "expensive_operations" in old_caps | new_caps:
        if (after.get("active_expensive_run_count") or 0) > 1:
            out.append(_violation("CONCURRENT_EXPENSIVE_RUNS", active=after["active_expensive_run_count"]))
        b, a = before.get("expensive_start_count"), after.get("expensive_start_count")
        _regression(out, b, a, "EXPENSIVE_START_COUNT_REGRESSED")
        if isinstance(b, int) and isinstance(a, int) and a - b > max_expensive_start_delta:
            out.append(_violation("EXPENSIVE_RUN_BUDGET_EXCEEDED", delta=a - b, allowed=max_expensive_start_delta))
    if "authority" in old_caps | new_caps:
        if (
            before.get("independent_authority_review_required")
            != after.get("independent_authority_review_required")
        ):
            out.append(_violation("AUTHORITY_REVIEW_REQUIREMENT_CHANGED"))
        b, a = before.get("authority_revision_count"), after.get("authority_revision_count")
        _regression(out, b, a, "AUTHORITY_REVISION_COUNT_REGRESSED")
        if (
            not allow_science_revision
            and before.get("authority_status") == "REJECTED"
            and isinstance(b, int)
            and isinstance(a, int)
            and a > b
        ):
            out.append(_violation("REJECTED_AUTHORITY_BRANCH_REOPENED_WITHOUT_REBASE"))
    if "final_boundary" in old_caps | new_caps:
        b = before.get("final_boundary_start_count")
        a = after.get("final_boundary_start_count")
        _regression(out, b, a, "FINAL_BOUNDARY_START_COUNT_REGRESSED")
        if not allow_final_start:
            _increase(out, b, a, "FINAL_BOUNDARY_STARTED_BEFORE_GUARD_RELEASE")
    return out


def _test_snapshot(facts: dict[str, Any], mode: str = "STANDARD") -> dict[str, Any]:
    snapshot = {
        "schema_id": SCHEMA_ID,
        "profile": "generic",
        "mode": mode,
        "repo": None,
        "facts": _normalize(facts),
    }
    snapshot["snapshot_sha256"] = _digest(snapshot)
    return snapshot


def _reseal_test_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    snapshot.pop("snapshot_sha256", None)
    snapshot["snapshot_sha256"] = _digest(snapshot)
    return snapshot


def _test_codes(before: dict[str, Any], after: dict[str, Any], *, allow_final: bool = False) -> set[str]:
    budget = MODES[after["mode"]]
    return {
        x["code"] for x in compare(
            before, after,
            max_event_delta=budget["events"],
            max_hotfix_delta=budget["mutations"],
            max_expensive_start_delta=budget["expensive"],
            allow_science_revision=False,
            allow_final_start=allow_final,
        )
    }


def _self_test() -> None:
    small0 = _test_snapshot({"project_id": "code", "closure_item_ids": ["B1"], "open_item_ids": ["B1"], "planned_mutation_count": 1, "completed_mutation_count": 0, "validation_rank": 0}, "LIGHT")
    small1 = _test_snapshot({"project_id": "code", "closure_item_ids": ["B1"], "open_item_ids": [], "planned_mutation_count": 1, "completed_mutation_count": 1, "validation_rank": 2}, "LIGHT")
    assert not _test_codes(small0, small1)
    expanded = _test_snapshot({"project_id": "code", "closure_item_ids": ["B1", "B2"], "open_item_ids": ["B2"], "planned_mutation_count": 2, "completed_mutation_count": 1, "validation_rank": 2}, "LIGHT")
    assert {"CLOSURE_ITEM_SET_EXPANDED", "PLANNED_MUTATION_COUNT_INCREASED"} <= _test_codes(small1, expanded)
    migration0 = _test_snapshot({"project_id": "migration", "change_generation": "E1", "validation_rank": 1})
    migration1 = _test_snapshot({"project_id": "migration", "change_generation": "E1", "validation_rank": 3})
    assert not _test_codes(migration0, migration1)
    science0 = _test_snapshot({"project_id": "science", "authority_status": "REJECTED", "authority_revision_count": 1})
    science1 = _test_snapshot({"project_id": "science", "authority_status": "OTHER", "authority_revision_count": 2})
    assert "REJECTED_AUTHORITY_BRANCH_REOPENED_WITHOUT_REBASE" in _test_codes(science0, science1)
    release0 = _test_snapshot({"project_id": "release", "final_boundary_start_count": 0})
    release1 = _test_snapshot({"project_id": "release", "final_boundary_start_count": 1})
    assert "FINAL_BOUNDARY_STARTED_BEFORE_GUARD_RELEASE" in _test_codes(release0, release1)
    assert not _test_codes(release0, release1, allow_final=True)
    delegated0 = _test_snapshot({
        "project_id": "delegated", "delegated_task_ids": ["D1"],
        "subagent_spawn_count": 0, "active_subagent_count": 0,
        "active_subagent_mutator_count": 0, "active_subagent_expensive_run_count": 0,
        "recursive_delegation_count": 0,
    })
    delegated1 = _test_snapshot({
        "project_id": "delegated", "delegated_task_ids": ["D1"],
        "subagent_spawn_count": 1, "active_subagent_count": 1,
        "active_subagent_mutator_count": 0, "active_subagent_expensive_run_count": 0,
        "recursive_delegation_count": 0,
    })
    assert not _test_codes(delegated0, delegated1)
    delegated_bad = _test_snapshot({
        "project_id": "delegated", "delegated_task_ids": ["D1", "D2", "D3"],
        "subagent_spawn_count": 3, "active_subagent_count": 3,
        "active_subagent_mutator_count": 1, "active_subagent_expensive_run_count": 1,
        "recursive_delegation_count": 1,
    })
    assert {
        "DELEGATED_TASK_SET_EXPANDED", "DELEGATED_TASK_DENOMINATOR_INCREASED",
        "ACTIVE_SUBAGENT_LIMIT_EXCEEDED", "DELEGATED_MUTATION_PROHIBITED",
        "DELEGATED_EXPENSIVE_RUN_PROHIBITED", "RECURSIVE_DELEGATION_PROHIBITED",
    } <= _test_codes(delegated1, delegated_bad)
    rescue0 = _test_snapshot({
        "project_id": "rescue", "delegated_task_ids": ["D1", "D2"],
        "active_subagent_count": 0, "subagent_spawn_count": 0,
    }, "RESCUE")
    rescue2 = _test_snapshot({
        "project_id": "rescue", "delegated_task_ids": ["D1", "D2"],
        "active_subagent_count": 2, "subagent_spawn_count": 2,
    }, "RESCUE")
    assert "ACTIVE_SUBAGENT_LIMIT_EXCEEDED" in _test_codes(rescue0, rescue2)
    review0 = _test_snapshot({
        "project_id": "review", "delegated_task_ids": ["D1", "D2"],
        "active_subagent_count": 0, "subagent_spawn_count": 0,
        "independent_authority_review_required": True,
    }, "RESCUE")
    review2 = _test_snapshot({
        "project_id": "review", "delegated_task_ids": ["D1", "D2"],
        "active_subagent_count": 2, "subagent_spawn_count": 2,
        "independent_authority_review_required": True,
    }, "RESCUE")
    assert "ACTIVE_SUBAGENT_LIMIT_EXCEEDED" not in _test_codes(review0, review2)
    regressed0 = _test_snapshot({
        "project_id": "monotonic", "completed_mutation_count": 2,
        "control_event_count": 4, "expensive_start_count": 3,
        "final_boundary_start_count": 1, "authority_revision_count": 2,
        "subagent_spawn_count": 1, "delegated_task_count": 1,
    })
    regressed1 = _test_snapshot({
        "project_id": "monotonic", "completed_mutation_count": 1,
        "control_event_count": 3, "expensive_start_count": 2,
        "final_boundary_start_count": 0, "authority_revision_count": 1,
        "subagent_spawn_count": 0, "delegated_task_count": 1,
    })
    assert {
        "COMPLETED_MUTATION_COUNT_REGRESSED", "CONTROL_EVENT_COUNT_REGRESSED",
        "EXPENSIVE_START_COUNT_REGRESSED", "FINAL_BOUNDARY_START_COUNT_REGRESSED",
        "AUTHORITY_REVISION_COUNT_REGRESSED", "SUBAGENT_SPAWN_COUNT_REGRESSED",
    } <= _test_codes(regressed0, regressed1, allow_final=True)
    try:
        _normalize({"closure_item_ids": ["B1"], "open_item_ids": ["B2"]})
    except ValueError:
        pass
    else:
        raise AssertionError("open_item_ids accepted outside closure_item_ids")
    git0 = _test_snapshot({"project_id": "git-drift"})
    git0["repo"] = {
        "repo_token": "repo", "head": "H1", "tracked_changed_count": 0,
        "untracked_count": 0, "tracked_path_tokens": [], "untracked_path_tokens": [],
        "changed_path_tokens": [], "allowed_path_tokens": ["P1"],
        "allowed_path_count": 1, "changed_paths_sha256": _digest([[], []]),
    }
    _reseal_test_snapshot(git0)
    git1 = {**git0, "repo": {**git0["repo"], "head": "H2"}}
    _reseal_test_snapshot(git1)
    assert "WORKTREE_HEAD_CHANGED" in _test_codes(git0, git1)
    planned = {**git0, "repo": {**git0["repo"], "changed_path_tokens": ["P1"]}}
    _reseal_test_snapshot(planned)
    assert "FROZEN_PATH_SET_EXPANDED" not in _test_codes(git0, planned)
    outside = {**git0, "repo": {**git0["repo"], "changed_path_tokens": ["P2"]}}
    _reseal_test_snapshot(outside)
    assert "FROZEN_PATH_SET_EXPANDED" in _test_codes(git0, outside)
    tampered = dict(git0)
    tampered["mode"] = "LIGHT"
    assert "BASELINE_SNAPSHOT_INVALID" in _test_codes(tampered, git1)
    try:
        _strict_json_text('{"a": 1, "a": 2}', "test JSON")
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate JSON key accepted")
    print("closure_guard_self_test=PASS scenarios=13")


def _add_capture_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", type=Path)
    parser.add_argument(
        "--allowed-paths-from",
        help="newline-delimited planned repository paths; freeze only when taking a baseline",
    )
    parser.add_argument("--run-state", type=Path)
    parser.add_argument("--facts")
    parser.add_argument("--profile", choices=("auto", "git", "generic", "v21"), default="auto")
    parser.add_argument("--mode", choices=tuple(MODES), default="STANDARD")


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    _add_capture_args(commands.add_parser("snapshot"))
    check = commands.add_parser("compare")
    check.add_argument("--baseline", required=True)
    _add_capture_args(check)
    check.add_argument(
        "--max-control-event-delta", "--max-event-delta", dest="max_event_delta", type=int
    )
    check.add_argument(
        "--max-mutation-delta", "--max-hotfix-delta", dest="max_hotfix_delta", type=int
    )
    check.add_argument("--max-expensive-start-delta", type=int)
    check.add_argument(
        "--allow-authority-revision", "--allow-science-revision",
        dest="allow_science_revision", action="store_true",
    )
    check.add_argument("--allow-final-start", action="store_true")
    commands.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        _self_test()
        return 0
    if args.command == "snapshot":
        current = capture(
            args.repo,
            args.run_state,
            args.facts,
            args.profile,
            args.mode,
            allowed_paths_from=args.allowed_paths_from,
        )
        print(json.dumps(current, indent=2, sort_keys=True))
        return 0
    baseline = _load(args.baseline)
    inherited_allowed = None
    if args.allowed_paths_from is None and isinstance(baseline.get("repo"), dict):
        inherited_allowed = baseline["repo"].get("allowed_path_tokens")
    current = capture(
        args.repo,
        args.run_state,
        args.facts,
        args.profile,
        args.mode,
        allowed_paths_from=args.allowed_paths_from,
        inherited_allowed_path_tokens=inherited_allowed,
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
        baseline, current,
        max_event_delta=budgets[0],
        max_hotfix_delta=budgets[1],
        max_expensive_start_delta=budgets[2],
        allow_science_revision=args.allow_science_revision,
        allow_final_start=args.allow_final_start,
    )
    scope_codes = {
        "BASELINE_SCHEMA_INCOMPATIBLE", "BASELINE_SNAPSHOT_INVALID",
        "CAPABILITY_SET_EXPANDED", "CAPABILITY_SET_REDUCED",
        "CLOSURE_ITEM_DENOMINATOR_INCREASED",
        "CLOSURE_ITEM_SET_EXPANDED", "FROZEN_PATH_SET_EXPANDED", "ALLOWED_PATH_SET_CHANGED",
        "DELEGATED_TASK_DENOMINATOR_INCREASED", "DELEGATED_TASK_SET_EXPANDED",
        "WORKTREE_HEAD_CHANGED",
        "GUARD_MODE_CHANGED", "GUARD_PROFILE_CHANGED", "PROJECT_CHANGED", "PROJECT_IDENTITY_SOURCE_CHANGED",
    }
    active_subagent_limit = defaults["subagents"]
    if (
        args.mode == "RESCUE"
        and baseline.get("facts", {}).get("independent_authority_review_required") is True
    ):
        active_subagent_limit = 2
    report = {
        "status": "BLOCKED" if violations else "PASS",
        "recommended_outcome": "REBASE_REQUIRED" if any(x["code"] in scope_codes for x in violations) else "BLOCKED" if violations else "CONTINUE",
        "mode": args.mode,
        "budgets": {
            "control_events": budgets[0],
            "mutations": budgets[1],
            "expensive_starts": budgets[2],
            "active_subagents": active_subagent_limit,
        },
        "violation_count": len(violations),
        "violations": violations,
        "current_snapshot_sha256": current["snapshot_sha256"],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2 if violations else 0


def main() -> int:
    try:
        return _main()
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
