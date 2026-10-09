# ruff: noqa: F821
"""Deterministic fixtures and property checks for closure_guard."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import closure_guard_core as _core
import tempfile

globals().update({name: value for name, value in vars(_core).items() if not name.startswith("__")})


def _run_cli_json(*args: str) -> tuple[int, dict[str, Any]]:
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("closure_guard.py")), *args],
        cwd=Path(__file__).parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"CLI returned non-JSON output: rc={completed.returncode} "
            f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
        ) from exc
    return completed.returncode, payload


def _test_control_economy() -> dict[str, Any]:
    return {
        "envelope_identity": "CONTROL-ENVELOPE-1",
        "origin_identity": "CONTROL-ORIGIN-1",
        "objective_scope_identity": "CONTROL-SCOPE-1",
        "stop_point_identity": "CONTROL-STOP-1",
        "limits": {"P0": {cost: 32 for cost in CONTROL_COSTS}},
        "records": [],
    }


def _test_snapshot(facts: dict[str, Any], mode: str = "STANDARD") -> dict[str, Any]:
    facts = dict(facts)
    legacy_events = facts.pop("control_event_count", 0)
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
    if mode in {"STANDARD", "RESCUE"} or legacy_events:
        defaults["control_economy"] = _test_control_economy()
    normalized = _normalize({**defaults, **facts})
    normalized = _finalize_control_economy(normalized, None, legacy_control_event_count=legacy_events)
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
            "schema_upgrade_from": None,
            "schema_upgrade_parent_snapshot_sha256": None,
            "schema_upgrade_count": 0,
        },
    }
    snapshot["snapshot_sha256"] = _digest(snapshot)
    _validate_snapshot(snapshot, "test snapshot")
    return snapshot


def _reseal_test_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    snapshot.pop("snapshot_sha256", None)
    snapshot["snapshot_sha256"] = _digest(snapshot)
    return snapshot


def _test_campaign_control(
    *,
    envelope: str = "ENVELOPE-1",
    scope: str = "OBJECTIVE-SCOPE-1",
    origin_mutations: int = 0,
    origin_starts: int = 0,
    absolute_mutations: int = 3,
    absolute_starts: int = 2,
    p0_mutations: int = 2,
    p0_starts: int = 1,
    s1_mutations: int = 1,
    s1_starts: int = 1,
    consumed: dict[str, dict[str, int]] | None = None,
    attempts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    zero = {owner: {resource: 0 for resource in CAMPAIGN_RESOURCES} for owner in OBJECTIVE_OWNERS}
    return {
        "envelope_identity": envelope,
        "origin_identity": "ORIGIN-1",
        "objective_scope_identity": scope,
        "origin_completed_mutation_count": origin_mutations,
        "origin_expensive_start_count": origin_starts,
        "absolute_limits": {
            "mutations": absolute_mutations,
            "expensive_starts": absolute_starts,
        },
        "objective_limits": {
            "P0": {"mutations": p0_mutations, "expensive_starts": p0_starts},
            "S1": {"mutations": s1_mutations, "expensive_starts": s1_starts},
            "S2": {"mutations": 0, "expensive_starts": 0},
            "S3": {"mutations": 0, "expensive_starts": 0},
        },
        "objective_consumed": consumed or zero,
        "attempt_records": attempts or [],
    }


def _test_attempt(
    attempt_id: str,
    owner: str,
    key_char: str,
    status: str = "ACTIVE",
) -> dict[str, Any]:
    return {
        "attempt_id": attempt_id,
        "objective_owner": owner,
        "equivalence_key_sha256": key_char * 64,
        "start_identity": f"START-{attempt_id}",
        "status": status,
        "terminal_evidence_identity": None if status == "ACTIVE" else f"TERMINAL-{attempt_id}",
    }


def _raw_control_from_snapshot(snapshot: dict[str, Any], request: dict[str, Any] | None = None) -> dict[str, Any]:
    control = snapshot["facts"]["control_economy"]
    return {
        "envelope_identity": control["envelope_identity"],
        "origin_identity": control["origin_identity"],
        "objective_scope_identity": control["objective_scope_identity"],
        "stop_point_identity": control["stop_point_identity"],
        "limits": control["limits"],
        "records": control["records"],
        "decision_request": request,
        "active_frontier": control["active_frontier"],
        "findings": [{key: value for key, value in finding.items() if key not in {"effective_tier", "advisory_code"}} for finding in control["findings"]],
        "classification_sets": control["classification_sets"],
        "surface_budget": None,
    }


def _test_decision_request(*, reuse: str | None = None, owner: str = "P0", action: str = "DISPATCH") -> dict[str, Any]:
    return {
        "objective_owner": owner,
        "action_class": action,
        "active_consumer_identity": "ACTIVE-CONSUMER",
        "validator_identity": "VALIDATOR-1",
        "authority_identity": "AUTHORITY-1",
        "trust_boundary_identity": "TRUST-1",
        "protected_constraint_identity": None,
        "costs": ["BLOCKING_GATE"],
        "effect": "CHANGE_MATERIAL_ACTION",
        "reuse_decision_id": reuse,
    }


def _test_frontier(
    *,
    primary: str = "READY",
    recovery: str = "DORMANT",
    terminal: str | None = None,
    generation: str = "G0",
) -> dict[str, Any]:
    return {
        "frontier_identity": "FRONTIER-1",
        "primary_objective_owner": "P0",
        "primary_state": primary,
        "primary_generation_identity": generation,
        "primary_consumer_identity": "PRIMARY-CONSUMER",
        "primary_terminal_status": terminal,
        "recovery_state": recovery,
        "recovery_consumer_identity": "RECOVERY-CONSUMER" if recovery != "NOT_APPLICABLE" else None,
        "recovery_activation_reason": None,
        "recovery_activation_identity": None,
    }


def _test_finding(
    *,
    finding_id: str,
    role: str = "PRIMARY",
    consumer: str | None = None,
    protected: str | None = None,
    owner: str = "P0",
    reachability: str = "REACHABLE",
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "objective_owner": owner,
        "claimed_tier": "HARD_FAIL",
        "reachability": reachability,
        "frontier_role": role,
        "decision_effect": "CHANGE_MATERIAL_ACTION",
        "evidence_identity": f"EVIDENCE-{finding_id}",
        "active_consumer_identity": consumer,
        "protected_constraint_identity": protected,
        "p0_edge_identity": None,
    }


def _test_classification(identity: str, denominator: str, count: int = 3) -> dict[str, Any]:
    return {
        "classification_id": identity,
        "structural_rule_identity": "STRUCTURAL-RULE",
        "production_mechanism_identity": "PRODUCER-MECHANISM",
        "producer_identity": "PRODUCER",
        "execution_purpose_identity": "EXECUTION-PURPOSE",
        "trust_route_identity": "TRUST-ROUTE",
        "classifier_identity": "CLASSIFIER",
        "denominator_identity": denominator,
        "denominator_kind": "IMMUTABLE_FINITE",
        "denominator_count": count,
        "disposition_counts": {
            "HARD_FAIL": 0,
            "REVIEW_REQUIRED": 0,
            "WARNING": 0,
            "INFO": count,
        },
        "active_consumer_closure_identity": "CONSUMER-CLOSURE",
        "terminal_evidence_identity": f"TERMINAL-{denominator}",
        "complete": True,
    }


def _test_surface(*, extra_gate: bool = False) -> dict[str, Any]:
    return {
        "control_responsibilities": ["CLOSURE"],
        "canonical_control_routes": ["CORE"],
        "blocking_gates": ["BASE", *(["EXTRA"] if extra_gate else [])],
        "recovery_branches": [],
        "durable_control_artifacts": [],
        "control_surface_identity": "SURFACE-2" if extra_gate else "SURFACE-1",
    }


def _test_stage_audit(
    boundary: str,
    *,
    predecessor: str | None = None,
    outcome: str = "PASS",
    generation: str = "G0",
) -> dict[str, Any]:
    return {
        "stage_identity": "FRONTIER-1",
        "boundary": boundary,
        "stage_generation_identity": generation,
        "deliverable_identity": f"DELIVERABLE-{boundary}",
        "audit_evidence_identity": f"AUDIT-{boundary}-{outcome}",
        "outcome": outcome,
        "predecessor_audit_decision_id": predecessor,
    }


def _test_stage_request(
    boundary: str,
    *,
    predecessor: str | None = None,
    outcome: str = "PASS",
    owner: str = "P0",
    generation: str = "G0",
) -> dict[str, Any]:
    request = _test_decision_request(
        owner=owner,
        action=STAGE_ACTIONS[boundary],
    )
    request["active_consumer_identity"] = "PRIMARY-CONSUMER"
    request["costs"] = []
    request["effect"] = "ADVANCE_VALIDATION"
    request["stage_audit"] = _test_stage_audit(
        boundary,
        predecessor=predecessor,
        outcome=outcome,
        generation=generation,
    )
    return request


def _test_codes(before: dict[str, Any], after: dict[str, Any], *, allow_final: bool = False) -> set[str]:
    budget = MODES[after["mode"]]
    return {
        x["code"]
        for x in compare(
            before,
            after,
            max_event_delta=budget["events"],
            max_hotfix_delta=budget["mutations"],
            max_expensive_start_delta=budget["expensive"],
            allow_final_start=allow_final,
        )
    }


def _assert_guard_input_error(expected_code: str, action: Any, failure_message: str) -> None:
    try:
        action()
    except GuardInputError as exc:
        assert exc.code == expected_code
    else:
        raise AssertionError(failure_message)


def _assert_value_error(
    action: Any, failure_message: str, *, expected_text: str | None = None
) -> None:
    try:
        action()
    except ValueError as exc:
        if expected_text is not None:
            assert expected_text in str(exc)
    else:
        raise AssertionError(failure_message)


def _test_normalization_schema_invariants() -> dict[str, Any]:
    small0 = _test_snapshot(
        {
            "project_id": "code",
            "change_generation": "G0",
            "closure_item_ids": ["B1"],
            "open_item_ids": ["B1"],
            "planned_mutation_count": 1,
            "completed_mutation_count": 0,
            "validation_rank": 0,
            "capabilities": ["validation_execution"],
        },
        "LIGHT",
    )
    small1 = _test_snapshot(
        {
            "project_id": "code",
            "change_generation": "G1",
            "closure_item_ids": ["B1"],
            "open_item_ids": [],
            "planned_mutation_count": 1,
            "completed_mutation_count": 1,
            "validation_rank": 2,
            "validation_discovered_count": 1,
            "validation_executed_count": 1,
            "validation_passed_count": 1,
            "validation_failed_count": 0,
            "validation_error_count": 0,
            "validation_skipped_count": 0,
            "validation_xfail_count": 0,
            "validation_xpass_count": 0,
            "validation_evidence_identity": "VALIDATION-G1",
            "validation_outer_terminal_status": "COMPLETED",
        },
        "LIGHT",
    )
    assert not _test_codes(small0, small1)
    expanded = _test_snapshot(
        {
            "project_id": "code",
            "closure_item_ids": ["B1", "B2"],
            "open_item_ids": ["B2"],
            "planned_mutation_count": 2,
            "completed_mutation_count": 1,
            "validation_rank": 2,
        },
        "LIGHT",
    )
    assert {"CLOSURE_ITEM_SET_EXPANDED", "PLANNED_MUTATION_COUNT_INCREASED"} <= _test_codes(small1, expanded)
    migration0 = _test_snapshot({"project_id": "migration", "change_generation": "E1", "validation_rank": 1})
    migration1 = _test_snapshot({"project_id": "migration", "change_generation": "E1", "validation_rank": 3})
    assert not _test_codes(migration0, migration1)
    science0 = _test_snapshot(
        {
            "project_id": "science",
            "authority_status": "REJECTED",
            "authority_revision_count": 1,
            "authority_revision_identity": "AUTHORITY-1",
        }
    )
    science1 = _test_snapshot(
        {
            "project_id": "science",
            "authority_status": "PROPOSED",
            "authority_revision_count": 2,
            "authority_revision_identity": "AUTHORITY-2",
        }
    )
    assert "REJECTED_AUTHORITY_BRANCH_REOPENED_WITHOUT_REBASE" in _test_codes(science0, science1)
    release_base = {
        "project_id": "release",
        "closure_item_ids": ["R"],
        "open_item_ids": [],
        "planned_mutation_count": 1,
        "completed_mutation_count": 1,
        "validation_level": "ACCEPTANCE",
        "validation_rank": 4,
        "validation_discovered_count": 1,
        "validation_executed_count": 1,
        "validation_passed_count": 1,
        "validation_failed_count": 0,
        "validation_error_count": 0,
        "validation_skipped_count": 0,
        "validation_xfail_count": 0,
        "validation_xpass_count": 0,
        "validation_evidence_identity": "VALIDATION",
        "validation_outer_terminal_status": "COMPLETED",
        "active_mutator_count": 0,
        "active_expensive_run_count": 0,
        "expensive_start_count": 0,
        "writer_free": True,
        "writer_proof_identity": "WRITER",
        "boundary_smoke_status": "PASS",
        "boundary_smoke_identity": "SMOKE",
        "authority_status": "NOT_APPLICABLE",
        "blocker_ids": [],
        "capabilities": ["blockers"],
    }
    release0 = _test_snapshot({**release_base, "final_boundary_start_count": 0})
    release1 = _test_snapshot({**release_base, "final_boundary_start_count": 1})
    assert "FINAL_BOUNDARY_STARTED_BEFORE_GUARD_RELEASE" in _test_codes(release0, release1)
    assert not _test_codes(release0, release1, allow_final=True)
    delegated0 = _test_snapshot(
        {
            "project_id": "delegated",
            "delegated_task_ids": ["D1"],
            "subagent_spawn_count": 0,
            "active_subagent_count": 0,
            "active_subagent_mutator_count": 0,
            "active_subagent_expensive_run_count": 0,
            "recursive_delegation_count": 0,
        }
    )
    delegated1 = _test_snapshot(
        {
            "project_id": "delegated",
            "delegated_task_ids": ["D1"],
            "subagent_spawn_count": 1,
            "active_subagent_count": 1,
            "active_subagent_mutator_count": 0,
            "active_subagent_expensive_run_count": 0,
            "recursive_delegation_count": 0,
        }
    )
    assert not _test_codes(delegated0, delegated1)
    delegated_bad = _test_snapshot(
        {
            "project_id": "delegated",
            "delegated_task_ids": ["D1", "D2", "D3"],
            "subagent_spawn_count": 3,
            "active_subagent_count": 3,
            "active_subagent_mutator_count": 1,
            "active_subagent_expensive_run_count": 1,
            "recursive_delegation_count": 1,
        }
    )
    assert {
        "DELEGATED_TASK_SET_EXPANDED",
        "DELEGATED_TASK_DENOMINATOR_INCREASED",
        "ACTIVE_SUBAGENT_LIMIT_EXCEEDED",
        "DELEGATED_MUTATION_PROHIBITED",
        "DELEGATED_EXPENSIVE_RUN_PROHIBITED",
        "RECURSIVE_DELEGATION_PROHIBITED",
    } <= _test_codes(delegated1, delegated_bad)
    rescue0 = _test_snapshot(
        {
            "project_id": "rescue",
            "delegated_task_ids": ["D1", "D2"],
            "active_subagent_count": 0,
            "subagent_spawn_count": 0,
            "active_subagent_mutator_count": 0,
            "active_subagent_expensive_run_count": 0,
            "recursive_delegation_count": 0,
        },
        "RESCUE",
    )
    rescue2 = _test_snapshot(
        {
            "project_id": "rescue",
            "delegated_task_ids": ["D1", "D2"],
            "active_subagent_count": 2,
            "subagent_spawn_count": 2,
            "active_subagent_mutator_count": 0,
            "active_subagent_expensive_run_count": 0,
            "recursive_delegation_count": 0,
        },
        "RESCUE",
    )
    assert "ACTIVE_SUBAGENT_LIMIT_EXCEEDED" in _test_codes(rescue0, rescue2)
    review0 = _test_snapshot(
        {
            "project_id": "review",
            "delegated_task_ids": ["D1", "D2"],
            "active_subagent_count": 0,
            "subagent_spawn_count": 0,
            "active_subagent_mutator_count": 0,
            "active_subagent_expensive_run_count": 0,
            "recursive_delegation_count": 0,
            "independent_authority_review_required": True,
            "authority_status": "UNRESOLVED",
        },
        "RESCUE",
    )
    review2 = _test_snapshot(
        {
            "project_id": "review",
            "delegated_task_ids": ["D1", "D2"],
            "active_subagent_count": 2,
            "subagent_spawn_count": 2,
            "active_subagent_mutator_count": 0,
            "active_subagent_expensive_run_count": 0,
            "recursive_delegation_count": 0,
            "independent_authority_review_required": True,
            "authority_status": "UNRESOLVED",
        },
        "RESCUE",
    )
    assert "ACTIVE_SUBAGENT_LIMIT_EXCEEDED" not in _test_codes(review0, review2)
    regressed0 = _test_snapshot(
        {
            "project_id": "monotonic",
            "planned_mutation_count": 2,
            "completed_mutation_count": 2,
            "control_event_count": 4,
            "active_expensive_run_count": 0,
            "expensive_start_count": 3,
            "final_boundary_start_count": 1,
            "authority_revision_count": 2,
            "authority_status": "UNRESOLVED",
            "subagent_spawn_count": 1,
            "delegated_task_count": 1,
            "active_subagent_count": 0,
            "active_subagent_mutator_count": 0,
            "active_subagent_expensive_run_count": 0,
            "recursive_delegation_count": 0,
        }
    )
    regressed1 = _test_snapshot(
        {
            "project_id": "monotonic",
            "planned_mutation_count": 2,
            "completed_mutation_count": 1,
            "control_event_count": 3,
            "active_expensive_run_count": 0,
            "expensive_start_count": 2,
            "final_boundary_start_count": 0,
            "authority_revision_count": 1,
            "authority_status": "UNRESOLVED",
            "subagent_spawn_count": 0,
            "delegated_task_count": 1,
            "active_subagent_count": 0,
            "active_subagent_mutator_count": 0,
            "active_subagent_expensive_run_count": 0,
            "recursive_delegation_count": 0,
        }
    )
    assert {
        "COMPLETED_MUTATION_COUNT_REGRESSED",
        "CONTROL_EVENT_COUNT_REGRESSED",
        "EXPENSIVE_START_COUNT_REGRESSED",
        "FINAL_BOUNDARY_START_COUNT_REGRESSED",
        "AUTHORITY_REVISION_COUNT_REGRESSED",
        "SUBAGENT_SPAWN_COUNT_REGRESSED",
    } <= _test_codes(regressed0, regressed1, allow_final=True)
    delta0 = _test_snapshot(
        {
            "project_id": "single-compare-budget",
            "planned_mutation_count": 4,
            "completed_mutation_count": 1,
            "expensive_start_count": 2,
            "active_expensive_run_count": 0,
        }
    )
    delta_within = _test_snapshot(
        {
            "project_id": "single-compare-budget",
            "planned_mutation_count": 4,
            "completed_mutation_count": 3,
            "expensive_start_count": 3,
            "active_expensive_run_count": 0,
        }
    )
    within_codes = {
        row["code"]
        for row in compare(
            delta0,
            delta_within,
            max_event_delta=0,
            max_hotfix_delta=2,
            max_expensive_start_delta=1,
            allow_final_start=False,
        )
    }
    assert "MUTATION_BUDGET_DELTA_EXCEEDED" not in within_codes
    assert "EXPENSIVE_RUN_BUDGET_EXCEEDED" not in within_codes
    delta_over = _test_snapshot(
        {
            "project_id": "single-compare-budget",
            "planned_mutation_count": 4,
            "completed_mutation_count": 4,
            "expensive_start_count": 4,
            "active_expensive_run_count": 0,
        }
    )
    over_codes = {
        row["code"]
        for row in compare(
            delta0,
            delta_over,
            max_event_delta=0,
            max_hotfix_delta=2,
            max_expensive_start_delta=1,
            allow_final_start=False,
        )
    }
    assert {
        "MUTATION_BUDGET_DELTA_EXCEEDED",
        "EXPENSIVE_RUN_BUDGET_EXCEEDED",
    } <= over_codes
    _assert_value_error(
        lambda: _normalize({"closure_item_ids": ["B1"], "open_item_ids": ["B2"]}),
        'open_item_ids accepted outside closure_item_ids',
        expected_text=None,
    )
    git0 = _test_snapshot({"project_id": "git-drift"})
    repo_token = _tokens("repo", ["repo"])[0]
    planned_path_token = _tokens("path", ["P1"])[0]
    outside_path_token = _tokens("path", ["P2"])[0]
    git0["repo"] = {
        "repo_token": repo_token,
        "head": "H1",
        "tracked_changed_count": 0,
        "untracked_count": 0,
        "tracked_path_tokens": [],
        "untracked_path_tokens": [],
        "changed_path_tokens": [],
        "allowed_path_tokens": [planned_path_token],
        "allowed_path_count": 1,
        "dirty_records": {},
        "changed_paths_sha256": _digest([[], []]),
    }
    _reseal_test_snapshot(git0)
    generic_repo = json.loads(json.dumps(git0))
    generic_repo["facts"]["capabilities"] = sorted(set(generic_repo["facts"]["capabilities"]) | {"vcs"})
    _reseal_test_snapshot(generic_repo)
    _validate_snapshot(generic_repo, "generic facts with repository")
    git1 = {**git0, "repo": {**git0["repo"], "head": "H2"}}
    _reseal_test_snapshot(git1)
    assert {"WORKTREE_HEAD_CHANGED", "ACTIVATION_STATE_DRIFT"} <= _test_codes(git0, git1)
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
    _assert_value_error(
        lambda: _strict_json_text('{"a": 1, "a": 2}', "test JSON"),
        'duplicate JSON key accepted',
        expected_text=None,
    )
    object0 = _test_snapshot(
        {
            "project_id": "objects",
            "changed_object_ids": ["OLD"],
            "allowed_object_ids": ["TARGET"],
            "protected_content_identity": "P1",
        }
    )
    object1 = _test_snapshot(
        {
            "project_id": "objects",
            "changed_object_ids": ["OLD", "TARGET"],
            "allowed_object_ids": ["TARGET"],
            "protected_content_identity": "P1",
        }
    )
    assert "FROZEN_OBJECT_SET_EXPANDED" not in _test_codes(object0, object1)
    object_bad = _test_snapshot(
        {
            "project_id": "objects",
            "changed_object_ids": ["OLD", "ADJACENT"],
            "allowed_object_ids": ["TARGET"],
            "protected_content_identity": "P2",
        }
    )
    assert {"FROZEN_OBJECT_SET_EXPANDED", "PROTECTED_CONTENT_CHANGED"} <= _test_codes(object0, object_bad)
    skipped = _test_snapshot(
        {
            "project_id": "validation",
            "validation_discovered_count": 1,
            "validation_executed_count": 0,
            "validation_passed_count": 0,
            "validation_failed_count": 0,
            "validation_error_count": 0,
            "validation_skipped_count": 1,
            "validation_xfail_count": 0,
            "validation_xpass_count": 0,
            "validation_evidence_identity": "V1",
            "validation_outer_terminal_status": "COMPLETED",
        }
    )
    assert "VALIDATION_COMPLETED_WITHOUT_CLEAN_EXECUTION" in _test_codes(skipped, skipped)
    state_bad = _test_snapshot(
        {
            "project_id": "state",
            "run_state_head_identity": "H1",
            "run_state_terminal_count": 1,
            "run_state_replay_verified": False,
            "run_state_projection_matches_replay": False,
            "duplicate_start_count": 1,
            "old_transaction_resume_count": 1,
        }
    )
    assert {
        "RUN_STATE_REPLAY_NOT_VERIFIED",
        "RUN_STATE_PROJECTION_MISMATCH",
        "DUPLICATE_START_DETECTED",
        "OLD_TRANSACTION_RESUME_DETECTED",
    } <= _test_codes(state_bad, state_bad)
    incomplete_release = _test_snapshot(
        {
            "project_id": "incomplete-release",
            "final_boundary_start_count": 0,
        }
    )
    incomplete_started = _test_snapshot(
        {
            "project_id": "incomplete-release",
            "final_boundary_start_count": 1,
        }
    )
    assert "FINAL_RELEASE_FACTS_INCOMPLETE" in _test_codes(incomplete_release, incomplete_started, allow_final=True)
    successor = {
        **release0,
        "lineage": {
            **release0["lineage"],
            "parent_snapshot_sha256": release0["snapshot_sha256"],
            "accepted_rebaseline_count": 1,
        },
    }
    _reseal_test_snapshot(successor)
    assert not _rebaseline_violations(release0, successor)
    reset = {**successor, "facts": {**successor["facts"], "completed_mutation_count": 0}}
    _reseal_test_snapshot(reset)
    assert "REBASE_RESET_COMPLETED_MUTATIONS" in {row["code"] for row in _rebaseline_violations(release0, reset)}

    _assert_value_error(
        lambda: _normalize(
            {
                "project_id": "empty-standard",
                "capabilities": [
                    "closure_items",
                    "mutations",
                    "validation_ladder",
                    "mutators",
                ],
            }
        ),
        'empty STANDARD capability shell was accepted',
        expected_text='capability shell lacks applicable facts',
    )
    for capability in CAPABILITY_REQUIRED_FACTS:
        _assert_value_error(
            lambda: _normalize(
                {
                    "project_id": f"empty-{capability}",
                    "capabilities": [capability],
                }
            ),
            f'empty {capability} capability shell was accepted',
            expected_text='capability shell lacks applicable facts',
        )
    _assert_value_error(
        lambda: _test_snapshot({"project_id": "generic-vcs", "capabilities": ["vcs"]}, "LIGHT"),
        'generic vcs capability shell was accepted',
        expected_text='vcs capability lacks repository facts',
    )
    mismatched_open = json.loads(json.dumps(small0))
    mismatched_open["facts"]["open_item_ids"] = _tokens("closure_item", ["B2"])
    _reseal_test_snapshot(mismatched_open)
    _assert_value_error(
        lambda: _validate_snapshot(mismatched_open, "mismatched open identities"),
        'open-item identity outside closure set was accepted',
        expected_text='open-item identities exceed closure identities',
    )
    return small0


def _test_identity_scope_invariants() -> dict[str, Any]:
    capability_predecessor = _test_snapshot({"project_id": "rebase-capability"})
    capability_successor = _test_snapshot({"project_id": "rebase-capability"}, "LIGHT")
    assert "REBASE_ERASED_CAPABILITIES" in {row["code"] for row in _rebaseline_violations(capability_predecessor, capability_successor)}

    closed_predecessor = _test_snapshot(
        {
            "project_id": "rebase-reopen",
            "closure_item_ids": ["C1"],
            "open_item_ids": [],
            "planned_mutation_count": 1,
            "completed_mutation_count": 0,
        },
        "LIGHT",
    )
    reopened_successor = _test_snapshot(
        {
            "project_id": "rebase-reopen",
            "closure_item_ids": ["C1"],
            "open_item_ids": ["C1"],
            "planned_mutation_count": 1,
            "completed_mutation_count": 0,
        },
        "LIGHT",
    )
    assert "REBASE_REOPENED_CLOSURE_ITEMS" in {row["code"] for row in _rebaseline_violations(closed_predecessor, reopened_successor)}
    count_predecessor = _test_snapshot(
        {
            "project_id": "rebase-count",
            "closure_item_count": 2,
            "open_item_count": 0,
            "closed_item_count": 2,
        },
        "LIGHT",
    )
    count_successor = _test_snapshot(
        {
            "project_id": "rebase-count",
            "closure_item_count": 2,
            "open_item_count": 1,
            "closed_item_count": 1,
        },
        "LIGHT",
    )
    assert "REBASE_REOPENED_CLOSURE_ITEMS" in {row["code"] for row in _rebaseline_violations(count_predecessor, count_successor)}

    wash_predecessor = _test_snapshot(
        {
            "project_id": "rebase-budget",
            "planned_mutation_count": 4,
            "completed_mutation_count": 0,
            "control_event_count": 0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
        }
    )
    wash_successor = _test_snapshot(
        {
            "project_id": "rebase-budget",
            "planned_mutation_count": 4,
            "completed_mutation_count": 2,
            "control_event_count": 5,
            "active_expensive_run_count": 0,
            "expensive_start_count": 2,
        }
    )
    assert {
        "REBASE_MUTATION_DELTA_EXCEEDED",
        "REBASE_CONTROL_EVENT_DELTA_EXCEEDED",
        "REBASE_EXPENSIVE_START_DELTA_EXCEEDED",
    } <= {row["code"] for row in _rebaseline_violations(wash_predecessor, wash_successor)}

    legal_predecessor = _test_snapshot(
        {
            "project_id": "legal-rebase",
            "closure_item_ids": ["C1"],
            "open_item_ids": [],
            "planned_mutation_count": 1,
            "completed_mutation_count": 0,
            "validation_rank": 0,
            "active_mutator_count": 0,
            "authority_status": "ACTIVATED",
            "authority_revision_count": 1,
            "authority_revision_identity": "AUTHORITY-1",
        },
        "LIGHT",
    )
    legal_successor = _test_snapshot(
        {
            "project_id": "legal-rebase",
            "closure_item_ids": ["C1", "C2"],
            "open_item_ids": ["C2"],
            "planned_mutation_count": 2,
            "completed_mutation_count": 0,
            "validation_rank": 0,
            "active_mutator_count": 0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "writer_free": True,
            "writer_proof_identity": "WRITER-2",
            "control_event_count": 0,
            "authority_status": "ACTIVATED",
            "authority_revision_count": 2,
            "authority_revision_identity": "AUTHORITY-2",
        },
        "LIGHT",
    )
    assert not _rebaseline_violations(legal_predecessor, legal_successor)

    _assert_value_error(
        lambda: _normalize({"authority_status": "ACTIVE"}),
        'event-style authority status was accepted',
        expected_text=None,
    )
    return legal_predecessor


def _test_campaign_budget_invariants() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    campaign0 = _test_snapshot(
        {
            "project_id": "campaign-control",
            "planned_mutation_count": 3,
            "completed_mutation_count": 0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "change_generation": "G0",
            "capabilities": ["validation_execution"],
            "campaign_control": _test_campaign_control(),
        }
    )
    p0_consumed = {
        "P0": {"mutations": 1, "expensive_starts": 1},
        "S1": {"mutations": 0, "expensive_starts": 0},
        "S2": {"mutations": 0, "expensive_starts": 0},
        "S3": {"mutations": 0, "expensive_starts": 0},
    }
    campaign1 = _test_snapshot(
        {
            "project_id": "campaign-control",
            "planned_mutation_count": 3,
            "completed_mutation_count": 1,
            "active_expensive_run_count": 1,
            "expensive_start_count": 1,
            "change_generation": "G1",
            "validation_discovered_count": 1,
            "validation_executed_count": 1,
            "validation_passed_count": 1,
            "validation_failed_count": 0,
            "validation_error_count": 0,
            "validation_skipped_count": 0,
            "validation_xfail_count": 0,
            "validation_xpass_count": 0,
            "validation_evidence_identity": "VALIDATION-G1",
            "validation_outer_terminal_status": "COMPLETED",
            "campaign_control": _test_campaign_control(consumed=p0_consumed, attempts=[_test_attempt("A1", "P0", "1")]),
        }
    )
    assert not _test_codes(campaign0, campaign1)
    campaign_budget = _campaign_budget_report(campaign1["facts"])
    assert campaign_budget is not None
    assert campaign_budget["absolute_limits"] == {"mutations": 3, "expensive_starts": 2}
    assert campaign_budget["remaining_total"] == {"mutations": 2, "expensive_starts": 1}

    campaign_terminal = _test_snapshot(
        {
            "project_id": "campaign-control",
            "planned_mutation_count": 3,
            "completed_mutation_count": 1,
            "active_expensive_run_count": 0,
            "expensive_start_count": 1,
            "change_generation": "G1",
            "validation_discovered_count": 1,
            "validation_executed_count": 1,
            "validation_passed_count": 1,
            "validation_failed_count": 0,
            "validation_error_count": 0,
            "validation_skipped_count": 0,
            "validation_xfail_count": 0,
            "validation_xpass_count": 0,
            "validation_evidence_identity": "VALIDATION-G1",
            "validation_outer_terminal_status": "COMPLETED",
            "campaign_control": _test_campaign_control(
                consumed=p0_consumed,
                attempts=[_test_attempt("A1", "P0", "1", "COMPLETED")],
            ),
        }
    )
    assert not _test_codes(campaign1, campaign_terminal)
    second_consumed = {
        "P0": {"mutations": 1, "expensive_starts": 1},
        "S1": {"mutations": 0, "expensive_starts": 1},
        "S2": {"mutations": 0, "expensive_starts": 0},
        "S3": {"mutations": 0, "expensive_starts": 0},
    }
    distinct_attempt = _test_snapshot(
        {
            "project_id": "campaign-control",
            "planned_mutation_count": 3,
            "completed_mutation_count": 1,
            "active_expensive_run_count": 1,
            "expensive_start_count": 2,
            "change_generation": "G1",
            "validation_discovered_count": 1,
            "validation_executed_count": 1,
            "validation_passed_count": 1,
            "validation_failed_count": 0,
            "validation_error_count": 0,
            "validation_skipped_count": 0,
            "validation_xfail_count": 0,
            "validation_xpass_count": 0,
            "validation_evidence_identity": "VALIDATION-G1",
            "validation_outer_terminal_status": "COMPLETED",
            "campaign_control": _test_campaign_control(
                consumed=second_consumed,
                attempts=[
                    _test_attempt("A1", "P0", "1", "COMPLETED"),
                    _test_attempt("A2", "S1", "2"),
                ],
            ),
        }
    )
    assert not _test_codes(campaign_terminal, distinct_attempt)
    _assert_guard_input_error(
        'MACHINE_COUNT_CONFLICT',
        lambda: _test_snapshot(
            {
                "project_id": "campaign-control",
                "planned_mutation_count": 3,
                "completed_mutation_count": 1,
                "active_expensive_run_count": 0,
                "expensive_start_count": 2,
                "campaign_control": _test_campaign_control(
                    consumed=second_consumed,
                    attempts=[
                        _test_attempt("A1", "P0", "1", "COMPLETED"),
                        _test_attempt("A2", "P0", "2", "COMPLETED"),
                    ],
                ),
            }
        ),
        'attempt owner/count conflict was accepted',
    )
    rewritten_terminal = _test_snapshot(
        {
            "project_id": "campaign-control",
            "planned_mutation_count": 3,
            "completed_mutation_count": 1,
            "active_expensive_run_count": 0,
            "expensive_start_count": 1,
            "campaign_control": _test_campaign_control(
                consumed=p0_consumed,
                attempts=[_test_attempt("A1", "P0", "1", "FAILED_TYPED")],
            ),
        }
    )
    assert "ATTEMPT_TERMINAL_REWRITTEN" in _test_codes(campaign_terminal, rewritten_terminal)

    duplicate_consumed = {
        **p0_consumed,
        "S1": {"mutations": 0, "expensive_starts": 1},
    }
    duplicate_attempt = _test_snapshot(
        {
            "project_id": "campaign-control",
            "planned_mutation_count": 3,
            "completed_mutation_count": 1,
            "active_expensive_run_count": 1,
            "expensive_start_count": 2,
            "campaign_control": _test_campaign_control(
                consumed=duplicate_consumed,
                attempts=[
                    _test_attempt("A1", "P0", "1", "COMPLETED"),
                    _test_attempt("A2", "S1", "1"),
                ],
            ),
        }
    )
    assert "EXPENSIVE_ATTEMPT_KEY_REUSED" in _test_codes(campaign_terminal, duplicate_attempt)

    mixed_consumed = {
        "P0": {"mutations": 1, "expensive_starts": 0},
        "S1": {"mutations": 0, "expensive_starts": 1},
        "S2": {"mutations": 0, "expensive_starts": 0},
        "S3": {"mutations": 0, "expensive_starts": 0},
    }
    mixed_action = _test_snapshot(
        {
            "project_id": "campaign-control",
            "planned_mutation_count": 3,
            "completed_mutation_count": 1,
            "active_expensive_run_count": 1,
            "expensive_start_count": 1,
            "campaign_control": _test_campaign_control(consumed=mixed_consumed, attempts=[_test_attempt("M1", "S1", "2")]),
        }
    )
    assert "CROSS_OBJECTIVE_ACTION_MIXED" in _test_codes(campaign0, mixed_action)

    owner_mismatch_consumed = {
        "P0": {"mutations": 0, "expensive_starts": 1},
        "S1": {"mutations": 0, "expensive_starts": 0},
        "S2": {"mutations": 0, "expensive_starts": 0},
        "S3": {"mutations": 0, "expensive_starts": 0},
    }
    _assert_guard_input_error(
        'MACHINE_COUNT_CONFLICT',
        lambda: _test_snapshot(
            {
                "project_id": "campaign-control",
                "planned_mutation_count": 3,
                "completed_mutation_count": 0,
                "active_expensive_run_count": 1,
                "expensive_start_count": 1,
                "campaign_control": _test_campaign_control(
                    consumed=owner_mismatch_consumed,
                    attempts=[_test_attempt("O1", "S1", "3")],
                ),
            }
        ),
        'attempt owner/budget mismatch was accepted',
    )

    accounting_bad = json.loads(json.dumps(campaign0))
    accounting_bad["facts"]["completed_mutation_count"] = 1
    accounting_bad["facts"]["remaining_mutation_count"] = 2
    _reseal_test_snapshot(accounting_bad)
    assert "OBJECTIVE_BUDGET_ACCOUNTING_MISMATCH" in _test_codes(campaign0, accounting_bad)
    repaired_consumption = {
        "P0": {"mutations": 1, "expensive_starts": 0},
        "S1": {"mutations": 0, "expensive_starts": 0},
        "S2": {"mutations": 0, "expensive_starts": 0},
        "S3": {"mutations": 0, "expensive_starts": 0},
    }
    accounting_repaired = _test_snapshot(
        {
            "project_id": "campaign-control",
            "planned_mutation_count": 3,
            "completed_mutation_count": 1,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "campaign_control": _test_campaign_control(consumed=repaired_consumption),
        }
    )
    assert "REBASE_PREDECESSOR_OBJECTIVE_BUDGET_ACCOUNTING_MISMATCH" in {row["code"] for row in _rebaseline_violations(accounting_bad, accounting_repaired)}
    over_consumed = {
        "P0": {"mutations": 3, "expensive_starts": 0},
        "S1": {"mutations": 1, "expensive_starts": 0},
        "S2": {"mutations": 0, "expensive_starts": 0},
        "S3": {"mutations": 0, "expensive_starts": 0},
    }
    over_budget_facts = _test_snapshot(
        {
            "project_id": "campaign-control",
            "planned_mutation_count": 4,
            "completed_mutation_count": 4,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "campaign_control": _test_campaign_control(consumed=over_consumed),
        }
    )["facts"]
    assert {
        "ABSOLUTE_MUTATION_BUDGET_EXCEEDED",
        "OBJECTIVE_BUDGET_EXCEEDED",
    } <= {row["code"] for row in _campaign_control_violations(over_budget_facts)}

    rebase_campaign = _test_snapshot(
        {
            "project_id": "campaign-control",
            "planned_mutation_count": 3,
            "completed_mutation_count": 0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "campaign_control": _test_campaign_control(envelope="ENVELOPE-2", p0_mutations=3, s1_mutations=0),
        }
    )
    assert not _campaign_control_rebaseline_violations(campaign0["facts"], rebase_campaign["facts"])
    envelope_only_rebase = _test_snapshot(
        {
            "project_id": "campaign-control",
            "planned_mutation_count": 3,
            "completed_mutation_count": 0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "campaign_control": _test_campaign_control(envelope="ENVELOPE-2"),
        }
    )
    assert not _campaign_control_rebaseline_violations(campaign0["facts"], envelope_only_rebase["facts"])
    rebase_p0_reduced = _test_snapshot(
        {
            "project_id": "campaign-control",
            "planned_mutation_count": 3,
            "completed_mutation_count": 0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "campaign_control": _test_campaign_control(envelope="ENVELOPE-2", p0_mutations=1, s1_mutations=2),
        }
    )
    assert "REBASE_REDUCED_P0_BUDGET" in {row["code"] for row in _campaign_control_rebaseline_violations(campaign0["facts"], rebase_p0_reduced["facts"])}
    reset_consumption = json.loads(json.dumps(campaign_terminal))
    reset_consumption["facts"]["campaign_control"]["envelope_identity"] = "ENVELOPE-2"
    reset_consumption["facts"]["campaign_control"]["objective_consumed"]["P0"]["mutations"] = 0
    assert "REBASE_RESET_OBJECTIVE_CONSUMPTION" in {row["code"] for row in _campaign_control_rebaseline_violations(campaign_terminal["facts"], reset_consumption["facts"])}
    rebase_limit_drift = _test_snapshot(
        {
            "project_id": "campaign-control",
            "planned_mutation_count": 3,
            "completed_mutation_count": 0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "campaign_control": _test_campaign_control(
                envelope="ENVELOPE-2",
                absolute_mutations=4,
                p0_mutations=3,
                s1_mutations=1,
            ),
        }
    )
    assert "REBASE_CHANGED_ABSOLUTE_LIMITS" in {row["code"] for row in _campaign_control_rebaseline_violations(campaign0["facts"], rebase_limit_drift["facts"])}
    normal_origin_drift = json.loads(json.dumps(campaign0))
    normal_origin_drift["facts"]["campaign_control"]["origin_identity"] = "ORIGIN-2"
    _reseal_test_snapshot(normal_origin_drift)
    assert "CAMPAIGN_ORIGIN_DRIFT" in _test_codes(campaign0, normal_origin_drift)
    normal_scope_drift = _test_snapshot(
        {
            "project_id": "campaign-control",
            "planned_mutation_count": 3,
            "completed_mutation_count": 0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "campaign_control": _test_campaign_control(scope="OBJECTIVE-SCOPE-2"),
        }
    )
    assert "OBJECTIVE_SCOPE_DRIFT" in _test_codes(campaign0, normal_scope_drift)
    assert "CAMPAIGN_ABSOLUTE_LIMITS_DRIFT" in _test_codes(campaign0, rebase_limit_drift)
    assert _recommended_outcome([_violation("CAMPAIGN_ORIGIN_DRIFT")]) == "BLOCKED"
    assert _recommended_outcome([_violation("CAMPAIGN_ABSOLUTE_LIMITS_DRIFT")]) == "BLOCKED"
    assert _recommended_outcome([_violation("OBJECTIVE_SCOPE_DRIFT")]) == "REBASE_REQUIRED"
    assert (
        _recommended_outcome(
            [
                _violation("CAMPAIGN_ORIGIN_DRIFT"),
                _violation("OBJECTIVE_SCOPE_DRIFT"),
            ]
        )
        == "BLOCKED"
    )
    assert (
        _recommended_outcome(
            [
                _violation("CAMPAIGN_ABSOLUTE_LIMITS_DRIFT"),
                _violation("CAMPAIGN_ENVELOPE_DRIFT"),
            ]
        )
        == "BLOCKED"
    )

    core_sparse = _normalize({"project_id": "core-only"})
    assert core_sparse["campaign_control"] is None
    assert core_sparse["completed_mutation_count"] is None
    assert core_sparse["independent_authority_review_required"] is False
    assert "authority" not in core_sparse["capabilities"]
    for machine_field in ("head", "head_tree", "dirty_paths", "dirty_records", "lineage"):
        _assert_guard_input_error(
            'MACHINE_FACT_OVERRIDE_PROHIBITED',
            lambda: _normalize({"project_id": "override", machine_field: "manual"}),
            f'manual machine fact was accepted: {machine_field}',
        )
    _assert_guard_input_error(
        'MACHINE_COUNT_CONFLICT',
        lambda: _normalize(
            {
                "project_id": "count-conflict",
                "closure_item_ids": ["C1"],
                "closure_item_count": 2,
            }
        ),
        'manual count conflict was accepted',
    )

    sparse_control = {
        "envelope_identity": "ENVELOPE-1",
        "origin_identity": "ORIGIN-1",
        "objective_scope_identity": "OBJECTIVE-SCOPE-1",
        "origin_completed_mutation_count": 0,
        "origin_expensive_start_count": 0,
        "objective_limits": {
            "P0": {"mutations": 2, "expensive_starts": 1},
            "S1": {"mutations": 1, "expensive_starts": 1},
        },
        "attempt_records": [],
    }
    sparse_normalized = _normalize(
        {
            "project_id": "sparse-campaign",
            "planned_mutation_count": 3,
            "completed_mutation_count": 0,
            "campaign_control": sparse_control,
        }
    )
    full_normalized = _normalize(
        {
            "project_id": "sparse-campaign",
            "planned_mutation_count": 3,
            "completed_mutation_count": 0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "campaign_control": _test_campaign_control(),
        }
    )
    assert sparse_normalized == full_normalized
    started_sparse = json.loads(json.dumps(sparse_control))
    started_sparse["attempt_records"] = [_test_attempt("SPARSE-A1", "P0", "a")]
    started_normalized = _normalize(
        {
            "project_id": "sparse-start",
            "planned_mutation_count": 3,
            "completed_mutation_count": 0,
            "campaign_control": started_sparse,
        }
    )
    assert started_normalized["expensive_start_count"] == 1
    assert started_normalized["active_expensive_run_count"] == 1
    assert started_normalized["campaign_control"]["objective_consumed"]["P0"]["expensive_starts"] == 1
    return campaign0, campaign1, distinct_attempt


def _test_rebaseline_attempt_invariants(
    small0: dict[str, Any],
    legal_predecessor: dict[str, Any],
    campaign0: dict[str, Any],
    campaign1: dict[str, Any],
    distinct_attempt: dict[str, Any],
) -> None:
    unauthorized_scope = _test_snapshot(
        {
            "project_id": "legal-rebase",
            "closure_item_ids": ["C1", "C2"],
            "open_item_ids": ["C2"],
            "planned_mutation_count": 2,
            "completed_mutation_count": 0,
            "validation_rank": 0,
            "active_mutator_count": 0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "writer_free": True,
            "writer_proof_identity": "WRITER-2",
            "authority_status": "ACTIVATED",
            "authority_revision_count": 1,
            "authority_revision_identity": "AUTHORITY-1",
        },
        "LIGHT",
    )
    unauthorized_codes = {row["code"] for row in _rebaseline_violations(legal_predecessor, unauthorized_scope)}
    assert "REBASE_AUTHORITY_REVISION_NOT_ADVANCED" in unauthorized_codes
    pre_campaign = _test_snapshot(
        {
            "project_id": "campaign-activation",
            "planned_mutation_count": 3,
            "completed_mutation_count": 0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
        },
        "LIGHT",
    )
    post_campaign = _test_snapshot(
        {
            "project_id": "campaign-activation",
            "planned_mutation_count": 3,
            "completed_mutation_count": 0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "campaign_control": _test_campaign_control(),
        },
        "LIGHT",
    )
    assert "REBASE_SCOPE_DELTA_AUTHORITY_REQUIRED" in {row["code"] for row in _rebaseline_violations(pre_campaign, post_campaign)}
    authorized_campaign = _test_snapshot(
        {
            "project_id": "campaign-activation",
            "planned_mutation_count": 3,
            "completed_mutation_count": 0,
            "active_mutator_count": 0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "writer_free": True,
            "writer_proof_identity": "WRITER-CAMPAIGN",
            "authority_status": "ACTIVATED",
            "authority_revision_count": 1,
            "authority_revision_identity": "AUTHORITY-CAMPAIGN-1",
            "campaign_control": _test_campaign_control(),
        },
        "LIGHT",
    )
    assert not _rebaseline_violations(pre_campaign, authorized_campaign)
    mutation_without_generation = _test_snapshot(
        {
            "project_id": "code",
            "change_generation": "G0",
            "closure_item_ids": ["B1"],
            "open_item_ids": [],
            "planned_mutation_count": 1,
            "completed_mutation_count": 1,
            "validation_rank": 2,
            "validation_discovered_count": 1,
            "validation_executed_count": 1,
            "validation_passed_count": 1,
            "validation_failed_count": 0,
            "validation_error_count": 0,
            "validation_skipped_count": 0,
            "validation_xfail_count": 0,
            "validation_xpass_count": 0,
            "validation_evidence_identity": "VALIDATION-G1",
            "validation_outer_terminal_status": "COMPLETED",
        },
        "LIGHT",
    )
    assert "MUTATION_COMPLETED_WITHOUT_GENERATION_ADVANCE" in _test_codes(small0, mutation_without_generation)
    mutation_without_validation = _test_snapshot(
        {
            "project_id": "code",
            "change_generation": "G1",
            "closure_item_ids": ["B1"],
            "open_item_ids": [],
            "planned_mutation_count": 1,
            "completed_mutation_count": 1,
            "validation_rank": 2,
            "capabilities": ["validation_execution"],
        },
        "LIGHT",
    )
    assert "MUTATION_COMPLETED_WITHOUT_FRESH_VALIDATION" in _test_codes(small0, mutation_without_validation)
    late_scope = _test_snapshot(
        {
            "project_id": "legal-rebase",
            "change_generation": "G1",
            "closure_item_ids": ["C1", "C2"],
            "open_item_ids": ["C2"],
            "planned_mutation_count": 2,
            "completed_mutation_count": 1,
            "validation_rank": 1,
            "validation_discovered_count": 1,
            "validation_executed_count": 1,
            "validation_passed_count": 1,
            "validation_failed_count": 0,
            "validation_error_count": 0,
            "validation_skipped_count": 0,
            "validation_xfail_count": 0,
            "validation_xpass_count": 0,
            "validation_evidence_identity": "LATE-VALIDATION",
            "validation_outer_terminal_status": "COMPLETED",
            "active_mutator_count": 0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "writer_free": True,
            "writer_proof_identity": "WRITER-2",
            "authority_status": "ACTIVATED",
            "authority_revision_count": 2,
            "authority_revision_identity": "AUTHORITY-2",
        },
        "LIGHT",
    )
    assert "REBASE_SCOPE_EXPANSION_AFTER_MUTATION_STARTED" in {row["code"] for row in _rebaseline_violations(legal_predecessor, late_scope)}
    owner_scope = _test_snapshot(
        {
            "project_id": "campaign-control",
            "planned_mutation_count": 3,
            "completed_mutation_count": 0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "campaign_control": _test_campaign_control(envelope="ENVELOPE-2", scope="OBJECTIVE-SCOPE-2"),
        }
    )
    assert "OWNER_CHANGE_REQUIRES_ARCHITECTURE_REBASE" in {row["code"] for row in _rebaseline_violations(campaign0, owner_scope)}

    closure_root = _test_snapshot(
        {
            "project_id": "closure-lineage",
            "closure_item_ids": ["ROOT"],
            "open_item_ids": ["ROOT"],
            "planned_mutation_count": 1,
            "completed_mutation_count": 0,
        },
        "LIGHT",
    )
    split_closure = _test_snapshot(
        {
            "project_id": "closure-lineage",
            "closure_item_ids": ["ROOT", "A", "B"],
            "open_item_ids": ["ROOT", "A", "B"],
            "planned_mutation_count": 1,
            "completed_mutation_count": 0,
        },
        "LIGHT",
    )
    superseded_closure = _test_snapshot(
        {
            "project_id": "closure-lineage",
            "closure_item_ids": ["ROOT", "NEXT"],
            "open_item_ids": ["NEXT"],
            "planned_mutation_count": 1,
            "completed_mutation_count": 0,
        },
        "LIGHT",
    )
    for candidate in (split_closure, superseded_closure):
        assert "REBASE_CLOSURE_LINEAGE_UNPROVABLE" in {row["code"] for row in _rebaseline_violations(closure_root, candidate)}
    merge_root = _test_snapshot(
        {
            "project_id": "closure-merge",
            "closure_item_ids": ["A", "B"],
            "open_item_ids": ["A", "B"],
            "planned_mutation_count": 1,
            "completed_mutation_count": 0,
        },
        "LIGHT",
    )
    merged_closure = _test_snapshot(
        {
            "project_id": "closure-merge",
            "closure_item_ids": ["A", "B", "MERGED"],
            "open_item_ids": ["MERGED"],
            "planned_mutation_count": 1,
            "completed_mutation_count": 0,
        },
        "LIGHT",
    )
    assert "REBASE_CLOSURE_LINEAGE_UNPROVABLE" in {row["code"] for row in _rebaseline_violations(merge_root, merged_closure)}
    renamed_closure = _test_snapshot(
        {
            "project_id": "closure-lineage",
            "closure_item_ids": ["RENAMED"],
            "open_item_ids": ["RENAMED"],
            "planned_mutation_count": 1,
            "completed_mutation_count": 0,
        },
        "LIGHT",
    )
    assert "REBASE_ERASED_CLOSURE_ITEMS" in {row["code"] for row in _rebaseline_violations(closure_root, renamed_closure)}

    assert "ORPHAN_ACTIVE_ATTEMPT_REQUIRES_RECONCILIATION" in _test_codes(campaign1, distinct_attempt)
    for old_status in sorted(ATTEMPT_STATUSES - {"ACTIVE"}):
        for new_status in sorted(ATTEMPT_STATUSES - {"ACTIVE", old_status}):
            before_attempt = {"attempt_records": [_test_attempt("T", "P0", "b", old_status)]}
            after_attempt = {"attempt_records": [_test_attempt("T", "P0", "b", new_status)]}
            assert "ATTEMPT_TERMINAL_REWRITTEN" in {row["code"] for row in _attempt_transition_violations(before_attempt, after_attempt)}
    for before_value in range(1, 5):
        regression: list[dict[str, Any]] = []
        _regression(regression, before_value, before_value - 1, "PROPERTY_REGRESSION")
        assert regression and regression[0]["code"] == "PROPERTY_REGRESSION"
    for code in (
        "REBASE_SCOPE_DELTA_AUTHORITY_REQUIRED",
        "DIRTY_MUTATION_COUNTED_COMPLETED",
        "ORPHAN_ACTIVE_ATTEMPT_REQUIRES_RECONCILIATION",
        "UNKNOWN_TYPED_FAILURE",
    ):
        assert _violation(code).get("minimum_legal_next_action")


def _test_decision_stage_invariants() -> tuple[dict[str, Any], dict[str, Any]]:
    # V9 cumulative-control economy and exact-key behavior.
    _assert_guard_input_error(
        'MACHINE_COUNT_OVERRIDE_PROHIBITED',
        lambda: _normalize({"project_id": "manual-count", "control_event_count": 1}),
        'manual V9 control_event_count was accepted',
    )
    missing_control = _test_snapshot({"project_id": "missing-control"}, "LIGHT")
    missing_control["mode"] = "STANDARD"
    _reseal_test_snapshot(missing_control)
    _assert_guard_input_error(
        'CONTROL_ECONOMY_REQUIRED',
        lambda: _validate_snapshot(missing_control, "missing control economy"),
        'STANDARD without control economy was accepted',
    )

    decision0 = _test_snapshot(
        {
            "project_id": "decision-economy",
            "change_generation": "G0",
        }
    )
    key_repo = {"head": "HEAD-1", "changed_paths_sha256": "STATE-1", "changed_path_tokens": [], "allowed_path_tokens": []}
    assert _control_state_key(decision0["facts"], {**key_repo, "repo_token": "DIRECTORY-A"}, decision0["facts"]["control_economy"]) == _control_state_key(
        decision0["facts"], {**key_repo, "repo_token": "DIRECTORY-B"}, decision0["facts"]["control_economy"]
    )
    first_control = _raw_control_from_snapshot(decision0, _test_decision_request())
    decision1 = _test_snapshot(
        {
            "project_id": "decision-economy",
            "change_generation": "G0",
            "control_economy": first_control,
        }
    )
    assert not _test_codes(decision0, decision1)
    assert decision1["facts"]["control_event_count"] == 1
    decision_id = decision1["facts"]["control_economy"]["active_decision_id"]
    _assert_guard_input_error(
        'CONTROL_DECISION_KEY_REUSED',
        lambda: _test_snapshot(
            {
                "project_id": "decision-economy",
                "change_generation": "G0",
                "control_economy": _raw_control_from_snapshot(decision1, _test_decision_request()),
            }
        ),
        'exact decision key created a duplicate record',
    )
    reused = _test_snapshot(
        {
            "project_id": "decision-economy",
            "change_generation": "G0",
            "control_economy": _raw_control_from_snapshot(decision1, _test_decision_request(reuse=decision_id)),
        }
    )
    assert not _test_codes(decision1, reused)
    assert reused["facts"]["control_economy"]["decision_disposition"] == ("REUSE_EXISTING_DECISION")
    assert len(reused["facts"]["control_economy"]["records"]) == 1
    relabeled_request = _test_decision_request()
    relabeled_request["effect"] = "ADVANCE_VALIDATION"
    _assert_guard_input_error(
        'CONTROL_DECISION_KEY_REUSED',
        lambda: _test_snapshot(
            {
                "project_id": "decision-economy",
                "change_generation": "G0",
                "control_economy": _raw_control_from_snapshot(decision1, relabeled_request),
            }
        ),
        'effect relabel created a duplicate decision key',
    )
    relabeled_request["reuse_decision_id"] = decision_id
    _assert_guard_input_error(
        'CONTROL_DECISION_REUSE_INVALID',
        lambda: _test_snapshot(
            {
                "project_id": "decision-economy",
                "change_generation": "G0",
                "control_economy": _raw_control_from_snapshot(decision1, relabeled_request),
            }
        ),
        'effect relabel changed a reused decision conclusion',
    )
    changed_key = _test_snapshot(
        {
            "project_id": "decision-economy",
            "change_generation": "G1",
            "control_economy": _raw_control_from_snapshot(decision1, _test_decision_request()),
        }
    )
    assert "CONTROL_DECISION_KEY_REUSED" not in _test_codes(decision1, changed_key)
    assert len(changed_key["facts"]["control_economy"]["records"]) == 2
    assert "CROSS_OBJECTIVE_CONTROL_COST" in _test_codes(decision0, changed_key)
    assert "CONTROL_RECORD_HISTORY_REGRESSED" in _test_codes(decision1, decision0)
    for key_field, changed_identity in (("validator_identity", "VALIDATOR-2"), ("trust_boundary_identity", "TRUST-2")):
        changed_request = _test_decision_request()
        changed_request[key_field] = changed_identity
        changed_control = _raw_control_from_snapshot(decision1, changed_request)
        changed_identity_snapshot = _test_snapshot({"project_id": "decision-economy", "change_generation": "G0", "control_economy": changed_control})
        assert len(changed_identity_snapshot["facts"]["control_economy"]["records"]) == 2

    # V9 reuses the decision chain for one design and one build audit per
    # material stage boundary; it does not create an audit ledger or gate.
    stage_control = _test_control_economy()
    stage_control["active_frontier"] = _test_frontier(primary="PREPARING")
    stage0 = _test_snapshot(
        {
            "project_id": "stage-convergence",
            "change_generation": "G0",
            "control_economy": stage_control,
        }
    )
    design_request = _test_stage_request("DESIGN_COMPLETE")
    design1 = _test_snapshot(
        {
            "project_id": "stage-convergence",
            "change_generation": "G0",
            "control_economy": _raw_control_from_snapshot(stage0, design_request),
        }
    )
    assert not _test_codes(stage0, design1)
    design_id = design1["facts"]["control_economy"]["active_decision_id"]
    assert design1["facts"]["control_economy"]["records"][-1]["stage_audit"]["boundary"] == "DESIGN_COMPLETE"
    assert _control_economy_report(design1["facts"])["stage_audit"]["outcome"] == "PASS"

    reused_design_request = _test_stage_request("DESIGN_COMPLETE")
    reused_design_request["reuse_decision_id"] = design_id
    reused_design = _test_snapshot(
        {
            "project_id": "stage-convergence",
            "change_generation": "G0",
            "control_economy": _raw_control_from_snapshot(design1, reused_design_request),
        }
    )
    assert not _test_codes(design1, reused_design)
    assert len(reused_design["facts"]["control_economy"]["records"]) == 1

    relabeled_audit = _test_stage_request("DESIGN_COMPLETE")
    relabeled_audit["stage_audit"]["outcome"] = "REDUCTION_REQUIRED"
    _assert_guard_input_error(
        'CONTROL_DECISION_KEY_REUSED',
        lambda: _test_snapshot(
            {
                "project_id": "stage-convergence",
                "change_generation": "G0",
                "control_economy": _raw_control_from_snapshot(design1, relabeled_audit),
            }
        ),
        'stage audit outcome relabel created a new decision',
    )
    relabeled_audit["reuse_decision_id"] = design_id
    _assert_guard_input_error(
        'CONTROL_DECISION_REUSE_INVALID',
        lambda: _test_snapshot(
            {
                "project_id": "stage-convergence",
                "change_generation": "G0",
                "control_economy": _raw_control_from_snapshot(design1, relabeled_audit),
            }
        ),
        'stage audit reuse changed the recorded outcome',
    )

    build_request = _test_stage_request(
        "BUILD_COMPLETE",
        predecessor=design_id,
    )
    build1 = _test_snapshot(
        {
            "project_id": "stage-convergence",
            "change_generation": "G0",
            "control_economy": _raw_control_from_snapshot(design1, build_request),
        }
    )
    assert not _test_codes(design1, build1)
    build_id = build1["facts"]["control_economy"]["active_decision_id"]
    assert build_id != design_id

    ready_control = _raw_control_from_snapshot(build1)
    ready_control["active_frontier"] = _test_frontier(primary="READY")
    ready_stage = _test_snapshot(
        {
            "project_id": "stage-convergence",
            "change_generation": "G0",
            "control_economy": ready_control,
        }
    )
    assert not _test_codes(build1, ready_stage)
    running_control = _raw_control_from_snapshot(ready_stage)
    running_control["active_frontier"] = _test_frontier(primary="RUNNING")
    running_stage = _test_snapshot(
        {
            "project_id": "stage-convergence",
            "change_generation": "G0",
            "control_economy": running_control,
        }
    )
    assert not _test_codes(ready_stage, running_stage)

    missing_build_control = _raw_control_from_snapshot(design1)
    missing_build_control["active_frontier"] = _test_frontier(primary="READY")
    missing_build = _test_snapshot(
        {
            "project_id": "stage-convergence",
            "change_generation": "G0",
            "control_economy": missing_build_control,
        }
    )
    assert "STAGE_BUILD_AUDIT_REQUIRED" in _test_codes(design1, missing_build)

    no_frontier = _test_snapshot({"project_id": "stage-frontier", "change_generation": "G0"})
    new_frontier_control = _raw_control_from_snapshot(no_frontier)
    new_frontier_control["active_frontier"] = _test_frontier(primary="PREPARING")
    unaudited_frontier = _test_snapshot(
        {
            "project_id": "stage-frontier",
            "change_generation": "G0",
            "control_economy": new_frontier_control,
        }
    )
    assert "STAGE_DESIGN_AUDIT_REQUIRED" in _test_codes(no_frontier, unaudited_frontier)

    reduction = _test_snapshot(
        {
            "project_id": "stage-convergence",
            "change_generation": "G0",
            "control_economy": _raw_control_from_snapshot(
                stage0,
                _test_stage_request("DESIGN_COMPLETE", outcome="REDUCTION_REQUIRED"),
            ),
        }
    )
    assert "STAGE_SIMPLICITY_AUDIT_REDUCTION_REQUIRED" in _test_codes(stage0, reduction)
    authority_blocked = _test_snapshot(
        {
            "project_id": "stage-convergence",
            "change_generation": "G0",
            "control_economy": _raw_control_from_snapshot(
                stage0,
                _test_stage_request("DESIGN_COMPLETE", outcome="BLOCKED_AUTHORITY"),
            ),
        }
    )
    assert "STAGE_SIMPLICITY_AUDIT_AUTHORITY_BLOCKED" in _test_codes(
        stage0,
        authority_blocked,
    )

    for invalid_request, expected_code in (
        (_test_decision_request(action="STAGE_DESIGN_AUDIT"), "STAGE_AUDIT_REQUIRED"),
        (_test_stage_request("DESIGN_COMPLETE", generation="OTHER"), "STAGE_AUDIT_CONTEXT_MISMATCH"),
        (_test_stage_request("DESIGN_COMPLETE", owner="S1"), "STAGE_AUDIT_CONTEXT_MISMATCH"),
        (_test_stage_request("BUILD_COMPLETE", predecessor="MISSING"), "STAGE_AUDIT_PREDECESSOR_INVALID"),
    ):
        invalid_request["active_consumer_identity"] = "PRIMARY-CONSUMER"
        _assert_guard_input_error(
            expected_code,
            lambda: _test_snapshot(
                {
                    "project_id": "stage-convergence",
                    "change_generation": "G0",
                    "control_economy": _raw_control_from_snapshot(design1, invalid_request),
                }
            ),
            f'invalid stage audit was accepted: {expected_code}',
        )
    return decision1, reused


def _test_frontier_authority_invariants(
    decision1: dict[str, Any],
    reused: dict[str, Any],
) -> None:
    tight = _test_control_economy()
    tight["limits"] = {"P0": {"DECISION": 1, "BLOCKING_GATE": 1}}
    tight["active_frontier"] = _test_frontier()
    tight0 = _test_snapshot(
        {
            "project_id": "tight-control",
            "change_generation": "G0",
            "control_economy": tight,
        }
    )
    tight1 = _test_snapshot(
        {
            "project_id": "tight-control",
            "change_generation": "G0",
            "control_economy": {
                **tight,
                "decision_request": _test_decision_request(),
            },
        }
    )
    assert not _test_codes(tight0, tight1)
    tight_decision_id = tight1["facts"]["control_economy"]["active_decision_id"]
    tight_reused = _test_snapshot(
        {
            "project_id": "tight-control",
            "change_generation": "G0",
            "control_economy": _raw_control_from_snapshot(tight1, _test_decision_request(reuse=tight_decision_id)),
        }
    )
    assert not _test_codes(tight1, tight_reused)
    assert tight_reused["facts"]["control_economy"]["remaining"]["P0"]["DECISION"] == 0
    tight2_control = _raw_control_from_snapshot(tight1, _test_decision_request())
    tight2 = _test_snapshot(
        {
            "project_id": "tight-control",
            "change_generation": "G1",
            "control_economy": tight2_control,
        }
    )
    assert "CONTROL_BUDGET_EXHAUSTED" in _test_codes(tight1, tight2)

    advisory_control = _test_control_economy()
    advisory_control.update(
        {
            "active_frontier": _test_frontier(),
            "findings": [_test_finding(finding_id="NO-CONSUMER")],
        }
    )
    advisory = _test_snapshot(
        {
            "project_id": "finding-tier",
            "change_generation": "G0",
            "control_economy": advisory_control,
        }
    )
    advisory_report = _control_economy_report(advisory["facts"])
    assert advisory_report and advisory_report["advisories"][0]["code"] == ("GATE_NO_ACTIVE_CONSUMER_DOWNGRADED")
    mismatched_control = _test_control_economy()
    mismatched_control.update(
        {
            "active_frontier": _test_frontier(),
            "findings": [_test_finding(finding_id="WRONG-CONSUMER", consumer="OTHER-CONSUMER")],
        }
    )
    mismatched = _test_snapshot({"project_id": "finding-consumer-binding", "control_economy": mismatched_control})
    assert _control_economy_report(mismatched["facts"])["advisories"][0]["code"] == "GATE_NO_ACTIVE_CONSUMER_DOWNGRADED"
    dormant_control = _test_control_economy()
    dormant_control.update(
        {
            "active_frontier": _test_frontier(),
            "findings": [_test_finding(finding_id="DORMANT", role="RECOVERY", consumer="RECOVERY-CONSUMER")],
        }
    )
    dormant = _test_snapshot(
        {
            "project_id": "dormant-recovery",
            "change_generation": "G0",
            "control_economy": dormant_control,
        }
    )
    assert _control_economy_report(dormant["facts"])["advisories"][0]["code"] == ("DORMANT_RECOVERY_BLOCK_IGNORED")
    secondary_control = _test_control_economy()
    secondary_control.update(
        {
            "active_frontier": _test_frontier(),
            "findings": [_test_finding(finding_id="SECONDARY", owner="S1", consumer="SECONDARY-CONSUMER")],
        }
    )
    secondary = _test_snapshot(
        {
            "project_id": "secondary-finding",
            "change_generation": "G0",
            "control_economy": secondary_control,
        }
    )
    assert "effective_blockers" not in _control_economy_report(secondary["facts"])
    protected_control = _test_control_economy()
    protected_control.update(
        {
            "active_frontier": _test_frontier(),
            "findings": [_test_finding(finding_id="PROTECTED", protected="SAFETY", reachability="UNKNOWN")],
        }
    )
    protected = _test_snapshot(
        {
            "project_id": "protected-finding",
            "change_generation": "G0",
            "control_economy": protected_control,
        }
    )
    assert _effective_blocker_violations(protected["facts"])

    invalid_recovery_control = _test_control_economy()
    invalid_recovery_control["active_frontier"] = _test_frontier(recovery="ACTIVE")
    invalid_recovery = _test_snapshot(
        {
            "project_id": "invalid-recovery",
            "change_generation": "G0",
            "control_economy": invalid_recovery_control,
        }
    )
    assert "RECOVERY_ACTIVATION_NOT_ADMISSIBLE" in {row["code"] for row in _control_economy_violations(invalid_recovery["facts"])}
    _assert_value_error(
        lambda: _active_frontier(_test_frontier(primary="TERMINAL", terminal="UNTYPED")),
        'untyped primary terminal was accepted',
        expected_text=None,
    )

    ready_control0 = _test_control_economy()
    ready_control0["active_frontier"] = _test_frontier(generation="G0")
    ready0 = _test_snapshot(
        {
            "project_id": "ready-freeze",
            "change_generation": "G0",
            "control_economy": ready_control0,
        }
    )
    ready_control1 = _test_control_economy()
    ready_control1["active_frontier"] = _test_frontier(generation="G1")
    ready1 = _test_snapshot(
        {
            "project_id": "ready-freeze",
            "change_generation": "G1",
            "control_economy": ready_control1,
        }
    )
    assert "READY_GENERATION_DRIFT" in _test_codes(ready0, ready1)

    complete_class = _test_classification("CLASS-1", "DENOMINATOR-1")
    class_control0 = _test_control_economy()
    class_control0["classification_sets"] = [complete_class]
    class0 = _test_snapshot(
        {
            "project_id": "classification",
            "control_economy": class_control0,
        }
    )
    drift_class = _test_classification("CLASS-1", "DENOMINATOR-2")
    class_control1 = _test_control_economy()
    class_control1["classification_sets"] = [drift_class]
    class1 = _test_snapshot(
        {
            "project_id": "classification",
            "control_economy": class_control1,
        }
    )
    assert "CLASSIFICATION_SET_DRIFT" in _test_codes(class0, class1)
    next_class_control = _test_control_economy()
    next_class_control["classification_sets"] = [complete_class, _test_classification("CLASS-2", "DENOMINATOR-2")]
    next_class = _test_snapshot(
        {
            "project_id": "classification",
            "control_economy": next_class_control,
        }
    )
    assert "CLASSIFICATION_SET_DRIFT" not in _test_codes(class0, next_class)
    incomplete = _test_classification("CLASS-X", "DENOMINATOR-X")
    incomplete["complete"] = False
    _assert_guard_input_error(
        'CLASSIFICATION_SET_INCOMPLETE',
        lambda: _test_snapshot(
            {
                "project_id": "classification-incomplete",
                "control_economy": {**_test_control_economy(), "classification_sets": [incomplete]},
            }
        ),
        'incomplete all-hit set was accepted',
    )

    surface_control0 = _test_control_economy()
    surface_control0["surface_budget"] = _test_surface()
    surface0 = _test_snapshot(
        {
            "project_id": "surface-budget",
            "control_economy": surface_control0,
        }
    )
    no_surface = _test_snapshot({"project_id": "surface-budget"})
    assert "CONTROL_SURFACE_EXPANSION_REQUIRES_ARCHITECTURE_REBASE" in _test_codes(no_surface, surface0)
    surface_control1 = _test_control_economy()
    surface_control1["surface_budget"] = _test_surface(extra_gate=True)
    surface1 = _test_snapshot(
        {
            "project_id": "surface-budget",
            "control_economy": surface_control1,
        }
    )
    assert "CONTROL_SURFACE_EXPANSION_REQUIRES_ARCHITECTURE_REBASE" in _test_codes(surface0, surface1)

    scope_control = _test_control_economy()
    scope_control.update({"envelope_identity": "CONTROL-ENVELOPE-2", "objective_scope_identity": "CONTROL-SCOPE-2"})
    scope_rebase = _test_snapshot({"project_id": "surface-budget", "control_economy": scope_control})
    assert {"REBASE_SCOPE_DELTA_AUTHORITY_REQUIRED", "OWNER_CHANGE_REQUIRES_ARCHITECTURE_REBASE"} <= {row["code"] for row in _rebaseline_violations(surface0, scope_rebase)}

    authorized_surface0 = _test_snapshot(
        {
            "project_id": "authorized-surface",
            "control_economy": surface_control0,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "writer_free": True,
            "writer_proof_identity": "SURFACE-WRITER-1",
            "authority_status": "ACTIVATED",
            "authority_revision_count": 1,
            "authority_revision_identity": "SURFACE-AUTHORITY-1",
        }
    )
    authorized_surface1_control = _raw_control_from_snapshot(authorized_surface0, _test_decision_request(action="ARCHITECTURE_REBASE"))
    authorized_surface1_control["surface_budget"] = _test_surface(extra_gate=True)
    authorized_surface1 = _test_snapshot(
        {
            "project_id": "authorized-surface",
            "control_economy": authorized_surface1_control,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "writer_free": True,
            "writer_proof_identity": "SURFACE-WRITER-2",
            "authority_status": "ACTIVATED",
            "authority_revision_count": 2,
            "authority_revision_identity": "SURFACE-AUTHORITY-2",
        }
    )
    authority_only_surface1 = json.loads(json.dumps(authorized_surface1))
    authority_only_surface1["facts"]["control_economy"] = surface1["facts"]["control_economy"]
    authority_only_surface1["facts"]["control_event_count"] = 0
    _reseal_test_snapshot(authority_only_surface1)
    assert "CONTROL_SURFACE_EXPANSION_REQUIRES_ARCHITECTURE_REBASE" in {row["code"] for row in _rebaseline_violations(authorized_surface0, authority_only_surface1)}
    assert "CONTROL_SURFACE_EXPANSION_REQUIRES_ARCHITECTURE_REBASE" not in {row["code"] for row in _rebaseline_violations(authorized_surface0, authorized_surface1)}
    duplicate_classes = {**_test_control_economy(), "classification_sets": [complete_class, _test_classification("CLASS-DUPLICATE", "DENOMINATOR-1")]}
    _assert_guard_input_error(
        'CLASSIFICATION_SET_DRIFT',
        lambda: _test_snapshot({"project_id": "classification-duplicate", "control_economy": duplicate_classes}),
        'duplicate classification for one denominator was accepted',
    )
    assert "S1" not in json.dumps(_control_economy_report(decision1["facts"]), sort_keys=True)

    transfer_before_control = _test_control_economy()
    transfer_before_control["limits"] = {"P0": {"DECISION": 1}, "S1": {"DECISION": 1}}
    transfer_before = _test_snapshot({"project_id": "control-transfer", "control_economy": transfer_before_control})
    transfer_after_control = _raw_control_from_snapshot(transfer_before)
    transfer_after_control["envelope_identity"] = "CONTROL-ENVELOPE-2"
    transfer_after_control["limits"] = {"P0": {"DECISION": 2}, "S1": {"DECISION": 0}}
    transfer_after = _test_snapshot({"project_id": "control-transfer", "control_economy": transfer_after_control})
    assert not _control_rebaseline_violations(transfer_before["facts"], transfer_after["facts"])

    pending_blocker_control = _test_control_economy()
    pending_blocker = _test_snapshot(
        {
            "project_id": "pending-blocker-conversion",
            "blocker_ids": ["LEGACY-BLOCKER"],
            "control_economy": pending_blocker_control,
        }
    )
    assert "CONTROL_FINDINGS_REQUIRED" in {row["code"] for row in _control_economy_violations(pending_blocker["facts"])}

    # Decision-record properties: append-only, per-owner, exact-key and budget conservation.
    assert decision1["facts"]["control_economy"]["records"] == reused["facts"]["control_economy"]["records"]
    sparse_limits = {**_test_control_economy(), "limits": {"P0": {"DECISION": 1}}}
    explicit_limits = {**_test_control_economy(), "limits": {owner: {cost: int(owner == "P0" and cost == "DECISION") for cost in CONTROL_COSTS} for owner in OBJECTIVE_OWNERS}}
    assert _normalize_control_economy(sparse_limits) == _normalize_control_economy(explicit_limits)
    for owner in OBJECTIVE_OWNERS:
        for cost in CONTROL_COSTS:
            control = decision1["facts"]["control_economy"]
            assert control["remaining"][owner][cost] == (control["limits"][owner][cost] - control["consumed"][owner][cost])


def _test_repository_path_invariants(temp_root: Path) -> None:
    repo = temp_root / "repo"
    repo.mkdir()
    _run(["git", "init", "-q"], repo)
    (repo / "a.txt").write_text("baseline\n", encoding="utf-8")
    _run(["git", "add", "a.txt"], repo)
    _run(
        [
            "git",
            "-c",
            "user.name=Guard Self Test",
            "-c",
            "user.email=guard@example.invalid",
            "commit",
            "-qm",
            "baseline",
        ],
        repo,
    )
    _assert_guard_input_error(
        'CONTROL_ECONOMY_REQUIRED',
        lambda: capture(repo, None, "git", "STANDARD"),
        'Git-only STANDARD capture bypassed control economy',
    )
    standard_facts_path = temp_root / "standard-facts.json"
    standard_facts_path.write_text(
        json.dumps(
            {
                "project_id": "generic-standard",
                "closure_item_ids": ["BASE"],
                "open_item_ids": ["BASE"],
                "planned_mutation_count": 1,
                "completed_mutation_count": 0,
                "validation_rank": 0,
                "active_mutator_count": 0,
                "control_economy": _test_control_economy(),
            }
        ),
        encoding="utf-8",
    )
    generic_standard = capture(repo, str(standard_facts_path), "generic", "STANDARD")
    assert {"vcs", "control_economy"} <= set(generic_standard["facts"]["capabilities"])
    allowed = temp_root / "allowed.txt"
    allowed.write_text("a.txt\nb.txt\n", encoding="utf-8")
    base_facts_path = temp_root / "base-facts.json"
    base_facts_path.write_text(
        json.dumps(
            {
                "project_id": "generic-repository",
                "change_generation": "G0",
                "planned_mutation_count": 1,
                "completed_mutation_count": 0,
                "capabilities": ["validation_execution"],
            }
        ),
        encoding="utf-8",
    )
    repo_baseline = capture(
        repo,
        str(base_facts_path),
        "generic",
        "LIGHT",
        allowed_paths_from=str(allowed),
    )
    assert "vcs" in repo_baseline["facts"]["capabilities"]
    current_facts_path = temp_root / "current-facts.json"
    current_facts_path.write_text(
        json.dumps(
            {
                "project_id": "generic-repository",
                "change_generation": "G1",
                "planned_mutation_count": 1,
                "completed_mutation_count": 1,
                "validation_discovered_count": 1,
                "validation_executed_count": 1,
                "validation_passed_count": 1,
                "validation_failed_count": 0,
                "validation_error_count": 0,
                "validation_skipped_count": 0,
                "validation_xfail_count": 0,
                "validation_xpass_count": 0,
                "validation_evidence_identity": "REPO-VALIDATION-G1",
                "validation_outer_terminal_status": "COMPLETED",
            }
        ),
        encoding="utf-8",
    )
    (repo / "a.txt").write_text("dirty\n", encoding="utf-8")
    dirty_snapshot_1 = _git(repo)
    dirty_identity_1 = dirty_snapshot_1["changed_paths_sha256"]
    dirty_snapshot_2 = _git(repo, inherited_dirty_records=dirty_snapshot_1["dirty_records"])
    dirty_token = next(iter(dirty_snapshot_1["dirty_records"]))
    assert dirty_identity_1 == dirty_snapshot_2["changed_paths_sha256"]
    assert dirty_snapshot_1["dirty_records"][dirty_token] is dirty_snapshot_2["dirty_records"][dirty_token]
    (repo / "a.txt").write_text("dirty-changed\n", encoding="utf-8")
    changed_snapshot = _git(repo, inherited_dirty_records=dirty_snapshot_1["dirty_records"])
    assert changed_snapshot["changed_paths_sha256"] != dirty_identity_1
    assert changed_snapshot["dirty_records"][dirty_token] is not dirty_snapshot_1["dirty_records"][dirty_token]
    (repo / "a.txt").write_text("dirty\n", encoding="utf-8")
    dirty_current = capture(
        repo,
        str(current_facts_path),
        "generic",
        "LIGHT",
        inherited_allowed_path_tokens=repo_baseline["repo"]["allowed_path_tokens"],
        inherited_lineage=repo_baseline["lineage"],
        comparison_base_head=repo_baseline["repo"]["head"],
    )
    assert "DIRTY_MUTATION_COUNTED_COMPLETED" in {
        row["code"]
        for row in compare(
            repo_baseline,
            dirty_current,
            max_event_delta=0,
            max_hotfix_delta=1,
            max_expensive_start_delta=1,
            allow_final_start=False,
        )
    }
    _run(["git", "add", "a.txt"], repo)
    _run(
        [
            "git",
            "-c",
            "user.name=Guard Self Test",
            "-c",
            "user.email=guard@example.invalid",
            "commit",
            "-qm",
            "mutation",
        ],
        repo,
    )
    committed_current = capture(
        repo,
        str(current_facts_path),
        "generic",
        "LIGHT",
        inherited_allowed_path_tokens=repo_baseline["repo"]["allowed_path_tokens"],
        inherited_lineage=repo_baseline["lineage"],
        comparison_base_head=repo_baseline["repo"]["head"],
    )
    committed_violations = compare(
        repo_baseline,
        committed_current,
        max_event_delta=0,
        max_hotfix_delta=1,
        max_expensive_start_delta=1,
        allow_final_start=False,
    )
    assert not committed_violations
    assert _activation_identity(repo_baseline, committed_current, (0, 1, 1), False) == _activation_identity(repo_baseline, committed_current, (0, 1, 1), False)

    _run(["git", "mv", "a.txt", "b.txt"], repo)
    rename_current = capture(
        repo,
        str(current_facts_path),
        "generic",
        "LIGHT",
        inherited_allowed_path_tokens=repo_baseline["repo"]["allowed_path_tokens"],
        inherited_lineage=repo_baseline["lineage"],
        comparison_base_head=committed_current["repo"]["head"],
    )
    assert set(_tokens("path", ["a.txt", "b.txt"])) <= set(rename_current["repo"]["changed_path_tokens"])
    _run(["git", "mv", "b.txt", "a.txt"], repo)

    _assert_guard_input_error(
        'REPOSITORY_PATH_CASE_COLLISION',
        lambda: _reject_case_collisions(["A.txt", "a.txt"]),
        'case-fold collision was accepted',
    )
    _assert_value_error(
        lambda: _normalize_repo_path(repo, "../escape"),
        'repository path escape was accepted',
        expected_text=None,
    )

    outside_dir = temp_root / "outside-dir"
    outside_dir.mkdir()
    (repo / "linked-dir").symlink_to(outside_dir, target_is_directory=True)
    _assert_guard_input_error(
        'REPOSITORY_SYMLINK_PATH_PROHIBITED',
        lambda: _validate_repo_object(repo, "linked-dir/file.txt", []),
        'intermediate symlink was accepted',
    )
    (repo / "linked-dir").unlink()
    _assert_guard_input_error(
        'REPOSITORY_SUBMODULE_PATH_PROHIBITED',
        lambda: _validate_repo_object(repo, "vendor", ["vendor"]),
        'submodule path was accepted',
    )

    (repo / "link.txt").symlink_to("a.txt")
    _assert_guard_input_error(
        'REPOSITORY_SYMLINK_PATH_PROHIBITED',
        lambda: _git(repo),
        'repository symlink was accepted',
    )
    (repo / "link.txt").unlink()

    outside_file = temp_root / "outside-hardlink-source"
    outside_file.write_text("hardlink\n", encoding="utf-8")
    os.link(outside_file, repo / "hard.txt")
    _assert_guard_input_error(
        'REPOSITORY_HARDLINK_PATH_PROHIBITED',
        lambda: _git(repo),
        'repository hardlink was accepted',
    )
    (repo / "hard.txt").unlink()

    os.mkfifo(repo / "special.pipe")
    _assert_guard_input_error(
        'REPOSITORY_SPECIAL_FILE_PROHIBITED',
        lambda: _validate_repo_object(repo, "special.pipe", []),
        'repository special file was accepted',
    )
    (repo / "special.pipe").unlink()

    index_lock = _git_dir(repo) / "index.lock"
    index_lock.touch()
    _assert_guard_input_error(
        'ACTIVATION_STATE_DRIFT',
        lambda: _git(repo),
        'active Git writer signal was accepted',
    )
    index_lock.unlink()


def _test_import_rebaseline_cli_invariants(temp_root: Path) -> None:
    import_seed = _test_snapshot(
        {
            "project_id": "schema-import",
            "control_event_count": 3,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "writer_free": True,
            "writer_proof_identity": "IMPORT-WRITER",
            "campaign_control": _test_campaign_control(),
        }
    )
    v8_seed = _test_snapshot(
        {
            "project_id": "schema-import",
            "control_event_count": 3,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "writer_free": True,
            "writer_proof_identity": "IMPORT-WRITER",
            "campaign_control": _test_campaign_control(),
            "control_economy": _raw_control_from_snapshot(
                import_seed,
                _test_decision_request(),
            ),
        }
    )
    v8_import = json.loads(json.dumps(v8_seed))
    v8_import["schema_id"] = V8_SCHEMA_ID
    _reseal_test_snapshot(v8_import)
    _validate_snapshot(
        v8_import,
        "V8 import fixture",
        expected_schema=V8_SCHEMA_ID,
    )
    v8_facts_path = temp_root / "v8-import-facts.json"
    v8_facts_path.write_text(
        json.dumps(
            {
                "project_id": "schema-import",
                "closure_item_ids": ["BASE"],
                "open_item_ids": ["BASE"],
                "planned_mutation_count": 1,
                "completed_mutation_count": 0,
                "validation_level": "BASELINE",
                "validation_rank": 0,
                "active_mutator_count": 0,
                "active_expensive_run_count": 0,
                "expensive_start_count": 0,
                "writer_free": True,
                "writer_proof_identity": "IMPORT-WRITER",
                "campaign_control": _test_campaign_control(),
                "control_economy": _raw_control_from_snapshot(v8_import),
            }
        ),
        encoding="utf-8",
    )
    v9_from_v8 = capture(
        None,
        str(v8_facts_path),
        "generic",
        "STANDARD",
        accepted_predecessor=v8_import,
    )
    assert not _v8_upgrade_violations(v8_import, v9_from_v8)
    assert v9_from_v8["lineage"]["schema_upgrade_from"] == V8_SCHEMA_ID
    assert v9_from_v8["lineage"]["schema_upgrade_count"] == 1
    assert v9_from_v8["facts"]["control_economy"]["records"] == v8_import["facts"]["control_economy"]["records"]
    assert "BASELINE_SCHEMA_INCOMPATIBLE" in _test_codes(v8_import, v9_from_v8)
    v8_predecessor_path = temp_root / "v8-predecessor.json"
    v8_predecessor_path.write_text(json.dumps(v8_import), encoding="utf-8")
    v8_cli_code, v8_cli_import = _run_cli_json(
        "snapshot",
        "--facts",
        str(v8_facts_path),
        "--profile",
        "generic",
        "--mode",
        "STANDARD",
        "--predecessor",
        str(v8_predecessor_path),
        "--accept-rebaseline",
    )
    assert v8_cli_code == 0
    assert v8_cli_import["schema_id"] == SCHEMA_ID
    assert v8_cli_import["lineage"]["schema_upgrade_from"] == V8_SCHEMA_ID
    assert v8_cli_import["lineage"]["schema_upgrade_count"] == 1
    v8_history_loss = json.loads(json.dumps(v9_from_v8))
    v8_history_loss["facts"]["control_economy"]["records"] = []
    v8_history_loss["facts"]["control_economy"]["consumed"] = {
        owner: {cost: 0 for cost in CONTROL_COSTS}
        for owner in OBJECTIVE_OWNERS
    }
    v8_history_loss["facts"]["control_economy"]["remaining"] = v8_history_loss["facts"]["control_economy"]["limits"]
    v8_history_loss["facts"]["control_event_count"] = 3
    _reseal_test_snapshot(v8_history_loss)
    assert "V8_UPGRADE_HISTORY_DRIFT" in {
        row["code"]
        for row in _v8_upgrade_violations(v8_import, v8_history_loss)
    }
    v7_import = json.loads(json.dumps(import_seed))
    v7_import["schema_id"] = V7_SCHEMA_ID
    v7_import["facts"].pop("control_economy")
    v7_import["facts"]["capabilities"] = sorted(set(v7_import["facts"]["capabilities"]) - {"control_economy"})
    v7_import["lineage"] = {
        "campaign_token": import_seed["lineage"]["campaign_token"],
        "parent_snapshot_sha256": None,
        "accepted_rebaseline_count": 0,
    }
    _reseal_test_snapshot(v7_import)
    _validate_v7_snapshot(v7_import, "V7 import fixture")
    import_facts_path = temp_root / "import-facts.json"
    import_facts_path.write_text(
        json.dumps(
            {
                "project_id": "schema-import",
                "closure_item_ids": ["BASE"],
                "open_item_ids": ["BASE"],
                "planned_mutation_count": 1,
                "completed_mutation_count": 0,
                "validation_level": "BASELINE",
                "validation_rank": 0,
                "active_mutator_count": 0,
                "active_expensive_run_count": 0,
                "expensive_start_count": 0,
                "writer_free": True,
                "writer_proof_identity": "IMPORT-WRITER",
                "campaign_control": _test_campaign_control(),
                "control_economy": {**_test_control_economy(), "objective_scope_identity": "OBJECTIVE-SCOPE-1"},
            }
        ),
        encoding="utf-8",
    )
    imported = capture(
        None,
        str(import_facts_path),
        "generic",
        "STANDARD",
        accepted_predecessor=v7_import,
    )
    assert not _v7_upgrade_violations(v7_import, imported)
    assert imported["lineage"]["schema_upgrade_count"] == 1
    assert imported["lineage"]["accepted_rebaseline_count"] == 0
    assert imported["facts"]["control_economy"]["legacy_control_event_count"] == 3
    assert "BASELINE_SCHEMA_INCOMPATIBLE" in _test_codes(v7_import, imported)
    v7_predecessor_path = temp_root / "v7-predecessor.json"
    v7_predecessor_path.write_text(json.dumps(v7_import), encoding="utf-8")
    v7_cli_code, v7_cli_import = _run_cli_json(
        "snapshot",
        "--facts",
        str(import_facts_path),
        "--profile",
        "generic",
        "--mode",
        "STANDARD",
        "--predecessor",
        str(v7_predecessor_path),
        "--accept-rebaseline",
    )
    assert v7_cli_code == 0
    assert v7_cli_import["schema_id"] == SCHEMA_ID
    assert v7_cli_import["lineage"]["schema_upgrade_from"] == V7_SCHEMA_ID
    assert v7_cli_import["lineage"]["schema_upgrade_count"] == 1
    v9_cli_baseline_path = temp_root / "v9-cli-baseline.json"
    v9_cli_baseline_path.write_text(json.dumps(v7_cli_import), encoding="utf-8")
    compare_cli_code, compare_cli_report = _run_cli_json(
        "compare",
        "--baseline",
        str(v9_cli_baseline_path),
        "--facts",
        str(import_facts_path),
        "--profile",
        "generic",
        "--mode",
        "STANDARD",
    )
    assert compare_cli_code == 0
    assert compare_cli_report["status"] == "PASS"
    assert compare_cli_report["decision_scope"] == "MACHINE_NO_VETO_ONLY"
    assert compare_cli_report["violation_count"] == 0
    assert _is_sha256(compare_cli_report["activation_identity"])
    blocked_cli_facts = json.loads(import_facts_path.read_text(encoding="utf-8"))
    blocked_cli_facts["closure_item_ids"] = ["BASE", "EXTRA"]
    blocked_cli_facts["open_item_ids"] = ["BASE", "EXTRA"]
    blocked_cli_facts["planned_mutation_count"] = 2
    blocked_cli_facts_path = temp_root / "blocked-cli-facts.json"
    blocked_cli_facts_path.write_text(json.dumps(blocked_cli_facts), encoding="utf-8")
    blocked_cli_code, blocked_cli_report = _run_cli_json(
        "compare",
        "--baseline",
        str(v9_cli_baseline_path),
        "--facts",
        str(blocked_cli_facts_path),
        "--profile",
        "generic",
        "--mode",
        "STANDARD",
    )
    assert blocked_cli_code == 2
    assert blocked_cli_report["status"] == "BLOCKED"
    assert blocked_cli_report["decision_scope"] == "MACHINE_VETO"
    assert [row["code"] for row in blocked_cli_report["violations"]] == [
        "CLOSURE_ITEM_SET_EXPANDED",
        "OPEN_ITEM_SET_EXPANDED",
        "CLOSURE_ITEM_DENOMINATOR_INCREASED",
        "OPEN_ITEM_COUNT_INCREASED",
        "PLANNED_MUTATION_COUNT_INCREASED",
        "REMAINING_MUTATION_COUNT_INCREASED",
    ], blocked_cli_report
    assert blocked_cli_report["minimum_legal_next_action"] == blocked_cli_report["violations"][0]["minimum_legal_next_action"]
    incompatible_cli_code, incompatible_cli_report = _run_cli_json(
        "compare",
        "--baseline",
        str(v7_predecessor_path),
        "--facts",
        str(import_facts_path),
        "--profile",
        "generic",
        "--mode",
        "STANDARD",
    )
    assert incompatible_cli_code == 2
    assert incompatible_cli_report["status"] == "ERROR"
    assert incompatible_cli_report["reason_code"] == "GUARD_INPUT_OR_CAPTURE_INVALID"
    assert "schema is incompatible" in incompatible_cli_report["message"]
    continued = capture(
        None,
        str(import_facts_path),
        "generic",
        "STANDARD",
        inherited_lineage=imported["lineage"],
        inherited_control_event_origin=3,
    )
    assert not _test_codes(imported, continued)
    blocked_id = _tokens("blocker", ["LEGACY-BLOCKER"])[0]
    v7_blocked = json.loads(json.dumps(v7_import))
    v7_blocked["facts"].update({"blocker_ids": [blocked_id], "blocker_count": 1})
    v7_blocked["facts"]["capabilities"] = sorted({*v7_blocked["facts"]["capabilities"], "blockers"})
    _reseal_test_snapshot(v7_blocked)
    imported_pending = json.loads(json.dumps(imported))
    imported_pending["facts"].update({"blocker_ids": [blocked_id], "blocker_count": 1})
    imported_pending["facts"]["capabilities"] = sorted({*imported_pending["facts"]["capabilities"], "blockers"})
    imported_pending["lineage"]["schema_upgrade_parent_snapshot_sha256"] = v7_blocked["snapshot_sha256"]
    _reseal_test_snapshot(imported_pending)
    assert not _v7_upgrade_violations(v7_blocked, imported_pending), _v7_upgrade_violations(v7_blocked, imported_pending)
    converted_control = _raw_control_from_snapshot(imported_pending)
    converted_control["findings"] = [_test_finding(finding_id="LEGACY-BLOCKER", consumer="LEGACY-CONSUMER")]
    converted = _test_snapshot(
        {
            "project_id": "schema-import",
            "control_event_count": 3,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "writer_free": True,
            "writer_proof_identity": "IMPORT-WRITER",
            "campaign_control": _test_campaign_control(),
            "control_economy": converted_control,
        }
    )
    converted["lineage"] = imported_pending["lineage"]
    _reseal_test_snapshot(converted)
    converted_codes = _test_codes(imported_pending, converted)
    assert "BASELINE_CONTROL_FINDINGS_REQUIRED" not in converted_codes, converted_codes
    lost_blocker = json.loads(json.dumps(imported_pending))
    lost_blocker["facts"].update({"blocker_ids": [], "blocker_count": 0})
    lost_blocker["facts"]["capabilities"].remove("blockers")
    _reseal_test_snapshot(lost_blocker)
    assert "V7_UPGRADE_HISTORY_DRIFT" in {row["code"] for row in _v7_upgrade_violations(v7_blocked, lost_blocker)}
    scope_drifted = json.loads(json.dumps(imported))
    scope_drifted["facts"]["control_economy"]["objective_scope_identity"] = "DRIFTED-SCOPE"
    _reseal_test_snapshot(scope_drifted)
    assert "V7_UPGRADE_HISTORY_DRIFT" in {row["code"] for row in _v7_upgrade_violations(v7_import, scope_drifted)}
    drifted_import = json.loads(json.dumps(imported))
    drifted_import["facts"]["authority_revision_identity"] = "DRIFTED-AUTHORITY"
    _reseal_test_snapshot(drifted_import)
    assert "V7_UPGRADE_HISTORY_DRIFT" in {row["code"] for row in _v7_upgrade_violations(v7_import, drifted_import)}


def _test_core_invariants() -> None:
    small0 = _test_normalization_schema_invariants()
    legal_predecessor = _test_identity_scope_invariants()
    campaign0, campaign1, distinct_attempt = _test_campaign_budget_invariants()
    _test_rebaseline_attempt_invariants(
        small0, legal_predecessor, campaign0, campaign1, distinct_attempt
    )
    decision1, reused = _test_decision_stage_invariants()
    _test_frontier_authority_invariants(decision1, reused)
    with tempfile.TemporaryDirectory(prefix="guard-v71-") as raw_temp:
        temp_root = Path(raw_temp)
        _test_repository_path_invariants(temp_root)
        _test_import_rebaseline_cli_invariants(temp_root)
    v6 = {**campaign0, "schema_id": "ENGINEERING_CLOSURE_GUARD_SNAPSHOT_V6"}
    _reseal_test_snapshot(v6)
    assert "BASELINE_SCHEMA_INCOMPATIBLE" in _test_codes(v6, campaign0)
    return None


def _write_test_json(root: Path, name: str, value: Any) -> Path:
    path = root / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _assert_cli(
    args: list[str],
    expected_code: int,
    *,
    profile: str | None = None,
    reason: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    code, payload = _run_cli_json(*args)
    assert code == expected_code
    assert payload["status"] == "ERROR" if expected_code else payload["profile"] == profile
    if reason is not None:
        assert payload["reason_code"] == reason
    if message is not None:
        assert message in payload["message"]
    return payload


def _test_cli_profile_and_rebaseline_contract() -> None:
    with tempfile.TemporaryDirectory(prefix="guard-v9-cli-") as raw_temp:
        root = Path(raw_temp)
        repo = root / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        (repo / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Guard Self Test",
                "-c",
                "user.email=guard-selftest@example.invalid",
                "commit",
                "-qm",
                "baseline",
            ],
            cwd=repo,
            check=True,
        )

        facts = {
            "project_id": "cli-profile-contract",
            "campaign_id": "cli-profile-contract-campaign",
            "change_generation": "G0",
            "closure_item_ids": ["BASE"],
            "open_item_ids": ["BASE"],
            "planned_mutation_count": 1,
            "completed_mutation_count": 0,
            "validation_level": "BASELINE",
            "validation_rank": 0,
            "active_mutator_count": 0,
            "capabilities": ["validation_execution"],
            "control_economy": _test_control_economy(),
        }
        facts_path = _write_test_json(root, "facts.json", facts)
        success_cases = (
            (["snapshot", "--repo", str(repo), "--facts", str(facts_path), "--profile", "generic", "--mode", "STANDARD"], "generic"),
            (["snapshot", "--facts", str(facts_path), "--profile", "auto", "--mode", "STANDARD"], "generic"),
            (["snapshot", "--repo", str(repo), "--profile", "git", "--mode", "LIGHT"], "git"),
        )
        for cli_args, expected_profile in success_cases:
            _assert_cli(cli_args, 0, profile=expected_profile)

        explicit_decision = json.loads(json.dumps(facts))
        explicit_decision["control_economy"]["decision_request"] = _test_decision_request()
        explicit_decision["control_economy"]["decision_request"]["costs"] = ["DECISION"]
        explicit_decision_path = _write_test_json(root, "explicit-decision.json", explicit_decision)
        error_cases = (
            (
                ["snapshot", "--repo", str(repo), "--facts", str(facts_path), "--profile", "git", "--mode", "STANDARD"],
                None,
                "git profile consumes only --repo",
            ),
            (
                ["snapshot", "--repo", str(repo), "--profile", "git", "--mode", "STANDARD"],
                "CONTROL_ECONOMY_REQUIRED",
                None,
            ),
            (
                ["snapshot", "--facts", str(explicit_decision_path), "--profile", "generic", "--mode", "STANDARD"],
                None,
                "DECISION",
            ),
        )
        for cli_args, reason, message in error_cases:
            _assert_cli(cli_args, 2, reason=reason, message=message)

        predecessor_facts = {
            "project_id": "cli-v9-rebaseline",
            "closure_item_ids": ["C1"],
            "open_item_ids": [],
            "planned_mutation_count": 1,
            "completed_mutation_count": 0,
            "validation_rank": 0,
            "active_mutator_count": 0,
            "authority_status": "ACTIVATED",
            "authority_revision_count": 1,
            "authority_revision_identity": "AUTHORITY-1",
        }
        predecessor_facts_path = _write_test_json(root, "predecessor-facts.json", predecessor_facts)
        predecessor = _assert_cli(
            ["snapshot", "--facts", str(predecessor_facts_path), "--profile", "generic", "--mode", "LIGHT"],
            0,
            profile="generic",
        )
        predecessor_path = _write_test_json(root, "predecessor.json", predecessor)

        successor_facts = {
            **predecessor_facts,
            "closure_item_ids": ["C1", "C2"],
            "open_item_ids": ["C2"],
            "planned_mutation_count": 2,
            "active_expensive_run_count": 0,
            "expensive_start_count": 0,
            "writer_free": True,
            "writer_proof_identity": "WRITER-2",
            "authority_revision_count": 2,
            "authority_revision_identity": "AUTHORITY-2",
        }
        successor_facts_path = _write_test_json(root, "successor-facts.json", successor_facts)
        successor = _assert_cli(
            [
                "snapshot", "--facts", str(successor_facts_path), "--profile", "generic", "--mode", "LIGHT",
                "--predecessor", str(predecessor_path), "--accept-rebaseline",
            ],
            0,
            profile="generic",
        )
        assert successor["lineage"]["accepted_rebaseline_count"] == 1

        successor_path = _write_test_json(root, "successor.json", successor)
        _assert_cli(
            [
                "snapshot", "--facts", str(successor_facts_path), "--profile", "generic", "--mode", "LIGHT",
                "--predecessor", str(successor_path), "--accept-rebaseline",
            ],
            2,
            message="accepted rebaseline limit exceeded",
        )


def _test_violation_guidance_contract() -> None:
    for code, expected in sorted(VIOLATION_GUIDANCE.items()):
        row = _violation(code)
        assert row["code"] == code
        assert all(row[key] == value for key, value in expected.items())
        assert isinstance(row["minimum_legal_next_action"], str)
        assert isinstance(row["prohibited_actions"], list)


SELF_TEST_GROUPS = (
    ("core-invariants", 141, _test_core_invariants),
    ("cli-profile-and-rebaseline", 8, _test_cli_profile_and_rebaseline_contract),
    ("violation-guidance", len(VIOLATION_GUIDANCE), _test_violation_guidance_contract),
)


def run_self_test() -> None:
    for _name, _scenario_count, test_group in SELF_TEST_GROUPS:
        test_group()
    scenario_count = sum(count for _name, count, _test_group in SELF_TEST_GROUPS)
    print(f"closure_guard_self_test=PASS scenarios={scenario_count}")
