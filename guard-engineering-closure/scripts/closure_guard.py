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


SCHEMA_ID = "ENGINEERING_CLOSURE_GUARD_SNAPSHOT_V5"
MODES = {
    "LIGHT": {"events": 0, "mutations": 1, "expensive": 1, "subagents": 0},
    "STANDARD": {"events": 4, "mutations": 1, "expensive": 1, "subagents": 2},
    "RESCUE": {"events": 2, "mutations": 1, "expensive": 1, "subagents": 1},
}
LIST_FIELDS = (
    "closure_item_ids", "open_item_ids", "blocker_ids", "delegated_task_ids",
    "changed_object_ids", "allowed_object_ids", "waiver_ids",
    "capabilities",
)
INT_FIELDS = (
    "closure_item_count",
    "open_item_count",
    "closed_item_count",
    "planned_mutation_count",
    "completed_mutation_count",
    "remaining_mutation_count",
    "validation_rank",
    "validation_discovered_count",
    "validation_executed_count",
    "validation_passed_count",
    "validation_failed_count",
    "validation_error_count",
    "validation_skipped_count",
    "validation_xfail_count",
    "validation_xpass_count",
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
    "run_state_terminal_count",
    "duplicate_start_count",
    "old_transaction_resume_count",
)
TEXT_FIELDS = (
    "project_id",
    "campaign_id",
    "change_generation",
    "validation_level",
    "validation_evidence_identity",
    "validation_outer_terminal_status",
    "authority_status",
    "authority_revision_identity",
    "protected_content_identity",
    "writer_proof_identity",
    "boundary_smoke_identity",
    "boundary_smoke_status",
    "run_state_head_identity",
    "waiver_scope_identity",
    "rescue_deadline_at",
)
BOOL_FIELDS = (
    "independent_authority_review_required",
    "writer_free",
    "run_state_replay_verified",
    "run_state_projection_matches_replay",
)
FACT_FIELDS = set(LIST_FIELDS + INT_FIELDS + TEXT_FIELDS + BOOL_FIELDS)
CAPABILITIES = {
    "authority",
    "boundary_smoke",
    "blockers",
    "campaign_lineage",
    "closure_items",
    "control_events",
    "delegation",
    "expensive_operations",
    "final_boundary",
    "mutations",
    "mutators",
    "object_scope",
    "run_state",
    "validation_ladder",
    "validation_execution",
    "vcs",
    "waivers",
    "writer_proof",
}
AUTHORITY_STATUSES = {
    "NOT_APPLICABLE",
    "UNRESOLVED",
    "PROPOSED",
    "APPROVED",
    "ACTIVATED",
    "REJECTED",
}
BOUNDARY_SMOKE_STATUSES = {"NOT_APPLICABLE", "PENDING", "PASS", "BLOCKED", "FAILED_TYPED"}
TERMINAL_STATUSES = {"NOT_APPLICABLE", "COMPLETED", "BLOCKED", "FAILED_TYPED", "INCOMPLETE"}
MODE_REQUIRED_CAPABILITIES = {
    "LIGHT": set(),
    "STANDARD": {"closure_items", "mutations", "validation_ladder", "mutators"},
    "RESCUE": {
        "closure_items",
        "mutations",
        "validation_ladder",
        "mutators",
        "campaign_lineage",
        "expensive_operations",
        "writer_proof",
        "boundary_smoke",
    },
}
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
    ids = {
        field: _tokens(
            "object" if field in {"changed_object_ids", "allowed_object_ids"} else field,
            values,
        )
        for field, values in raw_ids.items()
    }
    counts = {field: _nonnegative(raw.get(field), field) for field in INT_FIELDS}
    for id_field, count_field in (
        ("closure_item_ids", "closure_item_count"),
        ("open_item_ids", "open_item_count"),
        ("delegated_task_ids", "delegated_task_count"),
    ):
        if id_field in raw:
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
    elif isinstance(closure_count, int) and isinstance(open_count, int) and closed_count is None:
        counts["closed_item_count"] = closure_count - open_count
        if counts["closed_item_count"] < 0:
            raise ValueError("open_item_count exceeds closure_item_count")

    planned = counts["planned_mutation_count"]
    completed = counts["completed_mutation_count"]
    remaining = counts["remaining_mutation_count"]
    if isinstance(planned, int) and isinstance(completed, int):
        if completed > planned:
            raise ValueError("completed_mutation_count exceeds planned_mutation_count")
        expected_remaining = planned - completed
        if remaining not in (None, expected_remaining):
            raise ValueError("remaining_mutation_count disagrees with planned/completed counts")
        counts["remaining_mutation_count"] = expected_remaining

    validation_fields = (
        "validation_discovered_count",
        "validation_executed_count",
        "validation_passed_count",
        "validation_failed_count",
        "validation_error_count",
        "validation_skipped_count",
        "validation_xfail_count",
        "validation_xpass_count",
    )
    if any(counts[field] is not None for field in validation_fields):
        if any(counts[field] is None for field in validation_fields):
            raise ValueError("validation execution counts must be supplied as one exact set")
        discovered, executed, passed, failed, errors, skipped, xfail, xpass = (
            counts[field] for field in validation_fields
        )
        if discovered != executed + skipped:
            raise ValueError("validation_discovered_count must equal executed plus skipped")
        if executed != passed + failed + errors + xfail + xpass:
            raise ValueError("validation_executed_count does not match result counts")
        if raw.get("validation_evidence_identity") is None:
            raise ValueError("validation execution counts require validation_evidence_identity")
        if raw.get("validation_outer_terminal_status") is None:
            raise ValueError("validation execution counts require validation_outer_terminal_status")

    authority_status = raw.get("authority_status")
    if authority_status is not None and authority_status not in AUTHORITY_STATUSES:
        raise ValueError(f"authority_status is invalid: {authority_status}")
    smoke_status = raw.get("boundary_smoke_status")
    if smoke_status is not None and smoke_status not in BOUNDARY_SMOKE_STATUSES:
        raise ValueError(f"boundary_smoke_status is invalid: {smoke_status}")
    terminal_status = raw.get("validation_outer_terminal_status")
    if terminal_status is not None and terminal_status not in TERMINAL_STATUSES:
        raise ValueError(f"validation_outer_terminal_status is invalid: {terminal_status}")
    if smoke_status == "PASS" and raw.get("boundary_smoke_identity") is None:
        raise ValueError("PASS boundary smoke requires boundary_smoke_identity")
    if raw.get("writer_free") is not None and raw.get("writer_proof_identity") is None:
        raise ValueError("writer_free requires writer_proof_identity")
    if ids["waiver_ids"] and raw.get("waiver_scope_identity") is None:
        raise ValueError("waiver_ids require waiver_scope_identity")

    run_state_values = (
        raw.get("run_state_head_identity"),
        counts["run_state_terminal_count"],
        raw.get("run_state_replay_verified"),
        raw.get("run_state_projection_matches_replay"),
        counts["duplicate_start_count"],
        counts["old_transaction_resume_count"],
    )
    if any(value is not None for value in run_state_values) and any(
        value is None for value in run_state_values
    ):
        raise ValueError("run-state integrity facts must be supplied as one exact set")

    capabilities = set(_strings(raw.get("capabilities"), "capabilities"))
    inference = {
        "campaign_lineage": raw.get("campaign_id") is not None
        or raw.get("rescue_deadline_at") is not None,
        "closure_items": counts["closure_item_count"] is not None
        or counts["open_item_count"] is not None
        or counts["closed_item_count"] is not None,
        "blockers": bool(ids["blocker_ids"]),
        "mutations": counts["planned_mutation_count"] is not None
        or counts["completed_mutation_count"] is not None
        or counts["remaining_mutation_count"] is not None,
        "validation_ladder": counts["validation_rank"] is not None,
        "validation_execution": any(counts[field] is not None for field in validation_fields)
        or raw.get("validation_evidence_identity") is not None
        or raw.get("validation_outer_terminal_status") is not None,
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
        or raw.get("authority_revision_identity") is not None
        or raw.get("independent_authority_review_required") is not None,
        "object_scope": bool(ids["changed_object_ids"])
        or bool(ids["allowed_object_ids"])
        or raw.get("protected_content_identity") is not None,
        "writer_proof": raw.get("writer_free") is not None
        or raw.get("writer_proof_identity") is not None,
        "boundary_smoke": smoke_status is not None
        or raw.get("boundary_smoke_identity") is not None,
        "run_state": any(value is not None for value in run_state_values),
        "waivers": bool(ids["waiver_ids"])
        or raw.get("waiver_scope_identity") is not None,
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
    if "object_scope" in capabilities and raw.get("protected_content_identity") is None:
        raise ValueError("object_scope requires protected_content_identity")
    if "writer_proof" in capabilities and raw.get("writer_free") is None:
        raise ValueError("writer_proof requires writer_free")
    if "boundary_smoke" in capabilities and smoke_status is None:
        raise ValueError("boundary_smoke requires boundary_smoke_status")
    if "authority" in capabilities and authority_status is None:
        raise ValueError("authority capability requires authority_status")
    if authority_status in {"APPROVED", "ACTIVATED", "REJECTED"} and raw.get(
        "authority_revision_identity"
    ) is None:
        raise ValueError(f"{authority_status} authority requires authority_revision_identity")
    project = raw.get("project_id")
    campaign = raw.get("campaign_id") or project
    return {
        "project_token": _tokens("project", [project])[0] if project else None,
        "campaign_token": _tokens("campaign", [campaign])[0] if campaign else None,
        "change_generation": raw.get("change_generation"),
        **ids,
        **counts,
        "blocker_count": len(ids["blocker_ids"]),
        "validation_level": raw.get("validation_level"),
        "validation_evidence_identity": raw.get("validation_evidence_identity"),
        "validation_outer_terminal_status": terminal_status,
        "authority_status": authority_status,
        "authority_revision_identity": raw.get("authority_revision_identity"),
        "protected_content_identity": raw.get("protected_content_identity"),
        "writer_proof_identity": raw.get("writer_proof_identity"),
        "boundary_smoke_identity": raw.get("boundary_smoke_identity"),
        "boundary_smoke_status": smoke_status,
        "run_state_head_identity": raw.get("run_state_head_identity"),
        "waiver_scope_identity": raw.get("waiver_scope_identity"),
        "rescue_deadline_at": raw.get("rescue_deadline_at"),
        "independent_authority_review_required": raw.get(
            "independent_authority_review_required", False
        ),
        "writer_free": raw.get("writer_free"),
        "run_state_replay_verified": raw.get("run_state_replay_verified"),
        "run_state_projection_matches_replay": raw.get(
            "run_state_projection_matches_replay"
        ),
        "capabilities": sorted(capabilities),
    }


def _load(value: str) -> dict[str, Any]:
    text = sys.stdin.read() if value == "-" else Path(value).read_text(encoding="utf-8")
    return _strict_json_text(text, "guard JSON input")


def _validate_snapshot(snapshot: Any, label: str) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        raise ValueError(f"{label} must be a JSON object")
    required = {"schema_id", "profile", "mode", "repo", "facts", "lineage", "snapshot_sha256"}
    if set(snapshot) != required:
        raise ValueError(f"{label} fields do not match schema V5")
    if snapshot.get("schema_id") != SCHEMA_ID:
        raise ValueError(f"{label} schema is incompatible; capture a fresh V5 baseline")
    if snapshot.get("profile") not in {"git", "generic"}:
        raise ValueError(f"{label} has an invalid profile")
    if snapshot.get("mode") not in MODES:
        raise ValueError(f"{label} has an invalid mode")
    facts = snapshot.get("facts")
    fact_fields = (
        set(LIST_FIELDS[:-1])
        | set(INT_FIELDS)
        | {
            "project_token", "campaign_token", "change_generation", "blocker_count",
            "validation_level", "validation_evidence_identity",
            "validation_outer_terminal_status", "authority_status",
            "authority_revision_identity", "protected_content_identity",
            "writer_proof_identity", "boundary_smoke_identity", "boundary_smoke_status",
            "run_state_head_identity", "waiver_scope_identity", "rescue_deadline_at",
            "independent_authority_review_required", "writer_free",
            "run_state_replay_verified", "run_state_projection_matches_replay",
            "capabilities",
        }
    )
    if not isinstance(facts, dict) or set(facts) != fact_fields:
        raise ValueError(f"{label} facts are malformed")
    capabilities = facts.get("capabilities")
    if (
        not isinstance(capabilities, list)
        or not all(isinstance(value, str) for value in capabilities)
        or not set(capabilities) <= CAPABILITIES
        or capabilities != sorted(set(capabilities))
    ):
        raise ValueError(f"{label} capabilities are malformed")
    for field in LIST_FIELDS[:-1]:
        values = facts.get(field)
        if (
            not isinstance(values, list)
            or values != sorted(set(values))
            or any(
                len(value) != 64 or any(char not in "0123456789abcdef" for char in value)
                for value in values
            )
        ):
            raise ValueError(f"{label} {field} is malformed")
    for field in INT_FIELDS + ("blocker_count",):
        value = facts.get(field)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ValueError(f"{label} {field} is malformed")
    if not isinstance(facts.get("independent_authority_review_required"), bool):
        raise ValueError(f"{label} authority-review fact is malformed")
    for field in ("writer_free", "run_state_replay_verified", "run_state_projection_matches_replay"):
        if facts.get(field) is not None and not isinstance(facts.get(field), bool):
            raise ValueError(f"{label} {field} is malformed")
    for field in (
        "change_generation", "validation_level", "validation_evidence_identity",
        "validation_outer_terminal_status", "authority_status",
        "authority_revision_identity", "protected_content_identity",
        "writer_proof_identity", "boundary_smoke_identity", "boundary_smoke_status",
        "run_state_head_identity", "waiver_scope_identity", "rescue_deadline_at",
    ):
        value = facts.get(field)
        if value is not None and (not isinstance(value, str) or not value):
            raise ValueError(f"{label} {field} is malformed")
    for field in ("project_token", "campaign_token"):
        value = facts.get(field)
        if value is not None and (
            not isinstance(value, str)
            or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)
        ):
            raise ValueError(f"{label} {field} is malformed")
    if facts.get("authority_status") not in AUTHORITY_STATUSES | {None}:
        raise ValueError(f"{label} authority status is invalid")
    if facts.get("boundary_smoke_status") not in BOUNDARY_SMOKE_STATUSES | {None}:
        raise ValueError(f"{label} boundary smoke status is invalid")
    if facts.get("validation_outer_terminal_status") not in TERMINAL_STATUSES | {None}:
        raise ValueError(f"{label} validation terminal status is invalid")
    closure_count = facts.get("closure_item_count")
    open_count = facts.get("open_item_count")
    closed_count = facts.get("closed_item_count")
    if all(isinstance(value, int) for value in (closure_count, open_count, closed_count)):
        if closure_count != open_count + closed_count:
            raise ValueError(f"{label} closure counts are inconsistent")
    planned = facts.get("planned_mutation_count")
    completed = facts.get("completed_mutation_count")
    remaining = facts.get("remaining_mutation_count")
    if all(isinstance(value, int) for value in (planned, completed, remaining)):
        if completed > planned or remaining != planned - completed:
            raise ValueError(f"{label} mutation counts are inconsistent")
    validation_fields = (
        "validation_discovered_count", "validation_executed_count",
        "validation_passed_count", "validation_failed_count",
        "validation_error_count", "validation_skipped_count",
        "validation_xfail_count", "validation_xpass_count",
    )
    validation_values = [facts.get(field) for field in validation_fields]
    if any(value is not None for value in validation_values):
        if any(value is None for value in validation_values):
            raise ValueError(f"{label} validation counts are incomplete")
        discovered, executed, passed, failed, errors, skipped, xfail, xpass = validation_values
        if discovered != executed + skipped or executed != passed + failed + errors + xfail + xpass:
            raise ValueError(f"{label} validation counts are inconsistent")
        if not facts.get("validation_evidence_identity") or not facts.get(
            "validation_outer_terminal_status"
        ):
            raise ValueError(f"{label} validation evidence is incomplete")
    if facts.get("blocker_count") != len(facts.get("blocker_ids", [])):
        raise ValueError(f"{label} blocker count is inconsistent")
    for id_field, count_field in (
        ("closure_item_ids", "closure_item_count"),
        ("open_item_ids", "open_item_count"),
        ("delegated_task_ids", "delegated_task_count"),
    ):
        if facts[id_field] and facts.get(count_field) != len(facts[id_field]):
            raise ValueError(f"{label} {count_field} disagrees with {id_field}")
    if facts.get("boundary_smoke_status") == "PASS" and not facts.get(
        "boundary_smoke_identity"
    ):
        raise ValueError(f"{label} PASS boundary smoke lacks identity")
    if "object_scope" in capabilities and not facts.get("protected_content_identity"):
        raise ValueError(f"{label} object scope lacks protected-content identity")
    if "writer_proof" in capabilities and (
        facts.get("writer_free") is None or not facts.get("writer_proof_identity")
    ):
        raise ValueError(f"{label} writer proof is incomplete")
    if "boundary_smoke" in capabilities and facts.get("boundary_smoke_status") is None:
        raise ValueError(f"{label} boundary-smoke capability lacks status")
    if "authority" in capabilities and facts.get("authority_status") is None:
        raise ValueError(f"{label} authority capability lacks status")
    if facts.get("authority_status") in {"APPROVED", "ACTIVATED", "REJECTED"} and not facts.get(
        "authority_revision_identity"
    ):
        raise ValueError(f"{label} governed authority lacks revision identity")
    if facts.get("waiver_ids") and not facts.get("waiver_scope_identity"):
        raise ValueError(f"{label} waiver scope is missing")
    run_state_values = (
        facts.get("run_state_head_identity"), facts.get("run_state_terminal_count"),
        facts.get("run_state_replay_verified"),
        facts.get("run_state_projection_matches_replay"),
        facts.get("duplicate_start_count"), facts.get("old_transaction_resume_count"),
    )
    if any(value is not None for value in run_state_values) and any(
        value is None for value in run_state_values
    ):
        raise ValueError(f"{label} run-state facts are incomplete")
    inferred_capabilities = {
        name
        for name, present in {
            "closure_items": any(
                facts.get(field) is not None
                for field in ("closure_item_count", "open_item_count", "closed_item_count")
            ),
            "blockers": bool(facts.get("blocker_ids")),
            "mutations": any(
                facts.get(field) is not None
                for field in (
                    "planned_mutation_count", "completed_mutation_count",
                    "remaining_mutation_count",
                )
            ),
            "validation_ladder": facts.get("validation_rank") is not None,
            "validation_execution": any(value is not None for value in validation_values)
            or facts.get("validation_evidence_identity") is not None
            or facts.get("validation_outer_terminal_status") is not None,
            "control_events": facts.get("control_event_count") is not None,
            "delegation": bool(facts.get("delegated_task_ids"))
            or any(
                facts.get(field) is not None
                for field in (
                    "delegated_task_count", "subagent_spawn_count", "active_subagent_count",
                    "active_subagent_mutator_count", "active_subagent_expensive_run_count",
                    "recursive_delegation_count",
                )
            ),
            "mutators": facts.get("active_mutator_count") is not None,
            "expensive_operations": any(
                facts.get(field) is not None
                for field in ("active_expensive_run_count", "expensive_start_count")
            ),
            "final_boundary": facts.get("final_boundary_start_count") is not None,
            "authority": facts.get("authority_status") is not None
            or facts.get("authority_revision_count") is not None
            or facts.get("authority_revision_identity") is not None
            or facts.get("independent_authority_review_required") is not False,
            "object_scope": bool(facts.get("changed_object_ids"))
            or bool(facts.get("allowed_object_ids"))
            or facts.get("protected_content_identity") is not None,
            "writer_proof": facts.get("writer_free") is not None
            or facts.get("writer_proof_identity") is not None,
            "boundary_smoke": facts.get("boundary_smoke_status") is not None
            or facts.get("boundary_smoke_identity") is not None,
            "run_state": any(value is not None for value in run_state_values),
            "waivers": bool(facts.get("waiver_ids"))
            or facts.get("waiver_scope_identity") is not None,
        }.items()
        if present
    }
    if not inferred_capabilities <= set(capabilities):
        raise ValueError(
            f"{label} hides inferred capabilities: "
            f"{sorted(inferred_capabilities - set(capabilities))}"
        )
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
            values = repo.get(field)
            if (
                not isinstance(values, list)
                or values != sorted(set(values))
                or any(
                    len(value) != 64
                    or any(char not in "0123456789abcdef" for char in value)
                    for value in values
                )
            ):
                raise ValueError(f"{label} repository token list is malformed")
        for field in ("repo_token", "changed_paths_sha256"):
            value = repo.get(field)
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(char not in "0123456789abcdef" for char in value)
            ):
                raise ValueError(f"{label} repository identity is malformed")
        for field in ("tracked_changed_count", "untracked_count", "allowed_path_count"):
            value = repo.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{label} repository count is malformed")
        if repo["tracked_changed_count"] != len(repo["tracked_path_tokens"]):
            raise ValueError(f"{label} tracked-path count is inconsistent")
        if repo["untracked_count"] != len(repo["untracked_path_tokens"]):
            raise ValueError(f"{label} untracked-path count is inconsistent")
        if repo["allowed_path_count"] != len(repo["allowed_path_tokens"]):
            raise ValueError(f"{label} allowed-path count is inconsistent")
    lineage = snapshot.get("lineage")
    if not isinstance(lineage, dict) or set(lineage) != {
        "campaign_token", "parent_snapshot_sha256", "accepted_rebaseline_count"
    }:
        raise ValueError(f"{label} lineage is malformed")
    if not isinstance(lineage.get("campaign_token"), str) or not lineage["campaign_token"]:
        raise ValueError(f"{label} campaign lineage is missing")
    parent = lineage.get("parent_snapshot_sha256")
    if parent is not None and (not isinstance(parent, str) or len(parent) != 64):
        raise ValueError(f"{label} predecessor identity is malformed")
    rebaseline_count = lineage.get("accepted_rebaseline_count")
    if isinstance(rebaseline_count, bool) or not isinstance(rebaseline_count, int) or rebaseline_count < 0:
        raise ValueError(f"{label} rebaseline count is malformed")
    if facts.get("campaign_token") not in (None, lineage["campaign_token"]):
        raise ValueError(f"{label} campaign fact disagrees with lineage")
    missing = MODE_REQUIRED_CAPABILITIES[snapshot["mode"]] - set(capabilities)
    if snapshot["profile"] == "generic" and missing:
        raise ValueError(f"{label} generic {snapshot['mode']} facts miss capabilities: {sorted(missing)}")
    expected = snapshot.get("snapshot_sha256")
    payload = {key: value for key, value in snapshot.items() if key != "snapshot_sha256"}
    if not isinstance(expected, str) or expected != _digest(payload):
        raise ValueError(f"{label} snapshot hash mismatch")
    return snapshot


