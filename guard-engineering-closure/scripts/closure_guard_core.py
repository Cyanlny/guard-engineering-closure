"""Read-only, capability-aware scope guard for engineering closure."""

import hashlib
import json
import os
import stat
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any


SCHEMA_ID = "ENGINEERING_CLOSURE_GUARD_SNAPSHOT_V9"
V8_SCHEMA_ID = "ENGINEERING_CLOSURE_GUARD_SNAPSHOT_V8"
V7_SCHEMA_ID = "ENGINEERING_CLOSURE_GUARD_SNAPSHOT_V7"
MODES = {
    "LIGHT": {"events": 0, "mutations": 1, "expensive": 1, "subagents": 0},
    "STANDARD": {"events": 4, "mutations": 1, "expensive": 1, "subagents": 2},
    "RESCUE": {"events": 2, "mutations": 1, "expensive": 1, "subagents": 1},
}
LIST_FIELDS = tuple("closure_item_ids open_item_ids blocker_ids delegated_task_ids changed_object_ids allowed_object_ids waiver_ids capabilities".split())
INT_FIELDS = tuple(
    """closure_item_count open_item_count closed_item_count planned_mutation_count completed_mutation_count
    remaining_mutation_count validation_rank validation_discovered_count validation_executed_count validation_passed_count
    validation_failed_count validation_error_count validation_skipped_count validation_xfail_count validation_xpass_count
    control_event_count active_mutator_count active_expensive_run_count expensive_start_count delegated_task_count
    subagent_spawn_count active_subagent_count active_subagent_mutator_count active_subagent_expensive_run_count
    recursive_delegation_count final_boundary_start_count authority_revision_count run_state_terminal_count
    duplicate_start_count old_transaction_resume_count""".split()
)
TEXT_FIELDS = tuple(
    """project_id campaign_id change_generation validation_level validation_evidence_identity validation_outer_terminal_status
    authority_status authority_revision_identity protected_content_identity writer_proof_identity boundary_smoke_identity
    boundary_smoke_status run_state_head_identity waiver_scope_identity rescue_deadline_at""".split()
)
BOOL_FIELDS = tuple("independent_authority_review_required writer_free run_state_replay_verified run_state_projection_matches_replay".split())
FACT_FIELDS = set(LIST_FIELDS + INT_FIELDS + TEXT_FIELDS + BOOL_FIELDS)
FACT_FIELDS.update({"campaign_control", "control_economy"})
CAPABILITIES = set(
    """authority boundary_smoke blockers campaign_lineage campaign_control closure_items control_events control_economy
    delegation expensive_operations final_boundary mutations mutators object_scope run_state validation_ladder
    validation_execution vcs waivers writer_proof""".split()
)
AUTHORITY_STATUSES = set("NOT_APPLICABLE UNRESOLVED PROPOSED APPROVED ACTIVATED REJECTED".split())
BOUNDARY_SMOKE_STATUSES = {"NOT_APPLICABLE", "PENDING", "PASS", "BLOCKED", "FAILED_TYPED"}
TERMINAL_STATUSES = {"NOT_APPLICABLE", "COMPLETED", "BLOCKED", "FAILED_TYPED", "INCOMPLETE"}
OBJECTIVE_OWNERS = ("P0", "S1", "S2", "S3")
CONTROL_COSTS = tuple("DECISION AUTHORITY_ROUNDTRIP BLOCKER_ROUNDTRIP BLOCKING_GATE FULL_VALIDATION FULL_HASH_SCAN DURABLE_CONTROL_ARTIFACT CONTEXT_RECONSTRUCTION".split())
CONTROL_EFFECTS = set("CLOSE_CLOSURE_ITEM ADVANCE_VALIDATION CHANGE_MATERIAL_ACTION SATISFY_PROTECTED_BOUNDARY".split())
STAGE_BOUNDARIES = {"DESIGN_COMPLETE", "BUILD_COMPLETE"}
STAGE_AUDIT_OUTCOMES = {"PASS", "REDUCTION_REQUIRED", "BLOCKED_AUTHORITY"}
STAGE_ACTIONS = {
    "DESIGN_COMPLETE": "STAGE_DESIGN_AUDIT",
    "BUILD_COMPLETE": "STAGE_BUILD_AUDIT",
}
SURFACE_FIELDS = tuple("control_responsibilities canonical_control_routes blocking_gates recovery_branches durable_control_artifacts".split())
FINDING_TIERS = {"HARD_FAIL", "REVIEW_REQUIRED", "WARNING", "INFO"}
FINDING_REACHABILITY = {"REACHABLE", "UNREACHABLE", "UNKNOWN"}
PRIMARY_STATES = {"PREPARING", "READY", "RUNNING", "TERMINAL"}
RECOVERY_STATES = {"NOT_APPLICABLE", "DORMANT", "ACTIVE", "TERMINAL"}
CONTROL_ECONOMY_FIELDS = set(
    "envelope_identity origin_identity objective_scope_identity stop_point_identity limits records decision_request active_frontier findings classification_sets surface_budget".split()
)
CONTROL_RECORD_FIELDS = set(
    """decision_id objective_owner state_key_sha256 decision_key_sha256 action_class active_consumer_identity validator_identity
    authority_identity trust_boundary_identity protected_constraint_identity costs effect stage_audit record_sha256""".split()
)
CAMPAIGN_RESOURCES = ("mutations", "expensive_starts")
ATTEMPT_STATUSES = {"ACTIVE", "COMPLETED", "FAILED_TYPED", "BLOCKED", "INCOMPLETE"}
CAMPAIGN_CONTROL_FIELDS = set(
    "envelope_identity origin_identity objective_scope_identity origin_completed_mutation_count origin_expensive_start_count absolute_limits objective_limits objective_consumed attempt_records".split()
)
ATTEMPT_RECORD_FIELDS = set("attempt_id objective_owner equivalence_key_sha256 start_identity status terminal_evidence_identity".split())
MODE_REQUIRED_CAPABILITIES = {
    "LIGHT": set(),
    "STANDARD": set("closure_items mutations validation_ladder mutators control_economy".split()),
    "RESCUE": set("closure_items mutations validation_ladder mutators campaign_lineage expensive_operations writer_proof boundary_smoke control_economy".split()),
}
CAPABILITY_REQUIRED_FACTS = {
    "closure_items": tuple("closure_item_count open_item_count closed_item_count".split()),
    "mutations": tuple("planned_mutation_count completed_mutation_count remaining_mutation_count".split()),
    "validation_ladder": ("validation_rank",),
    "mutators": ("active_mutator_count",),
    "control_events": ("control_event_count",),
    "expensive_operations": ("active_expensive_run_count", "expensive_start_count"),
    "delegation": tuple(
        "delegated_task_count subagent_spawn_count active_subagent_count active_subagent_mutator_count active_subagent_expensive_run_count recursive_delegation_count".split()
    ),
    "final_boundary": ("final_boundary_start_count",),
}
REBASE_REQUIRED_CODES = set(
    """BASELINE_SCHEMA_INCOMPATIBLE BASELINE_SNAPSHOT_INVALID BASELINE_LINEAGE_CHANGED_WITHOUT_REBASE CAMPAIGN_CHANGED
    CAPABILITY_SET_EXPANDED CAPABILITY_SET_REDUCED CLOSURE_ITEM_DENOMINATOR_INCREASED CLOSURE_ITEM_SET_EXPANDED
    FROZEN_PATH_SET_EXPANDED ALLOWED_PATH_SET_CHANGED FROZEN_OBJECT_SET_EXPANDED ALLOWED_OBJECT_SET_CHANGED
    PROTECTED_CONTENT_CHANGED AUTHORITY_REVISION_REQUIRES_ACCEPTED_REBASE RESCUE_DEADLINE_CHANGED
    CAMPAIGN_CONTROL_CHANGED_WITHOUT_REBASE CAMPAIGN_ENVELOPE_DRIFT OBJECTIVE_SCOPE_DRIFT
    OBJECTIVE_LIMITS_CHANGED_WITHOUT_REBASE DELEGATED_TASK_DENOMINATOR_INCREASED DELEGATED_TASK_SET_EXPANDED
    WORKTREE_HEAD_CHANGED GUARD_MODE_CHANGED GUARD_PROFILE_CHANGED PROJECT_CHANGED PROJECT_IDENTITY_SOURCE_CHANGED""".split()
)

MACHINE_FACT_FIELDS = set(
    "head head_tree git_head git_tree dirty_paths dirty_path_tokens dirty_records allowed_path_delta scope_delta lineage snapshot_lineage snapshot_sha256 activation_identity".split()
)
UPGRADE_HISTORY_FIELDS = tuple(
    """project_token campaign_token change_generation closure_item_ids open_item_ids closure_item_count open_item_count closed_item_count
    planned_mutation_count completed_mutation_count remaining_mutation_count expensive_start_count active_expensive_run_count changed_object_ids
    allowed_object_ids protected_content_identity authority_status authority_revision_count authority_revision_identity campaign_control
    run_state_terminal_count duplicate_start_count old_transaction_resume_count""".split()
)
V8_UPGRADE_EXTRA_FIELDS = ("blocker_ids", "control_event_count", "capabilities")
UPGRADE_REPO_FIELDS = tuple("repo_token head changed_paths_sha256 changed_path_tokens allowed_path_tokens".split())