def capture(
    repo: Path | None,
    facts_path: str | None,
    profile: str,
    mode: str,
    allowed_paths_from: str | None = None,
    inherited_allowed_path_tokens: list[str] | None = None,
    inherited_lineage: dict[str, Any] | None = None,
    accepted_predecessor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = "generic" if profile == "auto" and facts_path else "git" if profile == "auto" else profile
    if profile == "generic" and not facts_path:
        raise ValueError("generic profile requires --facts")
    if profile == "git" and facts_path:
        raise ValueError("git profile consumes only --repo")
    if not any((repo, facts_path)):
        raise ValueError("provide --repo or --facts")
    facts = (
        _normalize(_load(facts_path)) if profile == "generic" else
        _normalize({"capabilities": ["vcs"]})
    )
    repo_facts = _git(
        repo,
        allowed_paths_from=allowed_paths_from,
        inherited_allowed_path_tokens=inherited_allowed_path_tokens,
    ) if repo else None
    campaign_token = (
        facts.get("campaign_token")
        or facts.get("project_token")
        or (repo_facts or {}).get("repo_token")
    )
    if not isinstance(campaign_token, str) or not campaign_token:
        raise ValueError("capture requires a project, campaign, or repository identity")
    if inherited_lineage is not None and accepted_predecessor is not None:
        raise ValueError("capture cannot inherit and rebaseline lineage simultaneously")
    if inherited_lineage is not None:
        lineage = dict(inherited_lineage)
        if lineage.get("campaign_token") != campaign_token:
            raise ValueError("current facts disagree with inherited campaign lineage")
    elif accepted_predecessor is not None:
        _validate_snapshot(accepted_predecessor, "predecessor snapshot")
        predecessor_lineage = accepted_predecessor["lineage"]
        if predecessor_lineage.get("campaign_token") != campaign_token:
            raise ValueError("accepted rebaseline cannot change campaign identity")
        if predecessor_lineage.get("accepted_rebaseline_count") >= 1:
            raise ValueError("accepted rebaseline limit exceeded for this campaign")
        lineage = {
            "campaign_token": campaign_token,
            "parent_snapshot_sha256": accepted_predecessor["snapshot_sha256"],
            "accepted_rebaseline_count": predecessor_lineage["accepted_rebaseline_count"] + 1,
        }
    else:
        lineage = {
            "campaign_token": campaign_token,
            "parent_snapshot_sha256": None,
            "accepted_rebaseline_count": 0,
        }
    snapshot = {
        "schema_id": SCHEMA_ID,
        "profile": profile,
        "mode": mode,
        "repo": repo_facts,
        "facts": facts,
        "lineage": lineage,
    }
    snapshot["snapshot_sha256"] = _digest(snapshot)
    _validate_snapshot(snapshot, "captured snapshot")
    return snapshot


def _rebaseline_violations(
    predecessor: dict[str, Any], successor: dict[str, Any]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    before, after = predecessor["facts"], successor["facts"]
    if predecessor.get("profile") != successor.get("profile"):
        out.append(_violation("REBASE_PROFILE_CHANGED"))
    if before.get("project_token") != after.get("project_token"):
        out.append(_violation("REBASE_PROJECT_CHANGED"))
    before_repo, after_repo = predecessor.get("repo"), successor.get("repo")
    if isinstance(before_repo, dict) != isinstance(after_repo, dict):
        out.append(_violation("REBASE_PROJECT_IDENTITY_SOURCE_CHANGED"))
    elif isinstance(before_repo, dict) and before_repo.get("repo_token") != after_repo.get("repo_token"):
        out.append(_violation("REBASE_REPOSITORY_CHANGED"))
    if not set(before.get("closure_item_ids", [])) <= set(after.get("closure_item_ids", [])):
        out.append(_violation("REBASE_ERASED_CLOSURE_ITEMS"))
    if isinstance(before_repo, dict) and not set(before_repo.get("allowed_path_tokens", [])) <= set(
        after_repo.get("allowed_path_tokens", [])
    ):
        out.append(_violation("REBASE_ERASED_ALLOWED_PATHS"))
    if not set(before.get("allowed_object_ids", [])) <= set(after.get("allowed_object_ids", [])):
        out.append(_violation("REBASE_ERASED_ALLOWED_OBJECTS"))
    for field, code in (
        ("completed_mutation_count", "REBASE_RESET_COMPLETED_MUTATIONS"),
        ("control_event_count", "REBASE_RESET_CONTROL_EVENTS"),
        ("expensive_start_count", "REBASE_RESET_EXPENSIVE_STARTS"),
        ("subagent_spawn_count", "REBASE_RESET_SUBAGENT_STARTS"),
        ("final_boundary_start_count", "REBASE_RESET_FINAL_STARTS"),
        ("authority_revision_count", "REBASE_RESET_AUTHORITY_REVISIONS"),
        ("run_state_terminal_count", "REBASE_RESET_TERMINALS"),
        ("duplicate_start_count", "REBASE_RESET_DUPLICATE_STARTS"),
        ("old_transaction_resume_count", "REBASE_RESET_OLD_RESUMES"),
    ):
        _regression(out, before.get(field), after.get(field), code)
    deadline = before.get("rescue_deadline_at")
    if deadline is not None and after.get("rescue_deadline_at") != deadline:
        out.append(_violation("REBASE_CHANGED_RESCUE_DEADLINE"))
    return out


def _violation(code: str, **details: Any) -> dict[str, Any]:
    return {"code": code, **details}


def _increase(out: list[dict[str, Any]], before: Any, after: Any, code: str) -> None:
    if isinstance(before, int) and isinstance(after, int) and after > before:
        out.append(_violation(code, before=before, after=after))


def _regression(out: list[dict[str, Any]], before: Any, after: Any, code: str) -> None:
    if isinstance(before, int) and isinstance(after, int) and after < before:
        out.append(_violation(code, before=before, after=after))


def _validation_clean(facts: dict[str, Any]) -> bool:
    return (
        isinstance(facts.get("validation_executed_count"), int)
        and facts["validation_executed_count"] > 0
        and facts.get("validation_passed_count") == facts["validation_executed_count"]
        and all(
            facts.get(field) == 0
            for field in (
                "validation_failed_count",
                "validation_error_count",
                "validation_skipped_count",
                "validation_xfail_count",
                "validation_xpass_count",
            )
        )
        and facts.get("validation_outer_terminal_status") == "COMPLETED"
        and isinstance(facts.get("validation_evidence_identity"), str)
    )


def _final_release_violations(facts: dict[str, Any], mode: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    required = {
        "blockers",
        "closure_items",
        "mutations",
        "mutators",
        "validation_ladder",
        "validation_execution",
        "writer_proof",
    }
    if mode in {"STANDARD", "RESCUE"}:
        required |= {"boundary_smoke", "expensive_operations"}
    missing = sorted(required - set(facts.get("capabilities", [])))
    if missing:
        out.append(_violation("FINAL_RELEASE_FACTS_INCOMPLETE", capabilities=missing))
        return out
    if facts.get("open_item_count") != 0:
        out.append(_violation("FINAL_RELEASE_HAS_OPEN_ITEMS"))
    if facts.get("remaining_mutation_count") != 0:
        out.append(_violation("FINAL_RELEASE_HAS_REMAINING_MUTATIONS"))
    if facts.get("blocker_count") != 0:
        out.append(_violation("FINAL_RELEASE_HAS_BLOCKERS"))
    if facts.get("active_mutator_count") != 0:
        out.append(_violation("FINAL_RELEASE_HAS_ACTIVE_MUTATOR"))
    if "expensive_operations" in required and facts.get("active_expensive_run_count") != 0:
        out.append(_violation("FINAL_RELEASE_HAS_ACTIVE_EXPENSIVE_RUN"))
    if facts.get("writer_free") is not True or not facts.get("writer_proof_identity"):
        out.append(_violation("FINAL_RELEASE_WRITER_PROOF_INVALID"))
    if not _validation_clean(facts):
        out.append(_violation("FINAL_RELEASE_VALIDATION_EVIDENCE_INVALID"))
    if "boundary_smoke" in required and facts.get("boundary_smoke_status") != "PASS":
        out.append(_violation("FINAL_RELEASE_BOUNDARY_SMOKE_NOT_PASS"))
    if "authority" in facts.get("capabilities", []) and facts.get("authority_status") not in {
        "NOT_APPLICABLE", "ACTIVATED"
    }:
        out.append(_violation("FINAL_RELEASE_AUTHORITY_NOT_ACTIVE"))
    if "run_state" in facts.get("capabilities", []):
        if facts.get("run_state_replay_verified") is not True:
            out.append(_violation("FINAL_RELEASE_RUN_STATE_REPLAY_INVALID"))
        if facts.get("run_state_projection_matches_replay") is not True:
            out.append(_violation("FINAL_RELEASE_RUN_STATE_PROJECTION_INVALID"))
        if facts.get("duplicate_start_count") != 0:
            out.append(_violation("FINAL_RELEASE_DUPLICATE_START_PRESENT"))
        if facts.get("old_transaction_resume_count") != 0:
            out.append(_violation("FINAL_RELEASE_OLD_RESUME_PRESENT"))
    return out


def compare(
    baseline: dict[str, Any],
    current: dict[str, Any],
    *,
    max_event_delta: int,
    max_hotfix_delta: int,
    max_expensive_start_delta: int = 1,
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
    if baseline.get("lineage") != current.get("lineage"):
        out.append(_violation("BASELINE_LINEAGE_CHANGED_WITHOUT_REBASE"))
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
    if before.get("campaign_token") != after.get("campaign_token"):
        out.append(_violation("CAMPAIGN_CHANGED"))
    if before.get("rescue_deadline_at") != after.get("rescue_deadline_at"):
        out.append(_violation("RESCUE_DEADLINE_CHANGED"))
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
        _increase(
            out,
            before.get("remaining_mutation_count"),
            after.get("remaining_mutation_count"),
            "REMAINING_MUTATION_COUNT_INCREASED",
        )
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
    if "validation_execution" in new_caps:
        if after.get("validation_outer_terminal_status") == "COMPLETED" and not _validation_clean(after):
            out.append(_violation("VALIDATION_COMPLETED_WITHOUT_CLEAN_EXECUTION"))
    if "mutators" in new_caps and (after.get("active_mutator_count") or 0) > 1:
        out.append(_violation("CONCURRENT_MUTATORS", active=after["active_mutator_count"]))
    if "writer_proof" in new_caps:
        if after.get("writer_free") is True and (after.get("active_mutator_count") or 0) > 0:
            out.append(_violation("WRITER_PROOF_CONTRADICTS_ACTIVE_MUTATOR"))
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
        authority_changed = (
            before.get("authority_status") != after.get("authority_status")
            or before.get("authority_revision_identity") != after.get("authority_revision_identity")
        )
        if authority_changed:
            out.append(_violation("AUTHORITY_REVISION_REQUIRES_ACCEPTED_REBASE"))
        if (
            before.get("authority_status") == "REJECTED"
            and isinstance(b, int)
            and isinstance(a, int)
            and a > b
        ):
            out.append(_violation("REJECTED_AUTHORITY_BRANCH_REOPENED_WITHOUT_REBASE"))
    if "object_scope" in old_caps | new_caps:
        before_allowed = set(before.get("allowed_object_ids", []))
        after_allowed = set(after.get("allowed_object_ids", []))
        if before_allowed != after_allowed:
            out.append(_violation("ALLOWED_OBJECT_SET_CHANGED"))
        outside = sorted(
            set(after.get("changed_object_ids", []))
            - set(before.get("changed_object_ids", []))
            - before_allowed
        )
        if outside:
            out.append(_violation("FROZEN_OBJECT_SET_EXPANDED", count=len(outside)))
        if before.get("protected_content_identity") != after.get("protected_content_identity"):
            out.append(_violation("PROTECTED_CONTENT_CHANGED"))
    if "waivers" in old_caps | new_caps:
        new_waivers = sorted(set(after.get("waiver_ids", [])) - set(before.get("waiver_ids", [])))
        if new_waivers:
            out.append(_violation("WAIVER_SET_EXPANDED_WITHOUT_REBASE", count=len(new_waivers)))
        if before.get("waiver_scope_identity") != after.get("waiver_scope_identity"):
            out.append(_violation("WAIVER_SCOPE_CHANGED_WITHOUT_REBASE"))
    if "run_state" in new_caps:
        _regression(
            out,
            before.get("run_state_terminal_count"),
            after.get("run_state_terminal_count"),
            "RUN_STATE_TERMINAL_COUNT_REGRESSED",
        )
        if after.get("run_state_replay_verified") is not True:
            out.append(_violation("RUN_STATE_REPLAY_NOT_VERIFIED"))
        if after.get("run_state_projection_matches_replay") is not True:
            out.append(_violation("RUN_STATE_PROJECTION_MISMATCH"))
        if (after.get("duplicate_start_count") or 0) > 0:
            out.append(_violation("DUPLICATE_START_DETECTED"))
        if (after.get("old_transaction_resume_count") or 0) > 0:
            out.append(_violation("OLD_TRANSACTION_RESUME_DETECTED"))
    if "final_boundary" in old_caps | new_caps:
        b = before.get("final_boundary_start_count")
        a = after.get("final_boundary_start_count")
        _regression(out, b, a, "FINAL_BOUNDARY_START_COUNT_REGRESSED")
        if isinstance(b, int) and isinstance(a, int) and a > b:
            if a - b > 1:
                out.append(_violation("DUPLICATE_FINAL_BOUNDARY_START", delta=a - b))
            if not allow_final_start:
                out.append(_violation("FINAL_BOUNDARY_STARTED_BEFORE_GUARD_RELEASE"))
            else:
                out.extend(_final_release_violations(after, current["mode"]))
    return out


def _test_snapshot(facts: dict[str, Any], mode: str = "STANDARD") -> dict[str, Any]:
    defaults: dict[str, Any] = {}
    if mode in {"STANDARD", "RESCUE"}:
        defaults = {
            "project_id": "self-test",
            "closure_item_ids": ["BASE"],
            "open_item_ids": ["BASE"],
            "planned_mutation_count": 1,
            "completed_mutation_count": 0,
            "validation_level": "BASELINE",
            "validation_rank": 0,
            "active_mutator_count": 0,
        }
    if mode == "RESCUE":
        defaults.update(
            {
                "campaign_id": "self-test-rescue",
                "active_expensive_run_count": 0,
                "expensive_start_count": 0,
                "writer_free": True,
                "writer_proof_identity": "WRITER-PROOF",
                "boundary_smoke_status": "PENDING",
            }
        )
    normalized = _normalize({**defaults, **facts})
    campaign_token = normalized.get("campaign_token") or normalized.get("project_token")
    snapshot = {
        "schema_id": SCHEMA_ID,
        "profile": "generic",
        "mode": mode,
        "repo": None,
        "facts": normalized,
        "lineage": {
            "campaign_token": campaign_token,
            "parent_snapshot_sha256": None,
            "accepted_rebaseline_count": 0,
        },
    }
    snapshot["snapshot_sha256"] = _digest(snapshot)
    _validate_snapshot(snapshot, "test snapshot")
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
    science0 = _test_snapshot({
        "project_id": "science", "authority_status": "REJECTED",
        "authority_revision_count": 1, "authority_revision_identity": "AUTHORITY-1",
    })
    science1 = _test_snapshot({
        "project_id": "science", "authority_status": "PROPOSED",
        "authority_revision_count": 2, "authority_revision_identity": "AUTHORITY-2",
    })
    assert "REJECTED_AUTHORITY_BRANCH_REOPENED_WITHOUT_REBASE" in _test_codes(science0, science1)
    release_base = {
        "project_id": "release", "closure_item_ids": ["R"], "open_item_ids": [],
        "planned_mutation_count": 1, "completed_mutation_count": 1,
        "validation_level": "ACCEPTANCE", "validation_rank": 4,
        "validation_discovered_count": 1, "validation_executed_count": 1,
        "validation_passed_count": 1, "validation_failed_count": 0,
        "validation_error_count": 0, "validation_skipped_count": 0,
        "validation_xfail_count": 0, "validation_xpass_count": 0,
        "validation_evidence_identity": "VALIDATION", "validation_outer_terminal_status": "COMPLETED",
        "active_mutator_count": 0, "active_expensive_run_count": 0,
        "expensive_start_count": 0, "writer_free": True,
        "writer_proof_identity": "WRITER", "boundary_smoke_status": "PASS",
        "boundary_smoke_identity": "SMOKE", "authority_status": "NOT_APPLICABLE",
        "blocker_ids": [], "capabilities": ["blockers"],
    }
    release0 = _test_snapshot({**release_base, "final_boundary_start_count": 0})
    release1 = _test_snapshot({**release_base, "final_boundary_start_count": 1})
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
        "independent_authority_review_required": True, "authority_status": "UNRESOLVED",
    }, "RESCUE")
    review2 = _test_snapshot({
        "project_id": "review", "delegated_task_ids": ["D1", "D2"],
        "active_subagent_count": 2, "subagent_spawn_count": 2,
        "independent_authority_review_required": True, "authority_status": "UNRESOLVED",
    }, "RESCUE")
    assert "ACTIVE_SUBAGENT_LIMIT_EXCEEDED" not in _test_codes(review0, review2)
    regressed0 = _test_snapshot({
        "project_id": "monotonic", "planned_mutation_count": 2,
        "completed_mutation_count": 2,
        "control_event_count": 4, "expensive_start_count": 3,
        "final_boundary_start_count": 1, "authority_revision_count": 2,
        "authority_status": "UNRESOLVED",
        "subagent_spawn_count": 1, "delegated_task_count": 1,
    })
    regressed1 = _test_snapshot({
        "project_id": "monotonic", "planned_mutation_count": 2,
        "completed_mutation_count": 1,
        "control_event_count": 3, "expensive_start_count": 2,
        "final_boundary_start_count": 0, "authority_revision_count": 1,
        "authority_status": "UNRESOLVED",
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
    repo_token = _tokens("repo", ["repo"])[0]
    planned_path_token = _tokens("path", ["P1"])[0]
    outside_path_token = _tokens("path", ["P2"])[0]
    git0["repo"] = {
        "repo_token": repo_token, "head": "H1", "tracked_changed_count": 0,
        "untracked_count": 0, "tracked_path_tokens": [], "untracked_path_tokens": [],
        "changed_path_tokens": [], "allowed_path_tokens": [planned_path_token],
        "allowed_path_count": 1, "changed_paths_sha256": _digest([[], []]),
    }
    _reseal_test_snapshot(git0)
    git1 = {**git0, "repo": {**git0["repo"], "head": "H2"}}
    _reseal_test_snapshot(git1)
    assert "WORKTREE_HEAD_CHANGED" in _test_codes(git0, git1)
    planned = {
        **git0,
        "repo": {**git0["repo"], "changed_path_tokens": [planned_path_token]},
    }
    _reseal_test_snapshot(planned)
    assert "FROZEN_PATH_SET_EXPANDED" not in _test_codes(git0, planned)
    outside = {
        **git0,
        "repo": {**git0["repo"], "changed_path_tokens": [outside_path_token]},
    }
    _reseal_test_snapshot(outside)
    assert "FROZEN_PATH_SET_EXPANDED" in _test_codes(git0, outside)
    tampered = dict(git0)
    tampered["mode"] = "LIGHT"
    assert "BASELINE_SNAPSHOT_INVALID" in _test_codes(tampered, git1)
    semantic_resign = {
        **small1,
        "facts": {**small1["facts"], "remaining_mutation_count": 1},
    }
    _reseal_test_snapshot(semantic_resign)
    assert "CURRENT_SNAPSHOT_INVALID" in _test_codes(small0, semantic_resign)
    try:
        _strict_json_text('{"a": 1, "a": 2}', "test JSON")
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate JSON key accepted")
    object0 = _test_snapshot({
        "project_id": "objects", "changed_object_ids": ["OLD"],
        "allowed_object_ids": ["TARGET"], "protected_content_identity": "P1",
    })
    object1 = _test_snapshot({
        "project_id": "objects", "changed_object_ids": ["OLD", "TARGET"],
        "allowed_object_ids": ["TARGET"], "protected_content_identity": "P1",
    })
    assert "FROZEN_OBJECT_SET_EXPANDED" not in _test_codes(object0, object1)
    object_bad = _test_snapshot({
        "project_id": "objects", "changed_object_ids": ["OLD", "ADJACENT"],
        "allowed_object_ids": ["TARGET"], "protected_content_identity": "P2",
    })
    assert {"FROZEN_OBJECT_SET_EXPANDED", "PROTECTED_CONTENT_CHANGED"} <= _test_codes(
        object0, object_bad
    )
    skipped = _test_snapshot({
        "project_id": "validation", "validation_discovered_count": 1,
        "validation_executed_count": 0, "validation_passed_count": 0,
        "validation_failed_count": 0, "validation_error_count": 0,
        "validation_skipped_count": 1, "validation_xfail_count": 0,
        "validation_xpass_count": 0, "validation_evidence_identity": "V1",
        "validation_outer_terminal_status": "COMPLETED",
    })
    assert "VALIDATION_COMPLETED_WITHOUT_CLEAN_EXECUTION" in _test_codes(skipped, skipped)
    state_bad = _test_snapshot({
        "project_id": "state", "run_state_head_identity": "H1",
        "run_state_terminal_count": 1, "run_state_replay_verified": False,
        "run_state_projection_matches_replay": False, "duplicate_start_count": 1,
        "old_transaction_resume_count": 1,
    })
    assert {
        "RUN_STATE_REPLAY_NOT_VERIFIED", "RUN_STATE_PROJECTION_MISMATCH",
        "DUPLICATE_START_DETECTED", "OLD_TRANSACTION_RESUME_DETECTED",
    } <= _test_codes(state_bad, state_bad)
    incomplete_release = _test_snapshot({
        "project_id": "incomplete-release", "final_boundary_start_count": 0,
    })
    incomplete_started = _test_snapshot({
        "project_id": "incomplete-release", "final_boundary_start_count": 1,
    })
    assert "FINAL_RELEASE_FACTS_INCOMPLETE" in _test_codes(
        incomplete_release, incomplete_started, allow_final=True
    )
    successor = {**release0, "lineage": {
        "campaign_token": release0["lineage"]["campaign_token"],
        "parent_snapshot_sha256": release0["snapshot_sha256"],
        "accepted_rebaseline_count": 1,
    }}
    _reseal_test_snapshot(successor)
    assert not _rebaseline_violations(release0, successor)
    reset = {**successor, "facts": {**successor["facts"], "completed_mutation_count": 0}}
    _reseal_test_snapshot(reset)
    assert "REBASE_RESET_COMPLETED_MUTATIONS" in {
        row["code"] for row in _rebaseline_violations(release0, reset)
    }
    try:
        _normalize({"authority_status": "ACTIVE"})
    except ValueError:
        pass
    else:
        raise AssertionError("event-style authority status was accepted")
    print("closure_guard_self_test=PASS scenarios=22")


def _add_capture_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", type=Path)
    parser.add_argument(
        "--allowed-paths-from",
        help="newline-delimited planned repository paths; freeze only when taking a baseline",
    )
    parser.add_argument("--facts")
    parser.add_argument("--profile", choices=("auto", "git", "generic"), default="auto")
    parser.add_argument("--mode", choices=tuple(MODES), default="STANDARD")


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    take = commands.add_parser("snapshot")
    _add_capture_args(take)
    take.add_argument("--predecessor", help="validated V5 predecessor for one accepted rebaseline")
    take.add_argument("--accept-rebaseline", action="store_true")
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
    check.add_argument("--allow-final-start", action="store_true")
    commands.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        _self_test()
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
        if predecessor is not None:
            violations = _rebaseline_violations(predecessor, current)
            if violations:
                raise ValueError(
                    "accepted rebaseline violates predecessor: "
                    + ",".join(row["code"] for row in violations)
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
        inherited_lineage=baseline["lineage"],
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
        allow_final_start=args.allow_final_start,
    )
    scope_codes = {
        "BASELINE_SCHEMA_INCOMPATIBLE", "BASELINE_SNAPSHOT_INVALID",
        "BASELINE_LINEAGE_CHANGED_WITHOUT_REBASE", "CAMPAIGN_CHANGED",
        "CAPABILITY_SET_EXPANDED", "CAPABILITY_SET_REDUCED",
        "CLOSURE_ITEM_DENOMINATOR_INCREASED",
        "CLOSURE_ITEM_SET_EXPANDED", "FROZEN_PATH_SET_EXPANDED", "ALLOWED_PATH_SET_CHANGED",
        "FROZEN_OBJECT_SET_EXPANDED", "ALLOWED_OBJECT_SET_CHANGED", "PROTECTED_CONTENT_CHANGED",
        "AUTHORITY_REVISION_REQUIRES_ACCEPTED_REBASE", "RESCUE_DEADLINE_CHANGED",
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