class GuardInputError(ValueError):
    """Typed capture/input failure without changing the CLI exit contract."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


def _count_conflict(message: str, **details: Any) -> None:
    raise GuardInputError("MACHINE_COUNT_CONFLICT", message, **details)


def _run(argv: list[str], cwd: Path) -> bytes:
    return subprocess.run(argv, cwd=str(cwd), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


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
    if str(normalized) in ("", ".") or ".." in normalized.parts or any(part.casefold() == ".git" for part in normalized.parts):
        raise ValueError(f"invalid allowed repository path: {value}")
    return normalized.as_posix()


def _casefold_key(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def _reject_case_collisions(paths: list[str]) -> None:
    seen: dict[str, str] = {}
    for value in paths:
        key = _casefold_key(value)
        if key in seen and seen[key] != value:
            raise GuardInputError(
                "REPOSITORY_PATH_CASE_COLLISION",
                "repository path set contains a case-fold collision",
                paths=sorted((seen[key], value)),
            )
        seen[key] = value


def _git_root(repo: Path) -> Path:
    root = Path(_run(["git", "rev-parse", "--show-toplevel"], repo.resolve()).decode().strip())
    return root.resolve()


def _git_dir(repo: Path) -> Path:
    value = Path(_run(["git", "rev-parse", "--git-dir"], repo).decode().strip())
    return value.resolve() if value.is_absolute() else (repo / value).resolve()


def _writer_signals(repo: Path) -> list[str]:
    git_dir = _git_dir(repo)
    names = (
        "index.lock",
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "rebase-apply",
        "rebase-merge",
        "sequencer",
    )
    return sorted(name for name in names if (git_dir / name).exists())


def _submodule_paths(repo: Path) -> list[str]:
    rows = _run(["git", "ls-files", "--stage", "-z"], repo).split(b"\0")
    out: list[str] = []
    for row in rows:
        if not row:
            continue
        meta, sep, raw_path = row.partition(b"\t")
        if sep and meta.split(b" ", 1)[0] == b"160000":
            out.append(raw_path.decode("utf-8"))
    return sorted(out)


def _validate_repo_object(repo: Path, relative: str, submodules: list[str]) -> None:
    if any(relative == item or relative.startswith(item + "/") for item in submodules):
        raise GuardInputError(
            "REPOSITORY_SUBMODULE_PATH_PROHIBITED",
            "path scope cannot cross a submodule boundary",
            path=relative,
        )
    root_stat = os.stat(repo)
    current = repo
    parts = Path(relative).parts
    for index, part in enumerate(parts):
        current = current / part
        try:
            observed = os.lstat(current)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(observed.st_mode):
            raise GuardInputError(
                "REPOSITORY_SYMLINK_PATH_PROHIBITED",
                "path scope cannot contain a symlink",
                path=relative,
            )
        if observed.st_dev != root_stat.st_dev:
            raise GuardInputError(
                "REPOSITORY_EXTERNAL_MOUNT_PROHIBITED",
                "path scope cannot cross a filesystem mount",
                path=relative,
            )
        if index < len(parts) - 1 and not stat.S_ISDIR(observed.st_mode):
            raise GuardInputError(
                "REPOSITORY_PATH_COMPONENT_INVALID",
                "an intermediate path component is not a directory",
                path=relative,
            )
        if index == len(parts) - 1:
            if stat.S_ISREG(observed.st_mode) and observed.st_nlink > 1:
                raise GuardInputError(
                    "REPOSITORY_HARDLINK_PATH_PROHIBITED",
                    "path scope cannot contain a multiply linked file",
                    path=relative,
                )
            if not (stat.S_ISREG(observed.st_mode) or stat.S_ISDIR(observed.st_mode)):
                raise GuardInputError(
                    "REPOSITORY_SPECIAL_FILE_PROHIBITED",
                    "path scope cannot contain a special filesystem object",
                    path=relative,
                )


def _dirty_signature(value: os.stat_result) -> list[int]:
    return [value.st_dev, value.st_ino, value.st_mode, value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns]


def _stable_dirty_identity(repo: Path, relative: str, cached: list[Any] | None = None) -> list[Any]:
    path = repo / relative
    try:
        before = os.lstat(path)
    except FileNotFoundError:
        return [0, 0, 0, 0, -1, 0, 0, _digest([relative, "MISSING"])]
    if not stat.S_ISREG(before.st_mode):
        raise GuardInputError(
            "REPOSITORY_SPECIAL_FILE_PROHIBITED",
            "dirty content must be a regular file",
            path=relative,
        )
    signature = _dirty_signature(before)
    if cached is not None and cached[:7] == signature:
        if _dirty_signature(os.lstat(path)) != signature:
            raise GuardInputError("ACTIVATION_STATE_DRIFT", "dirty file metadata changed during cache reuse", path=relative)
        return cached
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise GuardInputError(
            "ACTIVATION_STATE_DRIFT",
            "dirty file could not be opened under its captured identity",
            path=relative,
        ) from exc
    try:
        opened = os.fstat(descriptor)

        if signature != _dirty_signature(opened):
            raise GuardInputError(
                "ACTIVATION_STATE_DRIFT",
                "dirty file changed while its descriptor was opened",
                path=relative,
            )
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after_open = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        after_path = os.lstat(path)
    except FileNotFoundError as exc:
        raise GuardInputError(
            "ACTIVATION_STATE_DRIFT",
            "dirty file disappeared during capture",
            path=relative,
        ) from exc
    if signature != _dirty_signature(after_open) or signature != _dirty_signature(after_path):
        raise GuardInputError(
            "ACTIVATION_STATE_DRIFT",
            "dirty file changed during capture",
            path=relative,
        )
    return [*signature, digest.hexdigest()]


def _diff_paths(repo: Path, base: str) -> tuple[list[str], list[tuple[str, str]]]:
    fields = _run(["git", "diff", "--name-status", "-z", "-M", base], repo).split(b"\0")
    paths: list[str] = []
    renames: list[tuple[str, str]] = []
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index].decode("ascii", errors="strict")
        index += 1
        if status[:1] in {"R", "C"}:
            if index + 1 >= len(fields):
                raise ValueError("malformed git rename/copy record")
            old = fields[index].decode("utf-8")
            new = fields[index + 1].decode("utf-8")
            index += 2
            paths.extend((old, new))
            renames.append((old, new))
        else:
            if index >= len(fields):
                raise ValueError("malformed git path record")
            paths.append(fields[index].decode("utf-8"))
            index += 1
    return sorted(set(paths)), sorted(set(renames))


def _allowed_paths(repo: Path, source: str | None) -> list[str]:
    if source is None:
        return []
    text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    paths = sorted({_normalize_repo_path(repo, line.strip()) for line in text.splitlines() if line.strip()})
    _reject_case_collisions(paths)
    return paths


def _git(
    repo: Path,
    *,
    allowed_paths_from: str | None = None,
    inherited_allowed_path_tokens: list[str] | None = None,
    inherited_dirty_records: dict[str, list[Any]] | None = None,
    comparison_base_head: str | None = None,
) -> dict[str, Any]:
    repo = _git_root(repo)
    writer_signals = _writer_signals(repo)
    if writer_signals:
        raise GuardInputError(
            "ACTIVATION_STATE_DRIFT",
            "repository has an active local Git writer signal",
            writer_signals=writer_signals,
        )
    head = _run(["git", "rev-parse", "HEAD"], repo).decode().strip()
    head_tree = _run(["git", "rev-parse", "HEAD^{tree}"], repo).decode().strip()
    tracked, dirty_renames = _diff_paths(repo, "HEAD")
    if comparison_base_head is None or comparison_base_head == head:
        scope_tracked, scope_renames = tracked, dirty_renames
    else:
        scope_tracked, scope_renames = _diff_paths(repo, comparison_base_head)
    untracked = _paths(_run(["git", "ls-files", "--others", "--exclude-standard", "-z"], repo))
    allowed_paths = _allowed_paths(repo, allowed_paths_from)
    inspected = sorted(set(tracked) | set(scope_tracked) | set(untracked) | set(allowed_paths))
    _reject_case_collisions(inspected)
    submodules = _submodule_paths(repo)
    for relative in inspected:
        normalized = _normalize_repo_path(repo, relative)
        if normalized != relative:
            raise GuardInputError(
                "REPOSITORY_PATH_NOT_CANONICAL",
                "Git returned a non-canonical repository path",
                path=relative,
            )
        _validate_repo_object(repo, relative, submodules)
    tracked_tokens = _tokens("tracked", tracked)
    untracked_tokens = _tokens("untracked", untracked)
    changed_path_tokens = _tokens("path", sorted(set(scope_tracked) | set(tracked) | set(untracked)))
    allowed_tokens = _tokens("path", allowed_paths) if allowed_paths_from is not None else sorted(inherited_allowed_path_tokens or [])
    dirty_records: dict[str, list[Any]] = {}
    dirty_content: dict[str, str] = {}
    for relative in sorted(set(tracked) | set(untracked)):
        token = _tokens("path", [relative])[0]
        dirty_records[token] = _stable_dirty_identity(repo, relative, (inherited_dirty_records or {}).get(token))
        dirty_content[relative] = dirty_records[token][-1]
    return {
        "repo_token": _tokens("repo", [str(repo)])[0],
        "head": head,
        "tracked_changed_count": len(tracked),
        "untracked_count": len(untracked),
        "tracked_path_tokens": tracked_tokens,
        "untracked_path_tokens": untracked_tokens,
        "changed_path_tokens": changed_path_tokens,
        "allowed_path_tokens": allowed_tokens,
        "allowed_path_count": len(allowed_tokens),
        "dirty_records": dirty_records,
        "changed_paths_sha256": _digest(
            {
                "head_tree": head_tree,
                "dirty_content": dirty_content,
                "dirty_renames": dirty_renames,
                "scope_renames": scope_renames,
                "writer_signals": writer_signals,
            }
        ),
    }


def _nonnegative(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a nonnegative integer or null")
    return value


def _required_nonnegative(value: Any, field: str) -> int:
    normalized = _nonnegative(value, field)
    if normalized is None:
        raise ValueError(f"{field} must be a nonnegative integer")
    return normalized


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


def _identity(value: Any, field: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        suffix = " or null" if optional else ""
        raise ValueError(f"{field} must be a nonempty string{suffix}")
    return value


def _sha256_identity(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{field} must be a lowercase SHA-256 identity")
    return value


def _sparse_resource_counts(value: Any, field: str) -> tuple[dict[str, int], set[str]]:
    if value is None:
        return {resource: 0 for resource in CAMPAIGN_RESOURCES}, set()
    if not isinstance(value, dict) or not set(value) <= set(CAMPAIGN_RESOURCES):
        raise ValueError(f"{field} contains unknown resources")
    return (
        {resource: _required_nonnegative(value[resource], f"{field}.{resource}") if resource in value else 0 for resource in CAMPAIGN_RESOURCES},
        set(value),
    )


def _sparse_objective_counts(value: Any, field: str) -> tuple[dict[str, dict[str, int]], dict[str, set[str]]]:
    if value is None:
        raw: dict[str, Any] = {}
    elif not isinstance(value, dict) or not set(value) <= set(OBJECTIVE_OWNERS):
        raise ValueError(f"{field} contains unknown objective owners")
    else:
        raw = value
    normalized: dict[str, dict[str, int]] = {}
    supplied: dict[str, set[str]] = {}
    for owner in OBJECTIVE_OWNERS:
        normalized[owner], supplied[owner] = _sparse_resource_counts(raw.get(owner), f"{field}.{owner}")
    return normalized, supplied


def _normalize_campaign_control(value: Any, counts: dict[str, int | None] | None = None) -> dict[str, Any] | None:
    if value is None:
        return None
    required = CAMPAIGN_CONTROL_FIELDS - {"absolute_limits", "objective_consumed"}
    if not isinstance(value, dict) or not set(value) <= CAMPAIGN_CONTROL_FIELDS or not required <= set(value):
        raise ValueError("campaign_control fields do not match schema V7")
    objective_limits, _ = _sparse_objective_counts(value.get("objective_limits"), "campaign_control.objective_limits")
    absolute_derived = {resource: sum(objective_limits[owner][resource] for owner in OBJECTIVE_OWNERS) for resource in CAMPAIGN_RESOURCES}
    if value.get("absolute_limits") is None:
        absolute_limits = absolute_derived
    else:
        absolute_limits, supplied_absolute = _sparse_resource_counts(value.get("absolute_limits"), "campaign_control.absolute_limits")
        for resource in CAMPAIGN_RESOURCES:
            if resource not in supplied_absolute:
                absolute_limits[resource] = absolute_derived[resource]
            elif absolute_limits[resource] != absolute_derived[resource]:
                _count_conflict(
                    "absolute campaign limit disagrees with objective limits",
                    resource=resource,
                    supplied=absolute_limits[resource],
                    derived=absolute_derived[resource],
                )
    objective_consumed, supplied_consumed = _sparse_objective_counts(value.get("objective_consumed"), "campaign_control.objective_consumed")
    raw_records = value.get("attempt_records")
    if not isinstance(raw_records, list):
        raise ValueError("campaign_control.attempt_records must be a list")
    records: list[dict[str, Any]] = []
    seen_attempt_ids: set[str] = set()
    for index, record in enumerate(raw_records):
        label = f"campaign_control.attempt_records[{index}]"
        if not isinstance(record, dict) or set(record) != ATTEMPT_RECORD_FIELDS:
            raise ValueError(f"{label} fields do not match schema V7")
        attempt_id = _identity(record.get("attempt_id"), f"{label}.attempt_id")
        if attempt_id in seen_attempt_ids:
            raise ValueError("campaign_control.attempt_records contains duplicate attempt_id")
        seen_attempt_ids.add(attempt_id)
        owner = record.get("objective_owner")
        if owner not in OBJECTIVE_OWNERS:
            raise ValueError(f"{label}.objective_owner is invalid")
        status = record.get("status")
        if status not in ATTEMPT_STATUSES:
            raise ValueError(f"{label}.status is invalid")
        terminal_identity = _identity(
            record.get("terminal_evidence_identity"),
            f"{label}.terminal_evidence_identity",
            optional=True,
        )
        if status == "ACTIVE" and terminal_identity is not None:
            raise ValueError(f"{label} ACTIVE attempt cannot have terminal evidence")
        if status != "ACTIVE" and terminal_identity is None:
            raise ValueError(f"{label} terminal attempt requires terminal evidence")
        records.append(
            {
                "attempt_id": attempt_id,
                "objective_owner": owner,
                "equivalence_key_sha256": _sha256_identity(
                    record.get("equivalence_key_sha256"),
                    f"{label}.equivalence_key_sha256",
                ),
                "start_identity": _identity(record.get("start_identity"), f"{label}.start_identity"),
                "status": status,
                "terminal_evidence_identity": terminal_identity,
            }
        )
    records.sort(key=lambda row: row["attempt_id"])
    origin_mutations = _required_nonnegative(
        value.get("origin_completed_mutation_count"),
        "campaign_control.origin_completed_mutation_count",
    )
    origin_starts = _required_nonnegative(
        value.get("origin_expensive_start_count"),
        "campaign_control.origin_expensive_start_count",
    )
    starts_by_owner = {owner: sum(record["objective_owner"] == owner for record in records) for owner in OBJECTIVE_OWNERS}
    for owner in OBJECTIVE_OWNERS:
        supplied = supplied_consumed[owner]
        if "expensive_starts" in supplied and objective_consumed[owner]["expensive_starts"] != starts_by_owner[owner]:
            _count_conflict(
                "objective expensive-start consumption disagrees with attempt records",
                objective_owner=owner,
                supplied=objective_consumed[owner]["expensive_starts"],
                derived=starts_by_owner[owner],
            )
        objective_consumed[owner]["expensive_starts"] = starts_by_owner[owner]
    if counts is not None:
        derived_starts = origin_starts + len(records)
        supplied_starts = counts.get("expensive_start_count")
        if supplied_starts not in (None, derived_starts):
            _count_conflict(
                "expensive_start_count disagrees with attempt records",
                supplied=supplied_starts,
                derived=derived_starts,
            )
        counts["expensive_start_count"] = derived_starts
        derived_active = sum(record["status"] == "ACTIVE" for record in records)
        supplied_active = counts.get("active_expensive_run_count")
        if supplied_active not in (None, derived_active):
            _count_conflict(
                "active_expensive_run_count disagrees with ACTIVE attempts",
                supplied=supplied_active,
                derived=derived_active,
            )
        counts["active_expensive_run_count"] = derived_active

        supplied_mutation_owners = {owner for owner in OBJECTIVE_OWNERS if "mutations" in supplied_consumed[owner]}
        completed = counts.get("completed_mutation_count")
        if supplied_mutation_owners:
            derived_completed = origin_mutations + sum(objective_consumed[owner]["mutations"] for owner in OBJECTIVE_OWNERS)
            if completed not in (None, derived_completed):
                _count_conflict(
                    "completed_mutation_count disagrees with objective consumption",
                    supplied=completed,
                    derived=derived_completed,
                )
            counts["completed_mutation_count"] = derived_completed
        elif isinstance(completed, int):
            consumed = completed - origin_mutations
            if consumed < 0:
                raise GuardInputError(
                    "CAMPAIGN_ORIGIN_AHEAD_OF_COUNTERS",
                    "campaign mutation origin exceeds the completed counter",
                )
            if consumed:
                candidates = [owner for owner in OBJECTIVE_OWNERS if objective_limits[owner]["mutations"] >= consumed and objective_limits[owner]["mutations"] > 0]
                if len(candidates) != 1:
                    raise GuardInputError(
                        "CAMPAIGN_MUTATION_OWNER_AMBIGUOUS",
                        "mutation consumption cannot be assigned to exactly one objective",
                        candidate_owners=candidates,
                    )
                objective_consumed[candidates[0]]["mutations"] = consumed
        else:
            raise GuardInputError(
                "CAMPAIGN_MUTATION_COUNTER_REQUIRED",
                "campaign control requires completed mutation consumption or its global counter",
            )
    return {
        "envelope_identity": _identity(value.get("envelope_identity"), "campaign_control.envelope_identity"),
        "origin_identity": _identity(value.get("origin_identity"), "campaign_control.origin_identity"),
        "objective_scope_identity": _identity(
            value.get("objective_scope_identity"),
            "campaign_control.objective_scope_identity",
        ),
        "origin_completed_mutation_count": origin_mutations,
        "origin_expensive_start_count": origin_starts,
        "absolute_limits": absolute_limits,
        "objective_limits": objective_limits,
        "objective_consumed": objective_consumed,
        "attempt_records": records,
    }


def _control_limits(value: Any) -> dict[str, dict[str, int]]:
    if not isinstance(value, dict) or not set(value) <= set(OBJECTIVE_OWNERS):
        raise ValueError("control_economy.limits contains unknown objective owners")
    normalized: dict[str, dict[str, int]] = {}
    for owner in OBJECTIVE_OWNERS:
        raw = value.get(owner, {})
        if not isinstance(raw, dict) or not set(raw) <= set(CONTROL_COSTS):
            raise ValueError(f"control_economy.limits.{owner} contains unknown costs")
        normalized[owner] = {cost: _required_nonnegative(raw.get(cost, 0), f"limits.{owner}.{cost}") for cost in CONTROL_COSTS}
    return normalized


def _stage_audit(value: Any, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    fields = {
        "stage_identity",
        "boundary",
        "stage_generation_identity",
        "deliverable_identity",
        "audit_evidence_identity",
        "outcome",
        "predecessor_audit_decision_id",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{label} fields do not match schema V9")
    boundary = value.get("boundary")
    outcome = value.get("outcome")
    if boundary not in STAGE_BOUNDARIES or outcome not in STAGE_AUDIT_OUTCOMES:
        raise ValueError(f"{label} boundary or outcome is invalid")
    predecessor = _identity(
        value.get("predecessor_audit_decision_id"),
        f"{label}.predecessor_audit_decision_id",
        optional=True,
    )
    if (boundary == "DESIGN_COMPLETE") != (predecessor is None):
        raise GuardInputError(
            "STAGE_AUDIT_PREDECESSOR_INVALID",
            "design audit starts a stage lineage and build audit must cite its passed design audit",
        )
    return {
        "stage_identity": _identity(value.get("stage_identity"), f"{label}.stage_identity"),
        "boundary": boundary,
        "stage_generation_identity": _identity(
            value.get("stage_generation_identity"),
            f"{label}.stage_generation_identity",
        ),
        "deliverable_identity": _identity(value.get("deliverable_identity"), f"{label}.deliverable_identity"),
        "audit_evidence_identity": _identity(
            value.get("audit_evidence_identity"),
            f"{label}.audit_evidence_identity",
        ),
        "outcome": outcome,
        "predecessor_audit_decision_id": predecessor,
    }


def _stage_predecessor_matches(predecessor: dict[str, Any] | None, audit: dict[str, Any], owner: str, consumer: str) -> bool:
    predecessor_audit = (predecessor or {}).get("stage_audit")
    return bool(
        predecessor_audit
        and predecessor_audit["boundary"] == "DESIGN_COMPLETE"
        and predecessor_audit["outcome"] == "PASS"
        and predecessor_audit["stage_identity"] == audit["stage_identity"]
        and predecessor_audit["stage_generation_identity"]
        == audit["stage_generation_identity"]
        and predecessor["objective_owner"] == owner
        and predecessor["active_consumer_identity"] == consumer
    )


def _control_record(value: Any, index: int) -> dict[str, Any]:
    label = f"control_economy.records[{index}]"
    allowed = CONTROL_RECORD_FIELDS
    required = allowed - {"record_sha256", "stage_audit"}
    if not isinstance(value, dict) or not required <= set(value) or not set(value) <= allowed:
        raise ValueError(f"{label} fields do not match schema V9")
    owner = value.get("objective_owner")
    if owner not in OBJECTIVE_OWNERS:
        raise ValueError(f"{label}.objective_owner is invalid")
    costs = _strings(value.get("costs"), f"{label}.costs")
    if not costs or "DECISION" not in costs or not set(costs) <= set(CONTROL_COSTS):
        raise ValueError(f"{label}.costs must contain DECISION and only known costs")
    effect = value.get("effect")
    if effect not in CONTROL_EFFECTS:
        raise ValueError(f"{label}.effect is invalid")
    record = {
        "decision_id": _identity(value.get("decision_id"), f"{label}.decision_id"),
        "objective_owner": owner,
        "state_key_sha256": _sha256_identity(value.get("state_key_sha256"), f"{label}.state_key_sha256"),
        "decision_key_sha256": _sha256_identity(value.get("decision_key_sha256"), f"{label}.decision_key_sha256"),
        "action_class": _identity(value.get("action_class"), f"{label}.action_class"),
        "active_consumer_identity": _identity(value.get("active_consumer_identity"), f"{label}.active_consumer_identity"),
        "validator_identity": _identity(value.get("validator_identity"), f"{label}.validator_identity"),
        "authority_identity": _identity(value.get("authority_identity"), f"{label}.authority_identity"),
        "trust_boundary_identity": _identity(value.get("trust_boundary_identity"), f"{label}.trust_boundary_identity"),
        "protected_constraint_identity": _identity(
            value.get("protected_constraint_identity"),
            f"{label}.protected_constraint_identity",
            optional=True,
        ),
        "costs": costs,
        "effect": effect,
    }
    stage_audit = _stage_audit(value.get("stage_audit"), f"{label}.stage_audit")
    if stage_audit is not None:
        record["stage_audit"] = stage_audit
    record_sha256 = _digest(record)
    supplied = value.get("record_sha256")
    if supplied is not None and supplied != record_sha256:
        raise GuardInputError(
            "CONTROL_RECORD_HASH_MISMATCH",
            "control decision record hash is inconsistent",
            decision_id=record["decision_id"],
        )
    return {**record, "record_sha256": record_sha256}


def _active_frontier(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    fields = {
        "frontier_identity",
        "primary_objective_owner",
        "primary_state",
        "primary_generation_identity",
        "primary_consumer_identity",
        "primary_terminal_status",
        "recovery_state",
        "recovery_consumer_identity",
        "recovery_activation_reason",
        "recovery_activation_identity",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("control_economy.active_frontier fields do not match schema V9")
    primary_state = value.get("primary_state")
    recovery_state = value.get("recovery_state")
    if primary_state not in PRIMARY_STATES or recovery_state not in RECOVERY_STATES:
        raise ValueError("active frontier state is invalid")
    owner = value.get("primary_objective_owner")
    if owner not in OBJECTIVE_OWNERS:
        raise ValueError("active frontier objective owner is invalid")
    terminal = _identity(
        value.get("primary_terminal_status"),
        "active_frontier.primary_terminal_status",
        optional=True,
    )
    if (primary_state == "TERMINAL") != (terminal is not None) or (terminal is not None and terminal not in TERMINAL_STATUSES - {"NOT_APPLICABLE"}):
        raise ValueError("primary terminal status is inconsistent with TERMINAL state")
    for field in ("frontier_identity", "primary_generation_identity", "primary_consumer_identity"):
        _identity(value.get(field), f"active_frontier.{field}")
    for field in (
        "recovery_consumer_identity",
        "recovery_activation_reason",
        "recovery_activation_identity",
    ):
        _identity(value.get(field), f"active_frontier.{field}", optional=True)
    return dict(value)


def _finding(value: Any, index: int, frontier: dict[str, Any] | None) -> dict[str, Any]:
    label = f"control_economy.findings[{index}]"
    required = {
        "finding_id",
        "objective_owner",
        "claimed_tier",
        "reachability",
        "frontier_role",
        "decision_effect",
        "evidence_identity",
    }
    allowed = required | {"active_consumer_identity", "protected_constraint_identity", "p0_edge_identity"}
    if not isinstance(value, dict) or not required <= set(value) or not set(value) <= allowed:
        raise ValueError(f"{label} fields do not match schema V9")
    owner = value.get("objective_owner")
    tier = value.get("claimed_tier")
    reachability = value.get("reachability")
    role = value.get("frontier_role")
    if owner not in OBJECTIVE_OWNERS or tier not in FINDING_TIERS:
        raise ValueError(f"{label} owner or tier is invalid")
    if reachability not in FINDING_REACHABILITY or role not in {"PRIMARY", "RECOVERY"}:
        raise ValueError(f"{label} reachability or frontier role is invalid")
    effect = value.get("decision_effect")
    if effect not in CONTROL_EFFECTS | {"NONE"}:
        raise ValueError(f"{label}.decision_effect is invalid")
    consumer = _identity(value.get("active_consumer_identity"), f"{label}.active_consumer_identity", optional=True)
    protected = _identity(
        value.get("protected_constraint_identity"),
        f"{label}.protected_constraint_identity",
        optional=True,
    )
    p0_edge = _identity(value.get("p0_edge_identity"), f"{label}.p0_edge_identity", optional=True)
    effective = tier
    advisory_code: str | None = None
    primary_ready = bool(frontier and frontier["primary_state"] in {"READY", "RUNNING"})
    expected_consumer = (frontier or {}).get("primary_consumer_identity" if role == "PRIMARY" else "recovery_consumer_identity")
    if tier in {"HARD_FAIL", "REVIEW_REQUIRED"}:
        if reachability == "UNREACHABLE" or not (consumer or protected) or (frontier and consumer and consumer != expected_consumer) or effect == "NONE":
            effective, advisory_code = "WARNING", "GATE_NO_ACTIVE_CONSUMER_DOWNGRADED"
        elif reachability == "UNKNOWN" and protected is None:
            effective, advisory_code = "WARNING", "GATE_NO_ACTIVE_CONSUMER_DOWNGRADED"
        elif role == "RECOVERY" and primary_ready and frontier["recovery_state"] == "DORMANT":
            effective, advisory_code = "WARNING", "DORMANT_RECOVERY_BLOCK_IGNORED"
        elif frontier and frontier["primary_objective_owner"] == "P0" and owner != "P0" and not (p0_edge or protected):
            effective, advisory_code = "WARNING", "GATE_NO_ACTIVE_CONSUMER_DOWNGRADED"
    return {
        "finding_id": _identity(value.get("finding_id"), f"{label}.finding_id"),
        "objective_owner": owner,
        "claimed_tier": tier,
        "effective_tier": effective,
        "reachability": reachability,
        "frontier_role": role,
        "decision_effect": effect,
        "evidence_identity": _identity(value.get("evidence_identity"), f"{label}.evidence_identity"),
        "active_consumer_identity": consumer,
        "protected_constraint_identity": protected,
        "p0_edge_identity": p0_edge,
        "advisory_code": advisory_code,
    }


def _finding_projections(findings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blockers = [finding for finding in findings if finding["effective_tier"] in {"HARD_FAIL", "REVIEW_REQUIRED"}]
    advisories = [
        {"code": finding["advisory_code"] or "ADVISORY_FINDING", "finding_id": finding["finding_id"], "effective_tier": finding["effective_tier"]}
        for finding in findings
        if finding["effective_tier"] in {"WARNING", "INFO"}
    ]
    return blockers, advisories


def _classification_set(value: Any, index: int) -> dict[str, Any]:
    label = f"control_economy.classification_sets[{index}]"
    fields = {
        "classification_id",
        "structural_rule_identity",
        "production_mechanism_identity",
        "producer_identity",
        "execution_purpose_identity",
        "trust_route_identity",
        "classifier_identity",
        "denominator_identity",
        "denominator_kind",
        "denominator_count",
        "disposition_counts",
        "active_consumer_closure_identity",
        "terminal_evidence_identity",
        "complete",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{label} fields do not match schema V9")
    counts = value.get("disposition_counts")
    tiers = ("HARD_FAIL", "REVIEW_REQUIRED", "WARNING", "INFO")
    if not isinstance(counts, dict) or not set(counts) <= set(tiers):
        raise ValueError(f"{label}.disposition_counts is invalid")
    normalized_counts = {tier: _required_nonnegative(counts.get(tier, 0), f"{label}.{tier}") for tier in tiers}
    denominator = _required_nonnegative(value.get("denominator_count"), f"{label}.denominator_count")
    if (
        value.get("denominator_kind") != "IMMUTABLE_FINITE"
        or value.get("complete") is not True
        or not value.get("terminal_evidence_identity")
        or sum(normalized_counts.values()) != denominator
    ):
        raise GuardInputError(
            "CLASSIFICATION_SET_INCOMPLETE",
            "classification set must be finite, complete, terminal, and count-conserving",
            classification_id=value.get("classification_id"),
        )
    identities = {field: _identity(value.get(field), f"{label}.{field}") for field in fields if field.endswith("_identity")}
    return {
        "classification_id": _identity(value.get("classification_id"), f"{label}.classification_id"),
        **identities,
        "denominator_kind": "IMMUTABLE_FINITE",
        "denominator_count": denominator,
        "disposition_counts": normalized_counts,
        "complete": True,
    }


def _surface_budget(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    fields = {*SURFACE_FIELDS, "control_surface_identity"}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("control_economy.surface_budget fields do not match schema V9")
    normalized = {field: _tokens(field, _strings(value.get(field), f"surface_budget.{field}")) for field in SURFACE_FIELDS}
    return {
        **normalized,
        "control_surface_identity": _identity(value.get("control_surface_identity"), "surface_budget.control_surface_identity"),
    }


def _surface_growth(before: dict[str, Any] | None, after: dict[str, Any]) -> dict[str, int]:
    return {field: count for field in SURFACE_FIELDS if (count := len(set(after[field]) - set((before or {}).get(field, []))))}


def _normalize_control_economy(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    required = CONTROL_ECONOMY_FIELDS - {
        "decision_request",
        "active_frontier",
        "findings",
        "classification_sets",
        "surface_budget",
    }
    if not isinstance(value, dict) or not required <= set(value) or not set(value) <= CONTROL_ECONOMY_FIELDS:
        raise ValueError("control_economy fields do not match schema V9")
    records = [_control_record(record, index) for index, record in enumerate(value["records"])]
    ids = [record["decision_id"] for record in records]
    keys = [record["decision_key_sha256"] for record in records]
    if len(ids) != len(set(ids)) or len(keys) != len(set(keys)):
        raise GuardInputError("CONTROL_DECISION_KEY_REUSED", "control decision records contain duplicate identity or key")
    frontier = _active_frontier(value.get("active_frontier"))
    findings = [_finding(finding, index, frontier) for index, finding in enumerate(value.get("findings", []))]
    finding_ids = [finding["finding_id"] for finding in findings]
    if len(finding_ids) != len(set(finding_ids)):
        raise ValueError("control_economy.findings contains duplicate finding_id")
    classifications = [_classification_set(item, index) for index, item in enumerate(value.get("classification_sets", []))]
    class_ids = [item["classification_id"] for item in classifications]
    if len(class_ids) != len(set(class_ids)):
        raise ValueError("control_economy.classification_sets contains duplicate identity")
    class_keys = {
        tuple(
            item[field]
            for field in (
                "structural_rule_identity",
                "production_mechanism_identity",
                "producer_identity",
                "execution_purpose_identity",
                "trust_route_identity",
                "classifier_identity",
                "denominator_identity",
            )
        )
        for item in classifications
    }
    if len(class_keys) != len(classifications):
        raise GuardInputError("CLASSIFICATION_SET_DRIFT", "one finite denominator has duplicate classification identities")
    request = value.get("decision_request")
    if request is not None:
        required_request = {
            "objective_owner",
            "action_class",
            "active_consumer_identity",
            "validator_identity",
            "authority_identity",
            "trust_boundary_identity",
            "protected_constraint_identity",
            "costs",
            "effect",
            "reuse_decision_id",
        }
        allowed_request = required_request | {"stage_audit"}
        if not isinstance(request, dict) or not required_request <= set(request) or not set(request) <= allowed_request:
            raise ValueError("decision_request fields do not match V9")
        if request.get("objective_owner") not in OBJECTIVE_OWNERS:
            raise ValueError("decision_request objective owner is invalid")
        costs = _strings(request.get("costs"), "decision_request.costs")
        if not set(costs) <= set(CONTROL_COSTS) - {"DECISION"}:
            raise ValueError("decision_request contains unknown or explicit DECISION cost")
        if request.get("effect") not in CONTROL_EFFECTS:
            raise GuardInputError(
                "STOP_NO_JUSTIFIED_CONTROL_ACTION",
                "decision_request.effect is not allowed",
            )
        stage_audit = _stage_audit(
            request.get("stage_audit"),
            "decision_request.stage_audit",
        )
        request = {
            "objective_owner": request["objective_owner"],
            "action_class": _identity(request.get("action_class"), "decision_request.action_class"),
            "active_consumer_identity": _identity(request.get("active_consumer_identity"), "decision_request.active_consumer_identity"),
            "validator_identity": _identity(request.get("validator_identity"), "decision_request.validator_identity"),
            "authority_identity": _identity(request.get("authority_identity"), "decision_request.authority_identity"),
            "trust_boundary_identity": _identity(request.get("trust_boundary_identity"), "decision_request.trust_boundary_identity"),
            "protected_constraint_identity": _identity(
                request.get("protected_constraint_identity"),
                "decision_request.protected_constraint_identity",
                optional=True,
            ),
            "costs": costs,
            "effect": request["effect"],
            "reuse_decision_id": _identity(request.get("reuse_decision_id"), "decision_request.reuse_decision_id", optional=True),
        }
        if stage_audit is not None:
            request["stage_audit"] = stage_audit
    return {
        "envelope_identity": _identity(value.get("envelope_identity"), "control_economy.envelope_identity"),
        "origin_identity": _identity(value.get("origin_identity"), "control_economy.origin_identity"),
        "objective_scope_identity": _identity(value.get("objective_scope_identity"), "control_economy.objective_scope_identity"),
        "stop_point_identity": _identity(value.get("stop_point_identity"), "control_economy.stop_point_identity"),
        "limits": _control_limits(value.get("limits")),
        "records": records,
        "decision_request": request,
        "active_frontier": frontier,
        "findings": findings,
        "classification_sets": classifications,
        "surface_budget": _surface_budget(value.get("surface_budget")),
    }


def _control_state_key(facts: dict[str, Any], repo: dict[str, Any] | None, control: dict[str, Any]) -> str:
    campaign = facts.get("campaign_control") or {}
    frontier = control.get("active_frontier") or {}
    return _digest(
        {
            "project_token": facts.get("project_token"),
            "campaign_token": facts.get("campaign_token"),
            "change_generation": facts.get("change_generation"),
            "head": (repo or {}).get("head"),
            "repository_state": (repo or {}).get("changed_paths_sha256"),
            "changed_paths": (repo or {}).get("changed_path_tokens", []),
            "allowed_paths": (repo or {}).get("allowed_path_tokens", []),
            "changed_objects": facts.get("changed_object_ids", []),
            "allowed_objects": facts.get("allowed_object_ids", []),
            "protected_content_identity": facts.get("protected_content_identity"),
            "objective_scope_identity": control["objective_scope_identity"],
            "stop_point_identity": control["stop_point_identity"],
            "campaign_envelope_identity": campaign.get("envelope_identity"),
            "primary_frontier_identity": frontier.get("frontier_identity"),
            "primary_generation_identity": frontier.get("primary_generation_identity"),
            "authority_revision_identity": facts.get("authority_revision_identity"),
            "validator_identity": facts.get("validation_evidence_identity"),
        }
    )


def _validate_stage_audit_request(request: dict[str, Any], control: dict[str, Any]) -> None:
    audit = request.get("stage_audit")
    if audit is None:
        if request["action_class"] in set(STAGE_ACTIONS.values()):
            raise GuardInputError(
                "STAGE_AUDIT_REQUIRED",
                "a material stage-boundary action requires one current stage audit",
            )
        return
    if request["action_class"] != STAGE_ACTIONS[audit["boundary"]]:
        raise GuardInputError(
            "STAGE_AUDIT_CONTEXT_MISMATCH",
            "stage audit boundary and action class disagree",
        )
    frontier = control.get("active_frontier")
    if not frontier:
        raise GuardInputError(
            "STAGE_AUDIT_CONTEXT_MISMATCH",
            "stage audit requires the current primary frontier",
        )
    if (
        audit["stage_identity"] != frontier["frontier_identity"]
        or audit["stage_generation_identity"] != frontier["primary_generation_identity"]
        or request["objective_owner"] != frontier["primary_objective_owner"]
        or request["active_consumer_identity"] != frontier["primary_consumer_identity"]
    ):
        raise GuardInputError(
            "STAGE_AUDIT_CONTEXT_MISMATCH",
            "stage audit is stale or bound to another objective, generation, or consumer",
        )
    if audit["boundary"] == "BUILD_COMPLETE":
        predecessor = next(
            (
                record
                for record in control["records"]
                if record["decision_id"] == audit["predecessor_audit_decision_id"]
            ),
            None,
        )
        if not _stage_predecessor_matches(
            predecessor,
            audit,
            request["objective_owner"],
            request["active_consumer_identity"],
        ):
            raise GuardInputError(
                "STAGE_AUDIT_PREDECESSOR_INVALID",
                "build audit must cite the passed design audit for this exact stage, objective, generation, and consumer",
            )


def _finalize_control_economy(
    facts: dict[str, Any],
    repo: dict[str, Any] | None,
    *,
    legacy_control_event_count: int = 0,
) -> dict[str, Any]:
    control = facts.get("control_economy")
    if control is None:
        return facts
    control = dict(control)
    records = list(control["records"])
    request = control.pop("decision_request")
    active_decision_id: str | None = None
    disposition = "NO_DECISION_REQUEST"
    if request is not None:
        _validate_stage_audit_request(request, control)
        state_key = _control_state_key(facts, repo, control)
        semantic = {
            "state_key_sha256": state_key,
            "objective_owner": request["objective_owner"],
            "action_class": request["action_class"],
            "active_consumer_identity": request["active_consumer_identity"],
            "validator_identity": request["validator_identity"],
            "authority_identity": request["authority_identity"],
            "trust_boundary_identity": request["trust_boundary_identity"],
            "protected_constraint_identity": request["protected_constraint_identity"],
            "effect": request["effect"],
        }
        if request.get("stage_audit") is not None:
            semantic["stage_audit"] = request["stage_audit"]
        key_semantic = dict(semantic)
        if "stage_audit" in key_semantic:
            key_semantic["stage_audit"] = {
                key: value
                for key, value in key_semantic["stage_audit"].items()
                if key != "outcome"
            }
        decision_key = _digest(key_semantic)
        existing_scope = next(
            (
                record
                for record in records
                if all(
                    record.get(key) == value
                    for key, value in semantic.items()
                    if key not in {"effect", "stage_audit"}
                )
                and (
                    "stage_audit" not in semantic
                    or {
                        key: value
                        for key, value in (record.get("stage_audit") or {}).items()
                        if key != "outcome"
                    }
                    == key_semantic["stage_audit"]
                )
            ),
            None,
        )
        by_id = {record["decision_id"]: record for record in records}
        reuse_id = request["reuse_decision_id"]
        if reuse_id is not None:
            existing = by_id.get(reuse_id)
            if (
                existing is None
                or existing["decision_key_sha256"] != decision_key
                or (existing.get("stage_audit") or {}).get("outcome")
                != (request.get("stage_audit") or {}).get("outcome")
            ):
                raise GuardInputError(
                    "CONTROL_DECISION_REUSE_INVALID",
                    "reuse_decision_id does not bind this exact decision",
                    reuse_decision_id=reuse_id,
                )
            active_decision_id = reuse_id
            disposition = "REUSE_EXISTING_DECISION"
        elif existing_scope is not None:
            raise GuardInputError(
                "CONTROL_DECISION_KEY_REUSED",
                "exact decision key is reusable",
                reused_decision_id=existing_scope["decision_id"],
            )
        else:
            payload = {
                "decision_id": f"DECISION-{decision_key}",
                **semantic,
                "decision_key_sha256": decision_key,
                "costs": sorted({"DECISION", *request["costs"]}),
            }
            record = {**payload, "record_sha256": _digest(payload)}
            records.append(record)
            active_decision_id = record["decision_id"]
            disposition = "NEW_DECISION_RECORD"

    consumed = {owner: {cost: sum(record["objective_owner"] == owner and cost in record["costs"] for record in records) for cost in CONTROL_COSTS} for owner in OBJECTIVE_OWNERS}
    remaining = {owner: {cost: control["limits"][owner][cost] - consumed[owner][cost] for cost in CONTROL_COSTS} for owner in OBJECTIVE_OWNERS}
    findings = control["findings"]
    blockers, _ = _finding_projections(findings)
    normalized = {
        **control,
        "records": records,
        "legacy_control_event_count": legacy_control_event_count,
        "consumed": consumed,
        "remaining": remaining,
        "active_decision_id": active_decision_id,
        "decision_disposition": disposition,
    }
    capabilities = set(facts["capabilities"]) | {"control_economy", "control_events"}
    blocker_ids = facts["blocker_ids"]
    if findings:
        derived_blockers = _tokens("blocker", [finding["finding_id"] for finding in blockers])
        if blocker_ids and blocker_ids != derived_blockers:
            _count_conflict("blocker_ids disagree with effective V9 findings")
        blocker_ids = derived_blockers
        if blocker_ids:
            capabilities.add("blockers")
        elif not facts["blocker_ids"]:
            capabilities.discard("blockers")
    return {
        **facts,
        "blocker_ids": blocker_ids,
        "blocker_count": len(blocker_ids),
        "control_event_count": legacy_control_event_count + len(records),
        "control_economy": normalized,
        "capabilities": sorted(capabilities),
    }


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("closure facts must be a JSON object")
    machine_fields = sorted(set(raw) & MACHINE_FACT_FIELDS)
    if machine_fields:
        raise GuardInputError(
            "MACHINE_FACT_OVERRIDE_PROHIBITED",
            "repository, lineage, and activation facts are captured by the guard",
            fields=machine_fields,
        )
    if "control_event_count" in raw:
        raise GuardInputError(
            "MACHINE_COUNT_OVERRIDE_PROHIBITED",
            "control_event_count is derived from the V9 decision record chain",
            fields=["control_event_count"],
        )
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

    raw_ids = {field: _strings(raw.get(field), field) for field in LIST_FIELDS[:-1]}
    ids = {
        field: _tokens(
            "object" if field in {"changed_object_ids", "allowed_object_ids"} else "closure_item" if field in {"closure_item_ids", "open_item_ids"} else field,
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
                _count_conflict(
                    f"{count_field} disagrees with {id_field}",
                    count_field=count_field,
                    id_field=id_field,
                    supplied=counts[count_field],
                    derived=size,
                )
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
            _count_conflict(
                "closure_item_count disagrees with open and closed counts",
                supplied=closure_count,
                derived=open_count + closed_count,
            )
    elif isinstance(closure_count, int) and isinstance(open_count, int) and closed_count is None:
        counts["closed_item_count"] = closure_count - open_count
        if counts["closed_item_count"] < 0:
            _count_conflict("open_item_count exceeds closure_item_count")

    campaign_control = _normalize_campaign_control(raw.get("campaign_control"), counts)
    control_economy = _normalize_control_economy(raw.get("control_economy"))
    planned = counts["planned_mutation_count"]
    completed = counts["completed_mutation_count"]
    remaining = counts["remaining_mutation_count"]
    if isinstance(planned, int) and isinstance(completed, int):
        if completed > planned:
            _count_conflict("completed_mutation_count exceeds planned_mutation_count")
        expected_remaining = planned - completed
        if remaining not in (None, expected_remaining):
            _count_conflict(
                "remaining_mutation_count disagrees with planned/completed counts",
                supplied=remaining,
                derived=expected_remaining,
            )
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
        discovered, executed, passed, failed, errors, skipped, xfail, xpass = (counts[field] for field in validation_fields)
        if discovered != executed + skipped:
            _count_conflict("validation_discovered_count disagrees with executed and skipped counts")
        if executed != passed + failed + errors + xfail + xpass:
            _count_conflict("validation_executed_count disagrees with result counts")
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
    if any(value is not None for value in run_state_values) and any(value is None for value in run_state_values):
        raise ValueError("run-state integrity facts must be supplied as one exact set")

    capabilities = set(_strings(raw.get("capabilities"), "capabilities"))
    inference = {
        "campaign_lineage": raw.get("campaign_id") is not None or raw.get("rescue_deadline_at") is not None,
        "campaign_control": campaign_control is not None,
        "control_economy": control_economy is not None,
        "closure_items": counts["closure_item_count"] is not None or counts["open_item_count"] is not None or counts["closed_item_count"] is not None,
        "blockers": bool(ids["blocker_ids"]),
        "mutations": counts["planned_mutation_count"] is not None or counts["completed_mutation_count"] is not None or counts["remaining_mutation_count"] is not None,
        "validation_ladder": counts["validation_rank"] is not None,
        "validation_execution": any(counts[field] is not None for field in validation_fields)
        or raw.get("validation_evidence_identity") is not None
        or raw.get("validation_outer_terminal_status") is not None,
        "control_events": control_economy is not None,
        "delegation": bool(ids["delegated_task_ids"])
        or counts["delegated_task_count"] is not None
        or counts["subagent_spawn_count"] is not None
        or counts["active_subagent_count"] is not None
        or counts["active_subagent_mutator_count"] is not None
        or counts["active_subagent_expensive_run_count"] is not None
        or counts["recursive_delegation_count"] is not None,
        "mutators": counts["active_mutator_count"] is not None,
        "expensive_operations": counts["active_expensive_run_count"] is not None or counts["expensive_start_count"] is not None,
        "final_boundary": counts["final_boundary_start_count"] is not None,
        "authority": raw.get("authority_status") is not None
        or counts["authority_revision_count"] is not None
        or raw.get("authority_revision_identity") is not None
        or raw.get("independent_authority_review_required") is True,
        "object_scope": bool(ids["changed_object_ids"]) or bool(ids["allowed_object_ids"]) or raw.get("protected_content_identity") is not None,
        "writer_proof": raw.get("writer_free") is not None or raw.get("writer_proof_identity") is not None,
        "boundary_smoke": smoke_status is not None or raw.get("boundary_smoke_identity") is not None,
        "run_state": any(value is not None for value in run_state_values),
        "waivers": bool(ids["waiver_ids"]) or raw.get("waiver_scope_identity") is not None,
    }
    empty_shells = capabilities - {name for name, present in inference.items() if present} - {"blockers", "validation_execution", "vcs"}
    if empty_shells:
        raise ValueError(f"capability shell lacks applicable facts: {sorted(empty_shells)}")
    capabilities.update(name for name, present in inference.items() if present)
    unknown_caps = capabilities - CAPABILITIES
    if unknown_caps:
        raise ValueError(f"unknown capabilities: {sorted(unknown_caps)}")
    delegated_count = counts["delegated_task_count"]
    subagent_spawns = counts["subagent_spawn_count"]
    active_subagents = counts["active_subagent_count"]
    if isinstance(delegated_count, int):
        if isinstance(subagent_spawns, int) and subagent_spawns > delegated_count:
            _count_conflict("subagent_spawn_count exceeds delegated_task_count")
        if isinstance(active_subagents, int) and active_subagents > delegated_count:
            _count_conflict("active_subagent_count exceeds delegated_task_count")
    if "object_scope" in capabilities and raw.get("protected_content_identity") is None:
        raise ValueError("object_scope requires protected_content_identity")
    if "writer_proof" in capabilities and raw.get("writer_free") is None:
        raise ValueError("writer_proof requires writer_free")
    if "boundary_smoke" in capabilities and smoke_status is None:
        raise ValueError("boundary_smoke requires boundary_smoke_status")
    if "authority" in capabilities and authority_status is None:
        raise ValueError("authority capability requires authority_status")
    if "campaign_control" in capabilities and campaign_control is None:
        raise ValueError("campaign_control capability requires campaign_control facts")
    if "control_economy" in capabilities and control_economy is None:
        raise ValueError("control_economy capability requires control_economy facts")
    if authority_status in {"APPROVED", "ACTIVATED", "REJECTED"} and raw.get("authority_revision_identity") is None:
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
        "independent_authority_review_required": raw.get("independent_authority_review_required", False),
        "writer_free": raw.get("writer_free"),
        "run_state_replay_verified": raw.get("run_state_replay_verified"),
        "run_state_projection_matches_replay": raw.get("run_state_projection_matches_replay"),
        "campaign_control": campaign_control,
        "control_economy": control_economy,
        "capabilities": sorted(capabilities),
    }


def _load(value: str) -> dict[str, Any]:
    text = sys.stdin.read() if value == "-" else Path(value).read_text(encoding="utf-8")
    return _strict_json_text(text, "guard JSON input")


def _validate_control_economy_snapshot(control: Any, label: str) -> None:
    fields = (CONTROL_ECONOMY_FIELDS - {"decision_request"}) | {
        "legacy_control_event_count",
        "consumed",
        "remaining",
        "active_decision_id",
        "decision_disposition",
    }
    if not isinstance(control, dict) or set(control) != fields:
        raise ValueError(f"{label} control_economy is malformed")
    for field in (
        "envelope_identity",
        "origin_identity",
        "objective_scope_identity",
        "stop_point_identity",
    ):
        _identity(control.get(field), f"{label}.{field}")
    if control.get("limits") != _control_limits(control.get("limits")):
        raise ValueError(f"{label} control limits are not canonical")
    records = [_control_record(record, index) for index, record in enumerate(control["records"])]
    if records != control["records"]:
        raise ValueError(f"{label} control records are not canonical")
    if len({record["decision_id"] for record in records}) != len(records) or len({record["decision_key_sha256"] for record in records}) != len(records):
        raise ValueError(f"{label} control records are not unique")
    prior_records: dict[str, dict[str, Any]] = {}
    for record in records:
        audit = record.get("stage_audit")
        if audit is not None:
            if record["action_class"] != STAGE_ACTIONS[audit["boundary"]]:
                raise ValueError(f"{label} stage audit action is not canonical")
            predecessor = prior_records.get(audit["predecessor_audit_decision_id"])
            if audit["boundary"] == "BUILD_COMPLETE" and not _stage_predecessor_matches(
                predecessor,
                audit,
                record["objective_owner"],
                record["active_consumer_identity"],
            ):
                raise ValueError(f"{label} stage audit predecessor is not canonical")
        prior_records[record["decision_id"]] = record
    _required_nonnegative(control.get("legacy_control_event_count"), f"{label}.legacy_control_event_count")
    expected_consumed = {
        owner: {cost: sum(record["objective_owner"] == owner and cost in record["costs"] for record in records) for cost in CONTROL_COSTS} for owner in OBJECTIVE_OWNERS
    }
    expected_remaining = {owner: {cost: control["limits"][owner][cost] - expected_consumed[owner][cost] for cost in CONTROL_COSTS} for owner in OBJECTIVE_OWNERS}
    if control.get("consumed") != expected_consumed or control.get("remaining") != expected_remaining:
        raise ValueError(f"{label} control budget arithmetic is inconsistent")
    if control.get("active_decision_id") is not None and control["active_decision_id"] not in {record["decision_id"] for record in records}:
        raise ValueError(f"{label} active decision is absent from history")
    if control.get("decision_disposition") not in {
        "NO_DECISION_REQUEST",
        "NEW_DECISION_RECORD",
        "REUSE_EXISTING_DECISION",
    }:
        raise ValueError(f"{label} decision disposition is invalid")


def _validate_v7_snapshot(snapshot: Any, label: str) -> dict[str, Any]:
    if not isinstance(snapshot, dict) or set(snapshot) != set("schema_id profile mode repo facts lineage snapshot_sha256".split()):
        raise ValueError(f"{label} is not a V7 snapshot")
    if snapshot.get("schema_id") != V7_SCHEMA_ID:
        raise ValueError(f"{label} is not a V7 predecessor")
    payload = {key: value for key, value in snapshot.items() if key != "snapshot_sha256"}
    if snapshot.get("snapshot_sha256") != _digest(payload):
        raise ValueError(f"{label} V7 snapshot hash mismatch")
    if snapshot.get("profile") not in {"git", "generic"} or snapshot.get("mode") not in MODES:
        raise ValueError(f"{label} V7 profile or mode is invalid")
    facts = snapshot.get("facts")
    lineage = snapshot.get("lineage")
    if not isinstance(facts, dict) or not isinstance(lineage, dict):
        raise ValueError(f"{label} V7 facts or lineage are malformed")
    if set(lineage) != {"campaign_token", "parent_snapshot_sha256", "accepted_rebaseline_count"}:
        raise ValueError(f"{label} V7 lineage is malformed")
    if facts.get("campaign_control") is not None and _normalize_campaign_control(facts["campaign_control"]) != facts["campaign_control"]:
        raise ValueError(f"{label} V7 campaign control is not canonical")
    for field in "completed_mutation_count expensive_start_count control_event_count authority_revision_count run_state_terminal_count".split():
        value = facts.get(field)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ValueError(f"{label} V7 history counter is malformed: {field}")
    return snapshot


def _validate_snapshot(snapshot: Any, label: str, expected_schema: str = SCHEMA_ID) -> dict[str, Any]:
    """Validate a canonical V8/V9 snapshot; capture owns derived projections."""
    top = {"schema_id", "profile", "mode", "repo", "facts", "lineage", "snapshot_sha256"}
    if not isinstance(snapshot, dict) or set(snapshot) != top:
        raise ValueError(f"{label} fields do not match {expected_schema}")
    if snapshot["schema_id"] != expected_schema:
        raise ValueError(f"{label} schema is incompatible; capture or import a V9 baseline")
    if snapshot["profile"] not in {"git", "generic"} or snapshot["mode"] not in MODES:
        raise ValueError(f"{label} profile or mode is invalid")
    facts = snapshot["facts"]
    fact_fields = (
        set(LIST_FIELDS[:-1])
        | set(INT_FIELDS)
        | set(
            """project_token campaign_token change_generation blocker_count validation_level validation_evidence_identity
        validation_outer_terminal_status authority_status authority_revision_identity protected_content_identity
        writer_proof_identity boundary_smoke_identity boundary_smoke_status run_state_head_identity waiver_scope_identity
        rescue_deadline_at independent_authority_review_required writer_free run_state_replay_verified
        run_state_projection_matches_replay campaign_control control_economy capabilities""".split()
        )
    )
    if not isinstance(facts, dict) or set(facts) != fact_fields:
        raise ValueError(f"{label} facts are malformed")
    capabilities = facts["capabilities"]
    if not isinstance(capabilities, list) or capabilities != sorted(set(capabilities)) or not set(capabilities) <= CAPABILITIES:
        raise ValueError(f"{label} capabilities are malformed")
    for field in LIST_FIELDS[:-1]:
        values = facts[field]
        if not isinstance(values, list) or values != sorted(set(values)):
            raise ValueError(f"{label} {field} is malformed")
        for value in values:
            _sha256_identity(value, f"{label}.{field}")
    for field in INT_FIELDS + ("blocker_count",):
        value = facts[field]
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ValueError(f"{label} {field} is malformed")
    for field in ("project_token", "campaign_token"):
        if facts[field] is not None:
            _sha256_identity(facts[field], f"{label}.{field}")
    if not isinstance(facts["independent_authority_review_required"], bool):
        raise ValueError(f"{label} authority-review fact is malformed")
    for field in ("writer_free", "run_state_replay_verified", "run_state_projection_matches_replay"):
        if facts[field] is not None and not isinstance(facts[field], bool):
            raise ValueError(f"{label} {field} is malformed")
    if facts["authority_status"] not in AUTHORITY_STATUSES | {None}:
        raise ValueError(f"{label} authority status is invalid")
    if facts["boundary_smoke_status"] not in BOUNDARY_SMOKE_STATUSES | {None}:
        raise ValueError(f"{label} boundary smoke status is invalid")
    if facts["validation_outer_terminal_status"] not in TERMINAL_STATUSES | {None}:
        raise ValueError(f"{label} validation terminal status is invalid")
    for field in TEXT_FIELDS[3:]:
        value = facts.get(field)
        if value is not None and (not isinstance(value, str) or not value):
            raise ValueError(f"{label} {field} is malformed")
    if _normalize_campaign_control(facts["campaign_control"]) != facts["campaign_control"]:
        raise ValueError(f"{label} campaign_control is not canonical")
    if facts["control_economy"] is not None:
        _validate_control_economy_snapshot(facts["control_economy"], label)
        if expected_schema == V8_SCHEMA_ID and any(
            "stage_audit" in record
            for record in facts["control_economy"]["records"]
        ):
            raise ValueError(f"{label} V8 record contains a V9 field")
        expected_events = facts["control_economy"]["legacy_control_event_count"] + len(facts["control_economy"]["records"])
        if facts["control_event_count"] != expected_events:
            raise ValueError(f"{label} derived control_event_count is inconsistent")
    closure, opened, closed = (facts["closure_item_count"], facts["open_item_count"], facts["closed_item_count"])
    if all(isinstance(value, int) for value in (closure, opened, closed)) and closure != opened + closed:
        raise ValueError(f"{label} closure counts are inconsistent")
    if not set(facts["open_item_ids"]) <= set(facts["closure_item_ids"]):
        raise ValueError(f"{label} open-item identities exceed closure identities")
    planned, completed, remaining = (
        facts["planned_mutation_count"],
        facts["completed_mutation_count"],
        facts["remaining_mutation_count"],
    )
    if all(isinstance(value, int) for value in (planned, completed, remaining)) and (completed > planned or remaining != planned - completed):
        raise ValueError(f"{label} mutation counts are inconsistent")
    validation = [facts[field] for field in INT_FIELDS[7:15]]
    if any(value is not None for value in validation):
        if any(value is None for value in validation):
            raise ValueError(f"{label} validation counts are incomplete")
        discovered, executed, passed, failed, errors, skipped, xfail, xpass = validation
        if discovered != executed + skipped or executed != passed + failed + errors + xfail + xpass:
            raise ValueError(f"{label} validation counts are inconsistent")
        if not facts["validation_evidence_identity"] or not facts["validation_outer_terminal_status"]:
            raise ValueError(f"{label} validation evidence is incomplete")
    if facts["blocker_count"] != len(facts["blocker_ids"]):
        raise ValueError(f"{label} blocker count is inconsistent")
    for ids, count in (
        ("closure_item_ids", "closure_item_count"),
        ("open_item_ids", "open_item_count"),
        ("delegated_task_ids", "delegated_task_count"),
    ):
        if facts[ids] and facts[count] != len(facts[ids]):
            raise ValueError(f"{label} {count} disagrees with {ids}")
    if "campaign_control" in capabilities and facts["campaign_control"] is None:
        raise ValueError(f"{label} campaign_control capability lacks facts")
    if "control_economy" in capabilities and facts["control_economy"] is None:
        raise ValueError(f"{label} control_economy capability lacks facts")
    if "object_scope" in capabilities and not facts["protected_content_identity"]:
        raise ValueError(f"{label} object scope lacks protected-content identity")
    if "writer_proof" in capabilities and (facts["writer_free"] is None or not facts["writer_proof_identity"]):
        raise ValueError(f"{label} writer proof is incomplete")
    if "boundary_smoke" in capabilities and facts["boundary_smoke_status"] is None:
        raise ValueError(f"{label} boundary-smoke capability lacks status")
    repo = snapshot["repo"]
    if repo is not None:
        repo_fields = set(
            "repo_token head tracked_changed_count untracked_count tracked_path_tokens untracked_path_tokens changed_path_tokens allowed_path_tokens allowed_path_count dirty_records changed_paths_sha256".split()
        )
        if not isinstance(repo, dict) or set(repo) != repo_fields:
            raise ValueError(f"{label} repository facts are malformed")
        for field in ("tracked_path_tokens", "untracked_path_tokens", "changed_path_tokens", "allowed_path_tokens"):
            values = repo[field]
            if not isinstance(values, list) or values != sorted(set(values)):
                raise ValueError(f"{label} repository token list is malformed")
            for value in values:
                _sha256_identity(value, f"{label}.{field}")
        for field in ("repo_token", "changed_paths_sha256"):
            _sha256_identity(repo[field], f"{label}.{field}")
        dirty_records = repo["dirty_records"]
        if not isinstance(dirty_records, dict) or any(
            not _is_sha256(token)
            or not isinstance(record, list)
            or len(record) != 8
            or not all(isinstance(item, int) and not isinstance(item, bool) for item in record[:7])
            or not _is_sha256(record[-1])
            for token, record in dirty_records.items()
        ):
            raise ValueError(f"{label} repository dirty records are malformed")
        if (
            repo["tracked_changed_count"] != len(repo["tracked_path_tokens"])
            or repo["untracked_count"] != len(repo["untracked_path_tokens"])
            or repo["allowed_path_count"] != len(repo["allowed_path_tokens"])
            or len(dirty_records) != repo["tracked_changed_count"] + repo["untracked_count"]
            or not set(dirty_records) <= set(repo["changed_path_tokens"])
        ):
            raise ValueError(f"{label} repository counts are inconsistent")
    if "vcs" in capabilities and repo is None:
        raise ValueError(f"{label} vcs capability lacks repository facts")
    for capability, required_fields in CAPABILITY_REQUIRED_FACTS.items():
        if capability in capabilities:
            missing = [field for field in required_fields if facts[field] is None]
            if missing:
                raise ValueError(f"{label} capability facts are incomplete for {capability}: {missing}")
    lineage = snapshot["lineage"]
    lineage_fields = set("campaign_token parent_snapshot_sha256 accepted_rebaseline_count schema_upgrade_from schema_upgrade_parent_snapshot_sha256 schema_upgrade_count".split())
    if not isinstance(lineage, dict) or set(lineage) != lineage_fields:
        raise ValueError(f"{label} lineage is malformed")
    _sha256_identity(lineage["campaign_token"], f"{label}.campaign_token")
    if lineage["parent_snapshot_sha256"] is not None:
        _sha256_identity(lineage["parent_snapshot_sha256"], f"{label}.parent")
    max_upgrade_count = 1 if expected_schema == V8_SCHEMA_ID else 2
    if (
        lineage["accepted_rebaseline_count"] not in {0, 1}
        or isinstance(lineage["schema_upgrade_count"], bool)
        or not isinstance(lineage["schema_upgrade_count"], int)
        or not 0 <= lineage["schema_upgrade_count"] <= max_upgrade_count
    ):
        raise ValueError(f"{label} lineage count is malformed")
    if lineage["schema_upgrade_count"] == 0 and any(lineage[field] is not None for field in ("schema_upgrade_from", "schema_upgrade_parent_snapshot_sha256")):
        raise ValueError(f"{label} native lineage has unexpected upgrade identity")
    allowed_predecessors = {V7_SCHEMA_ID} if expected_schema == V8_SCHEMA_ID else {V7_SCHEMA_ID, V8_SCHEMA_ID}
    if lineage["schema_upgrade_count"] > 0 and (
        lineage["schema_upgrade_from"] not in allowed_predecessors
        or not isinstance(lineage["schema_upgrade_parent_snapshot_sha256"], str)
    ):
        raise ValueError(f"{label} imported lineage is malformed")
    missing = MODE_REQUIRED_CAPABILITIES[snapshot["mode"]] - set(capabilities)
    if "control_economy" in missing:
        raise GuardInputError("CONTROL_ECONOMY_REQUIRED", "STANDARD and RESCUE require control_economy")
    if snapshot["profile"] == "generic" and missing:
        raise ValueError(f"{label} generic {snapshot['mode']} facts miss capabilities: {sorted(missing)}")
    payload = {key: value for key, value in snapshot.items() if key != "snapshot_sha256"}
    if snapshot["snapshot_sha256"] != _digest(payload):
        raise ValueError(f"{label} snapshot hash mismatch")
    return snapshot


def capture(
    repo: Path | None,
    facts_path: str | None,
    profile: str,
    mode: str,
    allowed_paths_from: str | None = None,
    inherited_allowed_path_tokens: list[str] | None = None,
    inherited_dirty_records: dict[str, list[Any]] | None = None,
    inherited_lineage: dict[str, Any] | None = None,
    accepted_predecessor: dict[str, Any] | None = None,
    comparison_base_head: str | None = None,
    inherited_control_event_origin: int = 0,
) -> dict[str, Any]:
    profile = "generic" if profile == "auto" and facts_path else "git" if profile == "auto" else profile
    if profile == "generic" and not facts_path:
        raise ValueError("generic profile requires --facts")
    if profile == "git" and facts_path:
        raise ValueError("git profile consumes only --repo")
    if not any((repo, facts_path)):
        raise ValueError("provide --repo or --facts")
    predecessor_schema = (accepted_predecessor or {}).get("schema_id")
    if accepted_predecessor is not None:
        if predecessor_schema == V7_SCHEMA_ID:
            _validate_v7_snapshot(accepted_predecessor, "predecessor snapshot")
        elif predecessor_schema == V8_SCHEMA_ID:
            _validate_snapshot(accepted_predecessor, "predecessor snapshot", expected_schema=V8_SCHEMA_ID)
        else:
            _validate_snapshot(accepted_predecessor, "predecessor snapshot")
    facts = _normalize(_load(facts_path)) if profile == "generic" else _normalize({"capabilities": ["vcs"]})
    if allowed_paths_from is None and inherited_allowed_path_tokens is None and isinstance((accepted_predecessor or {}).get("repo"), dict):
        inherited_allowed_path_tokens = accepted_predecessor["repo"].get("allowed_path_tokens")
    if inherited_dirty_records is None and isinstance((accepted_predecessor or {}).get("repo"), dict):
        inherited_dirty_records = accepted_predecessor["repo"].get("dirty_records")
    if comparison_base_head is None and isinstance((accepted_predecessor or {}).get("repo"), dict):
        comparison_base_head = accepted_predecessor["repo"].get("head")
    repo_facts = (
        _git(
            repo,
            allowed_paths_from=allowed_paths_from,
            inherited_allowed_path_tokens=inherited_allowed_path_tokens,
            inherited_dirty_records=inherited_dirty_records,
            comparison_base_head=comparison_base_head,
        )
        if repo
        else None
    )
    if repo_facts is not None and "vcs" not in facts["capabilities"]:
        facts = {**facts, "capabilities": sorted({*facts["capabilities"], "vcs"})}
    legacy_control_events = inherited_control_event_origin
    if predecessor_schema == V7_SCHEMA_ID:
        legacy_control_events = accepted_predecessor["facts"].get("control_event_count") or 0
    elif predecessor_schema == V8_SCHEMA_ID:
        legacy_control_events = (accepted_predecessor["facts"].get("control_economy") or {}).get("legacy_control_event_count", 0)
    elif predecessor_schema == SCHEMA_ID:
        legacy_control_events = (accepted_predecessor["facts"].get("control_economy") or {}).get("legacy_control_event_count", 0)
    facts = _finalize_control_economy(facts, repo_facts, legacy_control_event_count=legacy_control_events)
    campaign_token = facts.get("campaign_token") or facts.get("project_token") or (repo_facts or {}).get("repo_token")
    if not isinstance(campaign_token, str) or not campaign_token:
        raise ValueError("capture requires a project, campaign, or repository identity")
    if inherited_lineage is not None and accepted_predecessor is not None:
        raise ValueError("capture cannot inherit and rebaseline lineage simultaneously")
    if inherited_lineage is not None:
        lineage = dict(inherited_lineage)
        if lineage.get("campaign_token") != campaign_token:
            raise ValueError("current facts disagree with inherited campaign lineage")
    elif accepted_predecessor is not None:
        predecessor_lineage = accepted_predecessor["lineage"]
        if predecessor_lineage.get("campaign_token") != campaign_token:
            raise ValueError("accepted rebaseline cannot change campaign identity")
        if predecessor_schema in {V7_SCHEMA_ID, V8_SCHEMA_ID}:
            lineage = {
                "campaign_token": campaign_token,
                "parent_snapshot_sha256": predecessor_lineage.get("parent_snapshot_sha256"),
                "accepted_rebaseline_count": predecessor_lineage["accepted_rebaseline_count"],
                "schema_upgrade_from": predecessor_schema,
                "schema_upgrade_parent_snapshot_sha256": accepted_predecessor["snapshot_sha256"],
                "schema_upgrade_count": predecessor_lineage.get("schema_upgrade_count", 0) + 1,
            }
        else:
            if predecessor_lineage.get("accepted_rebaseline_count") >= 1:
                raise ValueError("accepted rebaseline limit exceeded for this campaign")
            lineage = {
                **predecessor_lineage,
                "campaign_token": campaign_token,
                "parent_snapshot_sha256": accepted_predecessor["snapshot_sha256"],
                "accepted_rebaseline_count": predecessor_lineage["accepted_rebaseline_count"] + 1,
            }
    else:
        lineage = {
            "campaign_token": campaign_token,
            "parent_snapshot_sha256": None,
            "accepted_rebaseline_count": 0,
            "schema_upgrade_from": None,
            "schema_upgrade_parent_snapshot_sha256": None,
            "schema_upgrade_count": 0,
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


def _campaign_control_rebaseline_violations(before_facts: dict[str, Any], after_facts: dict[str, Any]) -> list[dict[str, Any]]:
    before = before_facts.get("campaign_control")
    after = after_facts.get("campaign_control")
    if before is None and after is None:
        return []
    if before is None:
        zero_consumed = all(after["objective_consumed"][owner][resource] == 0 for owner in OBJECTIVE_OWNERS for resource in CAMPAIGN_RESOURCES)
        if (
            after["origin_completed_mutation_count"] != after_facts.get("completed_mutation_count")
            or after["origin_expensive_start_count"] != after_facts.get("expensive_start_count")
            or after["attempt_records"]
            or not zero_consumed
        ):
            return [_violation("REBASE_CAMPAIGN_CONTROL_RETROACTIVE")]
        return []
    if after is None:
        return [_violation("REBASE_REMOVED_CAMPAIGN_CONTROL")]

    out: list[dict[str, Any]] = []
    if any(
        before[field] != after[field]
        for field in (
            "origin_identity",
            "origin_completed_mutation_count",
            "origin_expensive_start_count",
        )
    ):
        out.append(_violation("REBASE_CHANGED_CAMPAIGN_ORIGIN"))
    if before["absolute_limits"] != after["absolute_limits"]:
        out.append(_violation("REBASE_CHANGED_ABSOLUTE_LIMITS"))

    scope_changed = before["objective_scope_identity"] != after["objective_scope_identity"]
    limits_changed = before["objective_limits"] != after["objective_limits"]
    envelope_changed = before["envelope_identity"] != after["envelope_identity"]
    if (scope_changed or limits_changed) and not envelope_changed:
        out.append(_violation("REBASE_ENVELOPE_IDENTITY_NOT_REVISED"))
    for resource in CAMPAIGN_RESOURCES:
        if after["objective_limits"]["P0"][resource] < before["objective_limits"]["P0"][resource]:
            out.append(_violation("REBASE_REDUCED_P0_BUDGET", resource=resource))
        for owner in OBJECTIVE_OWNERS[1:]:
            if after["objective_limits"][owner][resource] > before["objective_limits"][owner][resource]:
                out.append(
                    _violation(
                        "REBASE_INCREASED_SECONDARY_BUDGET",
                        objective_owner=owner,
                        resource=resource,
                    )
                )
        for owner in OBJECTIVE_OWNERS:
            _regression(
                out,
                before["objective_consumed"][owner][resource],
                after["objective_consumed"][owner][resource],
                "REBASE_RESET_OBJECTIVE_CONSUMPTION",
            )
    out.extend(_attempt_transition_violations(before, after))
    return out


def _upgrade_common_violations(
    predecessor: dict[str, Any],
    successor: dict[str, Any],
    code: str,
    source_schema: str,
    fact_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    before, after = predecessor["facts"], successor["facts"]
    out: list[dict[str, Any]] = []
    if predecessor["profile"] != successor["profile"] or predecessor["mode"] != successor["mode"]:
        out.append(_violation(code, component="profile_or_mode"))
    if drifted := [field for field in fact_fields if before.get(field) != after.get(field)]:
        out.append(_violation(code, fields=drifted))
    before_repo, after_repo = predecessor.get("repo"), successor.get("repo")
    if isinstance(before_repo, dict) != isinstance(after_repo, dict):
        out.append(_violation(code, component="repository_presence"))
    elif isinstance(before_repo, dict) and (
        drifted := [field for field in UPGRADE_REPO_FIELDS if before_repo.get(field) != after_repo.get(field)]
    ):
        out.append(_violation(code, repository_fields=drifted))
    if after.get("writer_free") is not True or (after.get("active_mutator_count") or 0) != 0 or (after.get("active_expensive_run_count") or 0) != 0:
        out.append(_violation(code, component="writer_or_active_run"))
    lineage = successor["lineage"]
    if (
        lineage.get("schema_upgrade_count") != predecessor["lineage"].get("schema_upgrade_count", 0) + 1
        or lineage.get("schema_upgrade_from") != source_schema
        or lineage.get("schema_upgrade_parent_snapshot_sha256") != predecessor.get("snapshot_sha256")
        or lineage.get("accepted_rebaseline_count") != predecessor["lineage"].get("accepted_rebaseline_count")
    ):
        out.append(_violation(code, component="upgrade_lineage"))
    return out


def _v7_upgrade_violations(predecessor: dict[str, Any], successor: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        _validate_v7_snapshot(predecessor, "V7 predecessor")
        _validate_snapshot(successor, "V9 successor")
    except ValueError as exc:
        return [_violation("V7_UPGRADE_HISTORY_DRIFT", reason=str(exc))]
    before, after = predecessor["facts"], successor["facts"]
    out = _upgrade_common_violations(
        predecessor,
        successor,
        "V7_UPGRADE_HISTORY_DRIFT",
        V7_SCHEMA_ID,
        UPGRADE_HISTORY_FIELDS,
    )
    control = after.get("control_economy")
    legacy = before.get("control_event_count") or 0
    if not isinstance(control, dict) or control.get("legacy_control_event_count") != legacy:
        out.append(_violation("V7_UPGRADE_HISTORY_DRIFT", component="legacy_control_origin"))
    elif control.get("records"):
        out.append(_violation("V7_UPGRADE_HISTORY_DRIFT", component="decision_added_during_upgrade"))
    preserved_findings = set(_tokens("blocker", [finding["finding_id"] for finding in (control or {}).get("findings", [])]))
    if set(before.get("blocker_ids", [])) - set(after.get("blocker_ids", [])) - preserved_findings:
        out.append(_violation("V7_UPGRADE_HISTORY_DRIFT", component="lost_blocker_history"))
    campaign = before.get("campaign_control")
    if campaign and (control or {}).get("objective_scope_identity") != campaign.get("objective_scope_identity"):
        out.append(_violation("V7_UPGRADE_HISTORY_DRIFT", component="objective_scope"))
    return out


def _v8_upgrade_violations(predecessor: dict[str, Any], successor: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        _validate_snapshot(
            predecessor,
            "V8 predecessor",
            expected_schema=V8_SCHEMA_ID,
        )
        _validate_snapshot(successor, "V9 successor")
    except ValueError as exc:
        return [_violation("V8_UPGRADE_HISTORY_DRIFT", reason=str(exc))]
    before, after = predecessor["facts"], successor["facts"]
    out = _upgrade_common_violations(
        predecessor,
        successor,
        "V8_UPGRADE_HISTORY_DRIFT",
        V8_SCHEMA_ID,
        UPGRADE_HISTORY_FIELDS + V8_UPGRADE_EXTRA_FIELDS,
    )
    before_control = before.get("control_economy")
    after_control = after.get("control_economy")
    if isinstance(before_control, dict) != isinstance(after_control, dict):
        out.append(_violation("V8_UPGRADE_HISTORY_DRIFT", component="control_economy_presence"))
    elif isinstance(before_control, dict):
        preserved = (
            "envelope_identity",
            "origin_identity",
            "objective_scope_identity",
            "stop_point_identity",
            "limits",
            "records",
            "legacy_control_event_count",
            "consumed",
            "remaining",
            "active_frontier",
            "findings",
            "classification_sets",
            "surface_budget",
        )
        control_drift = [field for field in preserved if before_control.get(field) != after_control.get(field)]
        if control_drift:
            out.append(
                _violation(
                    "V8_UPGRADE_HISTORY_DRIFT",
                    control_fields=control_drift,
                )
            )
    return out


def _rebaseline_violations(predecessor: dict[str, Any], successor: dict[str, Any]) -> list[dict[str, Any]]:
    if predecessor.get("schema_id") == V7_SCHEMA_ID:
        return _v7_upgrade_violations(predecessor, successor)
    if predecessor.get("schema_id") == V8_SCHEMA_ID:
        return _v8_upgrade_violations(predecessor, successor)
    out: list[dict[str, Any]] = []
    before, after = predecessor["facts"], successor["facts"]
    for violation in _campaign_control_violations(before):
        out.append({**violation, "code": f"REBASE_PREDECESSOR_{violation['code']}"})
    if predecessor.get("profile") != successor.get("profile"):
        out.append(_violation("REBASE_PROFILE_CHANGED"))
    if before.get("project_token") != after.get("project_token"):
        out.append(_violation("REBASE_PROJECT_CHANGED"))
    before_repo, after_repo = predecessor.get("repo"), successor.get("repo")
    if isinstance(before_repo, dict) != isinstance(after_repo, dict):
        out.append(_violation("REBASE_PROJECT_IDENTITY_SOURCE_CHANGED"))
    elif isinstance(before_repo, dict) and before_repo.get("repo_token") != after_repo.get("repo_token"):
        out.append(_violation("REBASE_REPOSITORY_CHANGED"))
    before_caps = set(before.get("capabilities", []))
    after_caps = set(after.get("capabilities", []))
    erased_caps = sorted(before_caps - after_caps)
    if erased_caps:
        out.append(_violation("REBASE_ERASED_CAPABILITIES", capabilities=erased_caps))
    before_closure = set(before.get("closure_item_ids", []))
    after_closure = set(after.get("closure_item_ids", []))
    if not before_closure <= after_closure:
        out.append(_violation("REBASE_ERASED_CLOSURE_ITEMS"))
    b_total, a_total = before.get("closure_item_count"), after.get("closure_item_count")
    if isinstance(b_total, int) and isinstance(a_total, int) and a_total < b_total:
        out.append(_violation("REBASE_ERASED_CLOSURE_DENOMINATOR", before=b_total, after=a_total))
    new_closure = after_closure - before_closure
    old_open_closed = set(before.get("open_item_ids", [])) - set(after.get("open_item_ids", []))
    reopened = sorted((set(after.get("open_item_ids", [])) - set(before.get("open_item_ids", []))) - new_closure)
    b_closed, a_closed = before.get("closed_item_count"), after.get("closed_item_count")
    if reopened:
        out.append(_violation("REBASE_REOPENED_CLOSURE_ITEMS", count=len(reopened)))
    elif isinstance(b_closed, int) and isinstance(a_closed, int) and a_closed < b_closed:
        out.append(_violation("REBASE_REOPENED_CLOSURE_ITEMS", before=b_closed, after=a_closed))
    if len(new_closure) > 1 or (new_closure and old_open_closed):
        out.append(
            _violation(
                "REBASE_CLOSURE_LINEAGE_UNPROVABLE",
                new_item_count=len(new_closure),
                concurrently_closed_old_item_count=len(old_open_closed),
            )
        )
    if not before_closure and not after_closure and isinstance(b_total, int) and isinstance(a_total, int) and a_total > b_total:
        out.append(
            _violation(
                "REBASE_CLOSURE_LINEAGE_UNPROVABLE",
                denominator_delta=a_total - b_total,
            )
        )
    if isinstance(before_repo, dict) and not set(before_repo.get("allowed_path_tokens", [])) <= set(after_repo.get("allowed_path_tokens", [])):
        out.append(_violation("REBASE_ERASED_ALLOWED_PATHS"))
    if not set(before.get("allowed_object_ids", [])) <= set(after.get("allowed_object_ids", [])):
        out.append(_violation("REBASE_ERASED_ALLOWED_OBJECTS"))

    added_paths = (
        set(after_repo.get("allowed_path_tokens", [])) - set(before_repo.get("allowed_path_tokens", []))
        if isinstance(before_repo, dict) and isinstance(after_repo, dict)
        else set()
    )
    added_objects = set(after.get("allowed_object_ids", [])) - set(before.get("allowed_object_ids", []))
    closure_expanded = bool(new_closure) or (isinstance(b_total, int) and isinstance(a_total, int) and a_total > b_total)
    protected_changed = before.get("protected_content_identity") != after.get("protected_content_identity")
    before_control = before.get("campaign_control")
    after_control = after.get("campaign_control")
    before_economy = before.get("control_economy")
    after_economy = after.get("control_economy")
    campaign_activated = before_control is None and isinstance(after_control, dict)
    control_activated = before_economy is None and isinstance(after_economy, dict)
    objective_scope_changed = (
        isinstance(before_control, dict) and isinstance(after_control, dict) and before_control["objective_scope_identity"] != after_control["objective_scope_identity"]
    ) or (isinstance(before_economy, dict) and isinstance(after_economy, dict) and before_economy["objective_scope_identity"] != after_economy["objective_scope_identity"])
    control_limits_changed = isinstance(before_economy, dict) and isinstance(after_economy, dict) and before_economy["limits"] != after_economy["limits"]
    scope_delta = {
        "allowed_path_count": len(added_paths),
        "allowed_object_count": len(added_objects),
        "closure_item_count": len(new_closure),
        "closure_denominator_delta": (a_total - b_total if isinstance(b_total, int) and isinstance(a_total, int) and a_total > b_total else 0),
        "protected_content_changed": protected_changed,
        "objective_scope_changed": objective_scope_changed,
        "campaign_control_activated": campaign_activated,
        "control_economy_activated": control_activated,
        "control_limits_changed": control_limits_changed,
    }
    has_scope_delta = any((added_paths, added_objects, closure_expanded, protected_changed, objective_scope_changed, campaign_activated, control_activated, control_limits_changed))
    if has_scope_delta:
        before_revision = before.get("authority_revision_count")
        after_revision = after.get("authority_revision_count")
        expected_revision = (before_revision if isinstance(before_revision, int) else 0) + 1
        authority_active = after.get("authority_status") == "ACTIVATED"
        identity_advanced = isinstance(after.get("authority_revision_identity"), str) and after.get("authority_revision_identity") != before.get("authority_revision_identity")
        if not authority_active:
            out.append(
                _violation(
                    "REBASE_SCOPE_DELTA_AUTHORITY_REQUIRED",
                    rejected_delta=scope_delta,
                    missing_authority="ACTIVATED authority revision covering the exact delta",
                )
            )
        if after_revision != expected_revision or not identity_advanced:
            out.append(
                _violation(
                    "REBASE_AUTHORITY_REVISION_NOT_ADVANCED",
                    rejected_delta=scope_delta,
                    expected_revision=expected_revision,
                    actual_revision=after_revision,
                )
            )
        if objective_scope_changed and (not authority_active or after_revision != expected_revision):
            out.append(
                _violation(
                    "OWNER_CHANGE_REQUIRES_ARCHITECTURE_REBASE",
                    rejected_delta=scope_delta,
                )
            )
        writer_free = after.get("writer_free") is True and after.get("active_mutator_count") == 0 and after.get("active_expensive_run_count") == 0
        new_changed_paths = (
            set(after_repo.get("changed_path_tokens", [])) - set(before_repo.get("changed_path_tokens", []))
            if isinstance(before_repo, dict) and isinstance(after_repo, dict)
            else set()
        )
        new_changed_objects = set(after.get("changed_object_ids", [])) - set(before.get("changed_object_ids", []))
        mutation_advanced = (
            isinstance(before.get("completed_mutation_count"), int)
            and isinstance(after.get("completed_mutation_count"), int)
            and after["completed_mutation_count"] > before["completed_mutation_count"]
        )
        head_advanced = isinstance(before_repo, dict) and isinstance(after_repo, dict) and before_repo.get("head") != after_repo.get("head")
        if not writer_free or new_changed_paths or new_changed_objects or mutation_advanced or head_advanced:
            out.append(
                _violation(
                    "REBASE_SCOPE_EXPANSION_AFTER_MUTATION_STARTED",
                    rejected_delta=scope_delta,
                    writer_free=writer_free,
                    changed_path_count=len(new_changed_paths),
                    changed_object_count=len(new_changed_objects),
                )
            )
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
    predecessor_limits = MODES[predecessor["mode"]]
    for field, limit_key, code in (
        ("completed_mutation_count", "mutations", "REBASE_MUTATION_DELTA_EXCEEDED"),
        ("control_event_count", "events", "REBASE_CONTROL_EVENT_DELTA_EXCEEDED"),
        (
            "expensive_start_count",
            "expensive",
            "REBASE_EXPENSIVE_START_DELTA_EXCEEDED",
        ),
    ):
        before_value, after_value = before.get(field), after.get(field)
        allowed = predecessor_limits[limit_key]
        if isinstance(before_value, int) and isinstance(after_value, int) and after_value - before_value > allowed:
            out.append(_violation(code, delta=after_value - before_value, allowed=allowed))
    out.extend(_campaign_control_rebaseline_violations(before, after))
    out.extend(_control_rebaseline_violations(before, after))
    deadline = before.get("rescue_deadline_at")
    if deadline is not None and after.get("rescue_deadline_at") != deadline:
        out.append(_violation("REBASE_CHANGED_RESCUE_DEADLINE"))
    return out


def _guidance(next_action: str, *prohibited: str, reusable: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"minimum_legal_next_action": next_action}
    if prohibited:
        result["prohibited_actions"] = list(prohibited)
    if reusable:
        result["reusable_evidence"] = reusable
    return result


VIOLATION_GUIDANCE = {
    "CONTROL_ECONOMY_REQUIRED": _guidance("supply_one_bounded_control_economy_for_STANDARD_or_RESCUE", "continue_without_a_control_record_chain"),
    "CONTROL_DECISION_KEY_REUSED": _guidance(
        "reuse_the_existing_exact_key_decision_id",
        "rename_checkpoint_or_transaction_to_create_a_new_decision",
        reusable="the existing decision record and unchanged exact-key evidence",
    ),
    "CONTROL_BUDGET_EXHAUSTED": _guidance("reuse_an_uninvalidated_READY_decision_or_stop_for_authority", "add_a_gate_receipt_roundtrip_or_reconstructed_context"),
    "CROSS_OBJECTIVE_CONTROL_COST": _guidance("split_into_one_objective_owned_control_decision", "charge_one_record_to_multiple_objectives"),
    "GATE_NO_ACTIVE_CONSUMER_DOWNGRADED": _guidance("retain_as_advisory_until_a_current_consumer_is_proven", "block_primary_with_unreachable_telemetry"),
    "DORMANT_RECOVERY_BLOCK_IGNORED": _guidance("continue_the_uninvalidated_READY_primary", "activate_dormant_recovery_without_admissible_failure_or_authority"),
    "RECOVERY_ACTIVATION_NOT_ADMISSIBLE": _guidance(
        "keep_recovery_dormant_until_typed_primary_terminal_or_successor_authority", "make_archive_retry_or_recovery_a_primary_precondition"
    ),
    "READY_GENERATION_DRIFT": _guidance("freeze_the_new_generation_and_form_a_new_decision_key", "consume_the_previous_READY_activation"),
    "CLASSIFICATION_SET_INCOMPLETE": _guidance("classify_the_complete_finite_denominator_once", "return_to_per_object_exceptions", "use_an_open_or_wildcard_set"),
    "CLASSIFICATION_SET_DRIFT": _guidance("seal_one_new_complete_denominator_without_rewriting_the_old_set", "append_unclassified_members", "rewrite_terminal_dispositions"),
    "CONTROL_SURFACE_EXPANSION_REQUIRES_ARCHITECTURE_REBASE": _guidance(
        "justify_the_exact_surface_delta_under_writer_free_authority_rebase", "hide_new_routes_or_recovery_branches_inside_an_existing_file"
    ),
    "STOP_NO_JUSTIFIED_CONTROL_ACTION": _guidance("reuse_downgrade_defer_or_stop_the_control_action", "count_commentary_hashing_or_receipt_relabeling_as_progress"),
    "STAGE_AUDIT_REQUIRED": _guidance(
        "run_one_exact_key_stage_audit_with_the_existing_decision_chain",
        "promote_the_stage_or_start_the_next_material_action",
        "create_a_separate_audit_gate_or_ledger",
    ),
    "STAGE_DESIGN_AUDIT_REQUIRED": _guidance(
        "audit_the_current_stage_design_before_material_build_or_execution",
        "write_or_start_then_backfill_the_design_audit",
    ),
    "STAGE_BUILD_AUDIT_REQUIRED": _guidance(
        "audit_the_completed_build_before_READY_RUN_or_next_expensive_stage",
        "treat_compile_success_as_project_acceptance",
    ),
    "STAGE_AUDIT_CONTEXT_MISMATCH": _guidance(
        "recapture_the_current_stage_owner_generation_consumer_and_frontier",
        "reuse_an_audit_from_another_stage_or_objective",
    ),
    "STAGE_AUDIT_PREDECESSOR_INVALID": _guidance(
        "cite_the_passed_design_audit_for_the_same_stage_generation_owner_and_consumer",
        "promote_a_build_without_design_lineage",
    ),
    "STAGE_SIMPLICITY_AUDIT_REDUCTION_REQUIRED": _guidance(
        "apply_one_bounded_reduction_tranche_then_revalidate_only_the_affected_stage",
        "promote_with_orphan_duplicate_future_or_dormant_control_surfaces",
        reusable="unaffected exact-key evidence and sealed inputs",
    ),
    "STAGE_SIMPLICITY_AUDIT_AUTHORITY_BLOCKED": _guidance(
        "stop_for_the_named_project_or_protected_boundary_authority",
        "delete_or_weaken_a_required_contract_to_appear_simpler",
    ),
    "V8_UPGRADE_HISTORY_DRIFT": _guidance(
        "recapture_a_writer_free_V9_snapshot_preserving_all_V8_history",
        "reset_records_budget_attempt_failure_scope_or_authority_history",
        reusable="the validated_read_only_V8_snapshot",
    ),
    "V7_UPGRADE_HISTORY_DRIFT": _guidance(
        "recapture_a_writer_free_V9_snapshot_preserving_all_V7_history",
        "reset_budget_attempt_failure_scope_or_authority_history",
        reusable="the validated_read_only_V7_snapshot",
    ),
    "REBASE_SCOPE_DELTA_AUTHORITY_REQUIRED": _guidance(
        "obtain_and_activate_one_authority_revision_for_the_exact_scope_delta", "self_authorize_scope_delta", "mutate_before_rebaseline"
    ),
    "REBASE_AUTHORITY_REVISION_NOT_ADVANCED": _guidance("recapture_with_exactly_one_new_nonempty_authority_revision", "reuse_old_revision_identity", "skip_revision_lineage"),
    "REBASE_SCOPE_EXPANSION_AFTER_MUTATION_STARTED": _guidance(
        "stop_further_writes_and_adjudicate_existing_delta",
        "backfill_scope_authority",
        "continue_the_dirty_tranche",
        reusable="only unchanged exact-key evidence remains eligible for project-authorized reuse",
    ),
    "OWNER_CHANGE_REQUIRES_ARCHITECTURE_REBASE": _guidance("perform_an_authorized_writer_free_architecture_rebase", "relabel_surface_owner_as_a_facts_update"),
    "DIRTY_MUTATION_COUNTED_COMPLETED": _guidance("restore_completed_count_then_commit_or_abandon_the_dirty_tranche", "claim_dirty_work_as_completed"),
    "MUTATION_COMPLETED_WITHOUT_GENERATION_ADVANCE": _guidance("form_a_new_committed_or_project_generation_before_completion", "reuse_the_pre_mutation_generation"),
    "MUTATION_COMPLETED_WITHOUT_FRESH_VALIDATION": _guidance("run_the_minimum_sufficient_validation_on_the_new_generation", "reuse_stale_validation_as_mutation_completion"),
    "ORPHAN_ACTIVE_ATTEMPT_REQUIRES_RECONCILIATION": _guidance(
        "reconcile_the_existing_ACTIVE_attempt_to_one_evidenced_terminal",
        "start_a_replacement_attempt",
        "delete_or_relabel_the_ACTIVE_attempt",
        reusable="the original start identity and consumed budget remain valid history",
    ),
    "REBASE_CLOSURE_LINEAGE_UNPROVABLE": _guidance("retain_existing_item_identities_or_stop_for_project_lineage_authority", "rename_split_merge_or_supersede_without_lineage"),
    "ACTIVATION_STATE_DRIFT": _guidance("recapture_and_compare_inside_the_existing_project_lock_or_CAS", "consume_the_previous_activation_identity"),
}


def _violation(code: str, **details: Any) -> dict[str, Any]:
    guidance = VIOLATION_GUIDANCE.get(
        code,
        {"minimum_legal_next_action": "stop_and_resolve_the_named_typed_violation"},
    )
    return {"code": code, **guidance, **details}


def _add_violation(out: list[dict[str, Any]], code: str, **details: Any) -> None:
    out.append(_violation(code, **details))


def _increase(out: list[dict[str, Any]], before: Any, after: Any, code: str) -> None:
    if isinstance(before, int) and isinstance(after, int) and after > before:
        out.append(_violation(code, before=before, after=after))


def _regression(out: list[dict[str, Any]], before: Any, after: Any, code: str) -> None:
    if isinstance(before, int) and isinstance(after, int) and after < before:
        out.append(_violation(code, before=before, after=after))


def _objective_total(control: dict[str, Any], field: str, resource: str) -> int:
    return sum(control[field][owner][resource] for owner in OBJECTIVE_OWNERS)


def _campaign_control_violations(facts: dict[str, Any]) -> list[dict[str, Any]]:
    control = facts.get("campaign_control")
    if control is None:
        return []
    out: list[dict[str, Any]] = []
    completed = facts.get("completed_mutation_count")
    starts = facts.get("expensive_start_count")
    active = facts.get("active_expensive_run_count")
    if not all(isinstance(value, int) for value in (completed, starts, active)):
        return [_violation("CAMPAIGN_CONTROL_COUNTERS_INCOMPLETE")]

    origins = {
        "mutations": control["origin_completed_mutation_count"],
        "expensive_starts": control["origin_expensive_start_count"],
    }
    current = {"mutations": completed, "expensive_starts": starts}
    for resource in CAMPAIGN_RESOURCES:
        if current[resource] < origins[resource]:
            _add_violation(out, "CAMPAIGN_ORIGIN_AHEAD_OF_COUNTERS", resource=resource, origin=origins[resource], current=current[resource])
            continue
        limit_total = _objective_total(control, "objective_limits", resource)
        if limit_total != control["absolute_limits"][resource]:
            _add_violation(out, "OBJECTIVE_LIMIT_TOTAL_MISMATCH", resource=resource, objective_total=limit_total, absolute_limit=control["absolute_limits"][resource])
        consumed_total = _objective_total(control, "objective_consumed", resource)
        expected = current[resource] - origins[resource]
        if consumed_total != expected:
            _add_violation(out, "OBJECTIVE_BUDGET_ACCOUNTING_MISMATCH", resource=resource, consumed=consumed_total, expected=expected)
        if expected > control["absolute_limits"][resource]:
            _add_violation(
                out,
                "ABSOLUTE_MUTATION_BUDGET_EXCEEDED" if resource == "mutations" else "ABSOLUTE_EXPENSIVE_START_BUDGET_EXCEEDED",
                consumed=expected,
                allowed=control["absolute_limits"][resource],
            )
        for owner in OBJECTIVE_OWNERS:
            consumed = control["objective_consumed"][owner][resource]
            allowed = control["objective_limits"][owner][resource]
            if consumed > allowed:
                _add_violation(out, "OBJECTIVE_BUDGET_EXCEEDED", objective_owner=owner, resource=resource, consumed=consumed, allowed=allowed)

    records = control["attempt_records"]
    expected_attempts = max(0, starts - control["origin_expensive_start_count"])
    if len(records) != expected_attempts:
        _add_violation(out, "ATTEMPT_START_ACCOUNTING_MISMATCH", attempts=len(records), expected=expected_attempts)
    for owner in OBJECTIVE_OWNERS:
        owner_attempts = sum(record["objective_owner"] == owner for record in records)
        owner_consumed = control["objective_consumed"][owner]["expensive_starts"]
        if owner_attempts != owner_consumed:
            _add_violation(out, "ATTEMPT_OWNER_BUDGET_MISMATCH", objective_owner=owner, attempts=owner_attempts, consumed=owner_consumed)
    active_records = sum(record["status"] == "ACTIVE" for record in records)
    if active_records != active:
        _add_violation(out, "ATTEMPT_ACTIVE_COUNT_MISMATCH", active_attempts=active_records, active_expensive_runs=active)
    by_key: dict[str, list[str]] = {}
    for record in records:
        by_key.setdefault(record["equivalence_key_sha256"], []).append(record["attempt_id"])
    for key, attempt_ids in by_key.items():
        if len(attempt_ids) > 1:
            _add_violation(out, "EXPENSIVE_ATTEMPT_KEY_REUSED", equivalence_key_sha256=key, attempt_count=len(attempt_ids))
    return out


def _objective_delta_owners(before: dict[str, Any], after: dict[str, Any], resource: str) -> set[str]:
    return {owner for owner in OBJECTIVE_OWNERS if after["objective_consumed"][owner][resource] > before["objective_consumed"][owner][resource]}


def _attempt_transition_violations(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    before_records = {record["attempt_id"]: record for record in before["attempt_records"]}
    after_records = {record["attempt_id"]: record for record in after["attempt_records"]}
    removed = sorted(set(before_records) - set(after_records))
    if removed:
        out.append(_violation("ATTEMPT_HISTORY_REGRESSED", removed_count=len(removed)))
    for attempt_id in sorted(set(before_records) & set(after_records)):
        old = before_records[attempt_id]
        new = after_records[attempt_id]
        if any(old[field] != new[field] for field in ("objective_owner", "equivalence_key_sha256", "start_identity")):
            out.append(_violation("ATTEMPT_IDENTITY_REWRITTEN", attempt_id=attempt_id))
            continue
        if old["status"] == "ACTIVE":
            if new["status"] == "ACTIVE":
                continue
        elif new["status"] != old["status"] or new["terminal_evidence_identity"] != old["terminal_evidence_identity"]:
            out.append(_violation("ATTEMPT_TERMINAL_REWRITTEN", attempt_id=attempt_id))
    return out


def _campaign_control_compare(before_facts: dict[str, Any], after_facts: dict[str, Any]) -> list[dict[str, Any]]:
    before = before_facts.get("campaign_control")
    after = after_facts.get("campaign_control")
    if before is None and after is None:
        return []
    if before is None or after is None:
        return [_violation("CAMPAIGN_CONTROL_CHANGED_WITHOUT_REBASE")]
    counter_values = (
        before_facts.get("completed_mutation_count"),
        before_facts.get("expensive_start_count"),
        after_facts.get("completed_mutation_count"),
        after_facts.get("expensive_start_count"),
    )
    if not all(isinstance(value, int) for value in counter_values):
        return [_violation("CAMPAIGN_CONTROL_COUNTERS_INCOMPLETE")]
    out: list[dict[str, Any]] = []
    if before["envelope_identity"] != after["envelope_identity"]:
        out.append(_violation("CAMPAIGN_ENVELOPE_DRIFT"))
    if before["objective_scope_identity"] != after["objective_scope_identity"]:
        out.append(_violation("OBJECTIVE_SCOPE_DRIFT"))
    if any(
        before[field] != after[field]
        for field in (
            "origin_identity",
            "origin_completed_mutation_count",
            "origin_expensive_start_count",
        )
    ):
        out.append(_violation("CAMPAIGN_ORIGIN_DRIFT"))
    if before["absolute_limits"] != after["absolute_limits"]:
        out.append(_violation("CAMPAIGN_ABSOLUTE_LIMITS_DRIFT"))
    if before["objective_limits"] != after["objective_limits"]:
        out.append(_violation("OBJECTIVE_LIMITS_CHANGED_WITHOUT_REBASE"))

    delta_owners: set[str] = set()
    for resource in CAMPAIGN_RESOURCES:
        owners = _objective_delta_owners(before, after, resource)
        delta_owners |= owners
        for owner in OBJECTIVE_OWNERS:
            _regression(
                out,
                before["objective_consumed"][owner][resource],
                after["objective_consumed"][owner][resource],
                "OBJECTIVE_CONSUMPTION_REGRESSED",
            )
    if len(delta_owners) > 1:
        out.append(
            _violation(
                "CROSS_OBJECTIVE_ACTION_MIXED",
                objective_owner_count=len(delta_owners),
            )
        )

    out.extend(_attempt_transition_violations(before, after))
    before_ids = {record["attempt_id"] for record in before["attempt_records"]}
    new_records = [record for record in after["attempt_records"] if record["attempt_id"] not in before_ids]
    unresolved_before = [record["attempt_id"] for record in before["attempt_records"] if record["status"] == "ACTIVE"]
    if unresolved_before and new_records:
        out.append(
            _violation(
                "ORPHAN_ACTIVE_ATTEMPT_REQUIRES_RECONCILIATION",
                active_attempt_ids=sorted(unresolved_before),
                rejected_new_attempt_count=len(new_records),
            )
        )
    start_delta = after_facts["expensive_start_count"] - before_facts["expensive_start_count"]
    if len(new_records) != max(0, start_delta):
        out.append(
            _violation(
                "ATTEMPT_START_DELTA_MISMATCH",
                new_attempts=len(new_records),
                start_delta=start_delta,
            )
        )
    expensive_owners = _objective_delta_owners(before, after, "expensive_starts")
    new_attempt_owners = {record["objective_owner"] for record in new_records}
    if new_attempt_owners != expensive_owners:
        out.append(
            _violation(
                "ATTEMPT_OWNER_BUDGET_MISMATCH",
                attempt_owner_count=len(new_attempt_owners),
                budget_owner_count=len(expensive_owners),
            )
        )
    return out


def _control_economy_violations(facts: dict[str, Any]) -> list[dict[str, Any]]:
    control = facts.get("control_economy")
    if control is None:
        return []
    out: list[dict[str, Any]] = []
    for owner in OBJECTIVE_OWNERS:
        for cost in CONTROL_COSTS:
            consumed = control["consumed"][owner][cost]
            allowed = control["limits"][owner][cost]
            if consumed > allowed:
                out.append(
                    _violation(
                        "CONTROL_BUDGET_EXHAUSTED",
                        objective_owner=owner,
                        cost=cost,
                        consumed=consumed,
                        allowed=allowed,
                    )
                )
    frontier = control.get("active_frontier")
    if frontier:
        recovery = frontier["recovery_state"]
        if recovery == "ACTIVE":
            terminal = frontier.get("primary_terminal_status")
            authorized = frontier.get("recovery_activation_reason") == "AUTHORIZED_SUCCESSOR"
            failed = frontier["primary_state"] == "TERMINAL" and terminal in {"FAILED_TYPED", "BLOCKED", "INCOMPLETE"}
            if not (authorized or failed) or not frontier.get("recovery_activation_identity"):
                out.append(_violation("RECOVERY_ACTIVATION_NOT_ADMISSIBLE"))
    if facts.get("blocker_ids") and not control.get("findings"):
        out.append(
            _violation(
                "CONTROL_FINDINGS_REQUIRED",
                minimum_legal_next_action="describe_each_blocker_with_current_consumer_reachability_and_effect",
            )
        )
    active_record = next(
        (
            record
            for record in control["records"]
            if record["decision_id"] == control.get("active_decision_id")
        ),
        None,
    )
    active_audit = (active_record or {}).get("stage_audit")
    if active_audit and active_audit["outcome"] != "PASS":
        code = (
            "STAGE_SIMPLICITY_AUDIT_REDUCTION_REQUIRED"
            if active_audit["outcome"] == "REDUCTION_REQUIRED"
            else "STAGE_SIMPLICITY_AUDIT_AUTHORITY_BLOCKED"
        )
        out.append(
            _violation(
                code,
                stage_identity=active_audit["stage_identity"],
                boundary=active_audit["boundary"],
            )
        )
    return out


def _matching_stage_audit(
    records: list[dict[str, Any]],
    frontier: dict[str, Any],
    boundary: str,
) -> dict[str, Any] | None:
    return next(
        (
            record
            for record in reversed(records)
            if (record.get("stage_audit") or {}).get("boundary") == boundary
            and record["stage_audit"]["outcome"] == "PASS"
            and record["stage_audit"]["stage_identity"] == frontier["frontier_identity"]
            and record["stage_audit"]["stage_generation_identity"]
            == frontier["primary_generation_identity"]
            and record["objective_owner"] == frontier["primary_objective_owner"]
            and record["active_consumer_identity"] == frontier["primary_consumer_identity"]
        ),
        None,
    )


def _effective_blocker_violations(facts: dict[str, Any]) -> list[dict[str, Any]]:
    control = facts.get("control_economy") or {}
    blockers, _ = _finding_projections(control.get("findings", []))
    return [
        _violation(
            "CONTROL_EFFECTIVE_BLOCKER",
            finding_id=finding["finding_id"],
            effective_tier=finding["effective_tier"],
            active_consumer_identity=finding["active_consumer_identity"],
            minimum_legal_next_action="resolve_or_authoritatively_reclassify_the_reachable_active_consumer_finding",
        )
        for finding in blockers
    ]


def _control_economy_compare(baseline: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    before = baseline["facts"].get("control_economy")
    after = current["facts"].get("control_economy")
    if before is None and after is None:
        return []
    if before is None or after is None:
        return [_violation("CONTROL_ECONOMY_REQUIRED")]
    out: list[dict[str, Any]] = []
    for field, code in (
        ("envelope_identity", "CONTROL_ENVELOPE_DRIFT"),
        ("origin_identity", "CONTROL_ORIGIN_DRIFT"),
        ("objective_scope_identity", "OBJECTIVE_SCOPE_DRIFT"),
        ("stop_point_identity", "CONTROL_STOP_POINT_DRIFT"),
        ("limits", "CONTROL_LIMITS_CHANGED_WITHOUT_REBASE"),
        ("legacy_control_event_count", "V7_UPGRADE_HISTORY_DRIFT"),
    ):
        if before.get(field) != after.get(field):
            out.append(_violation(code, component=field))
    before_records, after_records = before["records"], after["records"]
    if after_records[: len(before_records)] != before_records:
        out.append(_violation("CONTROL_RECORD_HISTORY_REGRESSED"))
    new_records = after_records[len(before_records) :]
    if len(new_records) > 1:
        out.append(_violation("CROSS_OBJECTIVE_CONTROL_COST", new_record_count=len(new_records)))
    if len({record["objective_owner"] for record in new_records}) > 1:
        out.append(_violation("CROSS_OBJECTIVE_CONTROL_COST"))
    out.extend(_control_economy_violations(current["facts"]))
    out.extend(_effective_blocker_violations(current["facts"]))

    before_surface = before.get("surface_budget")
    after_surface = after.get("surface_budget")
    if after_surface is not None:
        if growth := _surface_growth(before_surface, after_surface):
            _add_violation(out, "CONTROL_SURFACE_EXPANSION_REQUIRES_ARCHITECTURE_REBASE", rejected_delta=growth)
    elif before_surface is not None and after_surface is None:
        out.append(_violation("CONTROL_SURFACE_FACTS_REMOVED"))

    before_sets = {item["classification_id"]: item for item in before.get("classification_sets", [])}
    after_sets = {item["classification_id"]: item for item in after.get("classification_sets", [])}
    for identity in set(before_sets) & set(after_sets):
        if before_sets[identity] != after_sets[identity]:
            out.append(_violation("CLASSIFICATION_SET_DRIFT", classification_id=identity))
    if not set(before_sets) <= set(after_sets):
        out.append(_violation("CLASSIFICATION_SET_DRIFT", removed=True))

    before_frontier = before.get("active_frontier")
    after_frontier = after.get("active_frontier")
    frontier_changed = bool(
        after_frontier
        and (
            not before_frontier
            or before_frontier["frontier_identity"] != after_frontier["frontier_identity"]
            or before_frontier["primary_generation_identity"]
            != after_frontier["primary_generation_identity"]
        )
    )
    mutation_advanced = (current["facts"].get("completed_mutation_count") or 0) > (
        baseline["facts"].get("completed_mutation_count") or 0
    )
    expensive_started = (current["facts"].get("expensive_start_count") or 0) > (
        baseline["facts"].get("expensive_start_count") or 0
    )
    if after_frontier and (mutation_advanced or expensive_started):
        if not _matching_stage_audit(before_records, after_frontier, "DESIGN_COMPLETE"):
            out.append(_violation("STAGE_DESIGN_AUDIT_REQUIRED"))
    if after_frontier and frontier_changed and after_frontier["primary_state"] != "TERMINAL":
        if not _matching_stage_audit(after_records, after_frontier, "DESIGN_COMPLETE"):
            out.append(_violation("STAGE_DESIGN_AUDIT_REQUIRED"))
        if after_frontier["primary_state"] in {"READY", "RUNNING"} and not _matching_stage_audit(
            after_records,
            after_frontier,
            "BUILD_COMPLETE",
        ):
            out.append(_violation("STAGE_BUILD_AUDIT_REQUIRED"))
    if before_frontier and after_frontier:
        if before_frontier["primary_state"] in {"READY", "RUNNING"}:
            before_generation = before_frontier["primary_generation_identity"]
            after_generation = after_frontier["primary_generation_identity"]
            repo_head_changed = (baseline.get("repo") or {}).get("head") != (current.get("repo") or {}).get("head")
            source_changed = baseline["facts"].get("change_generation") != current["facts"].get("change_generation")
            if before_generation != after_generation or repo_head_changed or source_changed:
                out.append(_violation("READY_GENERATION_DRIFT"))
        allowed_primary = {
            "PREPARING": {"PREPARING", "READY", "TERMINAL"},
            "READY": {"READY", "RUNNING", "TERMINAL"},
            "RUNNING": {"RUNNING", "TERMINAL"},
            "TERMINAL": {"TERMINAL"},
        }
        if after_frontier["primary_state"] not in allowed_primary[before_frontier["primary_state"]]:
            out.append(_violation("PRIMARY_FRONTIER_STATE_REGRESSED"))
        if not frontier_changed and before_frontier["primary_state"] == "PREPARING" and after_frontier["primary_state"] in {
            "READY",
            "RUNNING",
        } and not _matching_stage_audit(after_records, after_frontier, "BUILD_COMPLETE"):
            out.append(_violation("STAGE_BUILD_AUDIT_REQUIRED"))
        if not frontier_changed and before_frontier["primary_state"] == "READY" and after_frontier["primary_state"] == "RUNNING" and not _matching_stage_audit(
            before_records,
            before_frontier,
            "BUILD_COMPLETE",
        ):
            out.append(_violation("STAGE_BUILD_AUDIT_REQUIRED"))
        allowed_recovery = {
            "NOT_APPLICABLE": {"NOT_APPLICABLE", "DORMANT"},
            "DORMANT": {"DORMANT", "ACTIVE", "TERMINAL"},
            "ACTIVE": {"ACTIVE", "TERMINAL"},
            "TERMINAL": {"TERMINAL"},
        }
        if after_frontier["recovery_state"] not in allowed_recovery[before_frontier["recovery_state"]]:
            out.append(_violation("RECOVERY_FRONTIER_STATE_REGRESSED"))
    return out


def _control_rebaseline_violations(before_facts: dict[str, Any], after_facts: dict[str, Any]) -> list[dict[str, Any]]:
    before = before_facts.get("control_economy")
    after = after_facts.get("control_economy")
    if before is None or after is None:
        return [] if before is after else [_violation("CONTROL_ECONOMY_REQUIRED")]
    out: list[dict[str, Any]] = []
    if before["origin_identity"] != after["origin_identity"] or before["stop_point_identity"] != after["stop_point_identity"]:
        out.append(_violation("CONTROL_ORIGIN_OR_STOP_POINT_DRIFT"))
    if after["records"][: len(before["records"])] != before["records"]:
        out.append(_violation("CONTROL_RECORD_HISTORY_REGRESSED"))
    if after["legacy_control_event_count"] != before["legacy_control_event_count"]:
        out.append(_violation("V7_UPGRADE_HISTORY_DRIFT", component="legacy_control_origin"))
    for cost in CONTROL_COSTS:
        before_total = sum(before["limits"][owner][cost] for owner in OBJECTIVE_OWNERS)
        after_total = sum(after["limits"][owner][cost] for owner in OBJECTIVE_OWNERS)
        if before_total != after_total:
            out.append(_violation("CONTROL_REBASE_ABSOLUTE_LIMIT_CHANGED", cost=cost))
        if after["limits"]["P0"][cost] < before["limits"]["P0"][cost]:
            out.append(_violation("CONTROL_REBASE_REDUCED_P0_BUDGET", cost=cost))
        for owner in OBJECTIVE_OWNERS[1:]:
            if after["limits"][owner][cost] > before["limits"][owner][cost]:
                out.append(
                    _violation(
                        "CONTROL_REBASE_INCREASED_SECONDARY_BUDGET",
                        objective_owner=owner,
                        cost=cost,
                    )
                )
    control_changed = before["objective_scope_identity"] != after["objective_scope_identity"] or before["limits"] != after["limits"]
    if control_changed and before["envelope_identity"] == after["envelope_identity"]:
        out.append(_violation("CONTROL_REBASE_ENVELOPE_NOT_REVISED"))
    before_surface = before.get("surface_budget")
    after_surface = after.get("surface_budget")
    if after_surface is not None:
        growth = _surface_growth(before_surface, after_surface)
        before_revision = before_facts.get("authority_revision_count")
        after_revision = after_facts.get("authority_revision_count")
        authorized = (
            after_facts.get("authority_status") == "ACTIVATED"
            and isinstance(before_revision, int)
            and after_revision == before_revision + 1
            and after_facts.get("authority_revision_identity") != before_facts.get("authority_revision_identity")
            and after_facts.get("writer_free") is True
            and after_facts.get("active_mutator_count") == 0
            and after_facts.get("active_expensive_run_count") == 0
            and any(
                record["decision_id"] == after.get("active_decision_id") and (record["objective_owner"] == "P0" or record["protected_constraint_identity"])
                for record in after["records"]
            )
        )
        if growth and not authorized:
            _add_violation(out, "CONTROL_SURFACE_EXPANSION_REQUIRES_ARCHITECTURE_REBASE", rejected_delta=growth, missing_authority="writer-free activated architecture revision")
    elif before_surface is not None:
        out.append(_violation("CONTROL_SURFACE_FACTS_REMOVED"))
    return out


def _campaign_budget_report(facts: dict[str, Any]) -> dict[str, Any] | None:
    control = facts.get("campaign_control")
    if control is None:
        return None
    active_owners = {record["objective_owner"] for record in control["attempt_records"] if record["status"] == "ACTIVE"}
    if not active_owners:
        active_owners = {owner for owner in OBJECTIVE_OWNERS if any(control["objective_consumed"][owner][resource] for resource in CAMPAIGN_RESOURCES)}
    if not active_owners:
        active_owners = {owner for owner in OBJECTIVE_OWNERS if any(control["objective_limits"][owner][resource] for resource in CAMPAIGN_RESOURCES)}
    return {
        "absolute_limits": dict(control["absolute_limits"]),
        "remaining_total": {resource: control["absolute_limits"][resource] - _objective_total(control, "objective_consumed", resource) for resource in CAMPAIGN_RESOURCES},
        "remaining_by_objective": {
            owner: {resource: control["objective_limits"][owner][resource] - control["objective_consumed"][owner][resource] for resource in CAMPAIGN_RESOURCES}
            for owner in OBJECTIVE_OWNERS
            if owner in active_owners
        },
    }


def _control_economy_report(facts: dict[str, Any]) -> dict[str, Any] | None:
    control = facts.get("control_economy")
    if control is None:
        return None
    active_id = control.get("active_decision_id")
    active_record = next(
        (record for record in control["records"] if record["decision_id"] == active_id),
        None,
    )
    owner = (active_record or {}).get("objective_owner") or (control.get("active_frontier") or {}).get("primary_objective_owner") or "P0"
    report: dict[str, Any] = {
        "decision_disposition": control["decision_disposition"],
        "active_objective": owner,
        "remaining_control_budget": {cost: remaining for cost, remaining in control["remaining"][owner].items() if remaining != 0},
    }
    if control["decision_disposition"] == "REUSE_EXISTING_DECISION":
        report["reused_decision_id"] = active_id
    elif control["decision_disposition"] == "NEW_DECISION_RECORD":
        report["new_decision_record"] = active_id
    if (active_record or {}).get("stage_audit"):
        audit = active_record["stage_audit"]
        report["stage_audit"] = {
            "stage_identity": audit["stage_identity"],
            "boundary": audit["boundary"],
            "outcome": audit["outcome"],
        }
    blockers, advisories = _finding_projections(control["findings"])
    if blockers:
        report["effective_blockers"] = [
            {
                "finding_id": finding["finding_id"],
                "effective_tier": finding["effective_tier"],
                "active_consumer_identity": finding["active_consumer_identity"],
            }
            for finding in blockers
        ]
    if advisories:
        report["advisories"] = advisories
    return report


def _activation_identity(
    baseline: dict[str, Any],
    current: dict[str, Any],
    budgets: tuple[int, int, int],
    allow_final_start: bool,
) -> str:
    facts = current["facts"]
    repo = current.get("repo") or {}
    return _digest(
        {
            "baseline_snapshot_sha256": baseline["snapshot_sha256"],
            "current_snapshot_sha256": current["snapshot_sha256"],
            "head": repo.get("head"),
            "observed_repository_identity": repo.get("changed_paths_sha256"),
            "allowed_path_tokens": repo.get("allowed_path_tokens", []),
            "allowed_object_ids": facts.get("allowed_object_ids", []),
            "protected_content_identity": facts.get("protected_content_identity"),
            "authority_status": facts.get("authority_status"),
            "authority_revision_count": facts.get("authority_revision_count"),
            "authority_revision_identity": facts.get("authority_revision_identity"),
            "lineage": current["lineage"],
            "campaign_budget": _campaign_budget_report(facts),
            "control_economy": _control_economy_report(facts),
            "compare_budgets": budgets,
            "allow_final_start": allow_final_start,
        }
    )


def _recommended_outcome(violations: list[dict[str, Any]]) -> str:
    if not violations:
        return "CONTINUE"
    if all(violation["code"] in REBASE_REQUIRED_CODES for violation in violations):
        return "REBASE_REQUIRED"
    return "BLOCKED"


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
        "NOT_APPLICABLE",
        "ACTIVATED",
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
    before, after = baseline["facts"], current["facts"]
    before_completed = before.get("completed_mutation_count")
    after_completed = after.get("completed_mutation_count")
    mutation_delta = after_completed - before_completed if isinstance(before_completed, int) and isinstance(after_completed, int) and after_completed >= before_completed else 0
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
        head_changed = before_repo.get("head") != after_repo.get("head")
        if head_changed and mutation_delta == 0:
            _add_violation(out, "WORKTREE_HEAD_CHANGED", before=before_repo.get("head"), after=after_repo.get("head"))
            _add_violation(out, "ACTIVATION_STATE_DRIFT", drifted_component="HEAD")
        before_allowed = set(before_repo.get("allowed_path_tokens", []))
        after_allowed = set(after_repo.get("allowed_path_tokens", []))
        if before_allowed != after_allowed:
            out.append(_violation("ALLOWED_PATH_SET_CHANGED"))
        outside = sorted(set(after_repo.get("changed_path_tokens", [])) - set(before_repo.get("changed_path_tokens", [])) - before_allowed)
        if outside:
            out.append(_violation("FROZEN_PATH_SET_EXPANDED", count=len(outside), path_tokens=outside))

    if before.get("project_token") != after.get("project_token"):
        out.append(_violation("PROJECT_CHANGED"))
    if before.get("campaign_token") != after.get("campaign_token"):
        out.append(_violation("CAMPAIGN_CHANGED"))
    if before.get("rescue_deadline_at") != after.get("rescue_deadline_at"):
        out.append(_violation("RESCUE_DEADLINE_CHANGED"))
    for violation in _campaign_control_violations(before):
        out.append({**violation, "code": f"BASELINE_{violation['code']}"})
    out.extend(_campaign_control_violations(after))
    out.extend(_campaign_control_compare(before, after))
    converted_v7_blockers = baseline["lineage"].get("schema_upgrade_count") == 1 and set(before.get("blocker_ids", [])) <= set(
        _tokens("blocker", [finding["finding_id"] for finding in (after.get("control_economy") or {}).get("findings", [])])
    )
    for violation in _control_economy_violations(before):
        if violation["code"] != "CONTROL_FINDINGS_REQUIRED" or not converted_v7_blockers:
            out.append({**violation, "code": f"BASELINE_{violation['code']}"})
    out.extend(_control_economy_compare(baseline, current))
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
        _increase(out, before.get("planned_mutation_count"), after.get("planned_mutation_count"), "PLANNED_MUTATION_COUNT_INCREASED")
        b, a = before.get("completed_mutation_count"), after.get("completed_mutation_count")
        _regression(out, b, a, "COMPLETED_MUTATION_COUNT_REGRESSED")
        _increase(out, before.get("remaining_mutation_count"), after.get("remaining_mutation_count"), "REMAINING_MUTATION_COUNT_INCREASED")
        if isinstance(b, int) and isinstance(a, int) and a - b > max_hotfix_delta:
            out.append(_violation("MUTATION_BUDGET_DELTA_EXCEEDED", delta=a - b, allowed=max_hotfix_delta))
        if isinstance(b, int) and isinstance(a, int) and a > b:
            repo_dirty = isinstance(after_repo, dict) and (after_repo.get("tracked_changed_count", 0) > 0 or after_repo.get("untracked_count", 0) > 0)
            if repo_dirty:
                _add_violation(
                    out, "DIRTY_MUTATION_COUNTED_COMPLETED", tracked_changed_count=after_repo.get("tracked_changed_count"), untracked_count=after_repo.get("untracked_count")
                )
            generation_advanced = (isinstance(before_repo, dict) and isinstance(after_repo, dict) and before_repo.get("head") != after_repo.get("head")) or (
                isinstance(after.get("change_generation"), str) and after.get("change_generation") != before.get("change_generation")
            )
            if not generation_advanced:
                out.append(_violation("MUTATION_COMPLETED_WITHOUT_GENERATION_ADVANCE"))
            evidence_fresh = _validation_clean(after) and after.get("validation_evidence_identity") != before.get("validation_evidence_identity")
            if not evidence_fresh:
                out.append(_violation("MUTATION_COMPLETED_WITHOUT_FRESH_VALIDATION"))
    if "control_events" in old_caps | new_caps:
        b, a = before.get("control_event_count"), after.get("control_event_count")
        _regression(out, b, a, "CONTROL_EVENT_COUNT_REGRESSED")
        if isinstance(b, int) and isinstance(a, int) and a - b > max_event_delta:
            out.append(_violation("CONTROL_EVENT_BUDGET_EXCEEDED", delta=a - b, allowed=max_event_delta))
    if "delegation" in old_caps | new_caps:
        new_tasks = sorted(set(after.get("delegated_task_ids", [])) - set(before.get("delegated_task_ids", [])))
        if new_tasks:
            out.append(_violation("DELEGATED_TASK_SET_EXPANDED", count=len(new_tasks)))
        _increase(out, before.get("delegated_task_count"), after.get("delegated_task_count"), "DELEGATED_TASK_DENOMINATOR_INCREASED")
        _regression(out, before.get("subagent_spawn_count"), after.get("subagent_spawn_count"), "SUBAGENT_SPAWN_COUNT_REGRESSED")
        limit = MODES.get(current.get("mode"), {}).get("subagents", 0)
        if current.get("mode") == "RESCUE" and before.get("independent_authority_review_required") is True:
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
        if before.get("independent_authority_review_required") != after.get("independent_authority_review_required"):
            out.append(_violation("AUTHORITY_REVIEW_REQUIREMENT_CHANGED"))
        b, a = before.get("authority_revision_count"), after.get("authority_revision_count")
        _regression(out, b, a, "AUTHORITY_REVISION_COUNT_REGRESSED")
        authority_changed = before.get("authority_status") != after.get("authority_status") or before.get("authority_revision_identity") != after.get("authority_revision_identity")
        if authority_changed:
            out.append(_violation("AUTHORITY_REVISION_REQUIRES_ACCEPTED_REBASE"))
        if before.get("authority_status") == "REJECTED" and isinstance(b, int) and isinstance(a, int) and a > b:
            out.append(_violation("REJECTED_AUTHORITY_BRANCH_REOPENED_WITHOUT_REBASE"))
    if "object_scope" in old_caps | new_caps:
        before_allowed = set(before.get("allowed_object_ids", []))
        after_allowed = set(after.get("allowed_object_ids", []))
        if before_allowed != after_allowed:
            out.append(_violation("ALLOWED_OBJECT_SET_CHANGED"))
        outside = sorted(set(after.get("changed_object_ids", [])) - set(before.get("changed_object_ids", [])) - before_allowed)
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
        _regression(out, before.get("run_state_terminal_count"), after.get("run_state_terminal_count"), "RUN_STATE_TERMINAL_COUNT_REGRESSED")
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
