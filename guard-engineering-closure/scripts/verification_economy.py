#!/usr/bin/env python3
"""Plan file and hash re-verification without rereading unchanged content."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA_ID = "VERIFICATION_ECONOMY_SNAPSHOT_V3"


def _run(argv: list[str], cwd: Path) -> bytes:
    result = subprocess.run(
        argv,
        cwd=str(cwd),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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


def _require_identity(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty immutable identity")
    return value


def _nul_paths(payload: bytes) -> list[str]:
    return sorted(
        item.decode("utf-8", errors="strict")
        for item in payload.split(b"\0")
        if item
    )


def _path_token(kind: str, relative_path: str) -> str:
    return hashlib.sha256(f"{kind}:{relative_path}".encode("utf-8")).hexdigest()


def _tracked_index(repo: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for record in _run(["git", "ls-files", "-s", "-z"], repo).split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        fields = metadata.decode("ascii").split()
        if len(fields) != 3 or fields[2] != "0":
            continue
        result[raw_path.decode("utf-8", errors="strict")] = fields[1]
    return result


def _read_explicit_paths(path: str) -> list[str]:
    if path == "-":
        lines = sys.stdin.read().splitlines()
    else:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    return sorted({line.strip() for line in lines if line.strip()})


def _normalize_relative_path(repo: Path, value: str) -> str:
    candidate = Path(value)
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(repo.resolve())
        except ValueError as exc:
            raise ValueError(f"path escapes repository: {value}") from exc
    normalized = Path(os.path.normpath(str(candidate)))
    if (
        str(normalized) in ("", ".")
        or ".." in normalized.parts
        or ".git" in normalized.parts
    ):
        raise ValueError(f"invalid repository-relative path: {value}")
    return normalized.as_posix()


def _reject_intermediate_symlinks(repo: Path, relative_path: str) -> None:
    current = repo
    for part in Path(relative_path).parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"intermediate symlink is prohibited: {relative_path}")


def _enumerate_paths(repo: Path, scope: str, paths_from: str | None) -> tuple[list[str], set[str], set[str]]:
    tracked_index = _tracked_index(repo)
    tracked = set(tracked_index)
    dirty = set(_nul_paths(_run(["git", "diff", "HEAD", "--name-only", "-z"], repo)))
    untracked = set(
        _nul_paths(_run(["git", "ls-files", "--others", "--exclude-standard", "-z"], repo))
    )

    if paths_from is not None:
        selected = {
            _normalize_relative_path(repo, value)
            for value in _read_explicit_paths(paths_from)
        }
        unknown = selected - tracked - untracked
        if unknown:
            raise ValueError(
                f"explicit path is not tracked or untracked: {_path_token('unknown', sorted(unknown)[0])}"
            )
    elif scope == "changed":
        selected = dirty | untracked
    elif scope == "all":
        selected = tracked | untracked
    else:
        raise ValueError(f"unsupported scope: {scope}")
    for relative_path in selected:
        _reject_intermediate_symlinks(repo, relative_path)
    return sorted(selected), tracked, dirty


def _stat_key(path: Path) -> list[int]:
    value = path.lstat()
    return [
        int(value.st_dev),
        int(value.st_ino),
        int(value.st_mode),
        int(value.st_size),
        int(value.st_mtime_ns),
        int(value.st_ctime_ns),
    ]


def _hash_file(path: Path, expected_stat_key: list[int]) -> str:
    info = path.lstat()
    if _stat_key(path) != expected_stat_key:
        raise ValueError("WRITER_CHANGED_DURING_CAPTURE")
    digest = hashlib.sha256()
    if stat.S_ISLNK(info.st_mode):
        digest.update(b"SYMLINK\0")
        digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
        if _stat_key(path) != expected_stat_key:
            raise ValueError("WRITER_CHANGED_DURING_CAPTURE")
        return digest.hexdigest()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"unsupported non-regular path token: {_path_token('special', path.name)}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as handle:
        descriptor_stat = os.fstat(handle.fileno())
        descriptor_key = [
            int(value)
            for value in (
                descriptor_stat.st_dev,
                descriptor_stat.st_ino,
                descriptor_stat.st_mode,
                descriptor_stat.st_size,
                descriptor_stat.st_mtime_ns,
                descriptor_stat.st_ctime_ns,
            )
        ]
        if descriptor_key != expected_stat_key:
            raise ValueError("WRITER_CHANGED_DURING_CAPTURE")
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after_descriptor = os.fstat(handle.fileno())
        after_key = [
            int(after_descriptor.st_dev), int(after_descriptor.st_ino),
            int(after_descriptor.st_mode), int(after_descriptor.st_size),
            int(after_descriptor.st_mtime_ns), int(after_descriptor.st_ctime_ns),
        ]
        if after_key != expected_stat_key:
            raise ValueError("WRITER_CHANGED_DURING_CAPTURE")
    if _stat_key(path) != expected_stat_key:
        raise ValueError("WRITER_CHANGED_DURING_CAPTURE")
    return digest.hexdigest()


def _baseline_entries(baseline: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(baseline, dict):
        return {}
    entries = baseline.get("entries")
    if not isinstance(entries, list):
        raise ValueError("snapshot entries must be a list")
    result: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path_token"), str):
            raise ValueError("snapshot entry is malformed")
        token = str(entry["path_token"])
        if token in result:
            raise ValueError("snapshot contains duplicate path tokens")
        result[token] = entry
    return result


def _verification_key(snapshot: dict[str, Any]) -> str:
    entries = _baseline_entries(snapshot)
    return _canonical_sha256(
        {
            "repo_token": snapshot.get("repo_token"),
            "epoch": snapshot.get("epoch"),
            "validator_id": snapshot.get("validator_id"),
            "dependency_id": snapshot.get("dependency_id"),
            "execution_purpose": snapshot.get("execution_purpose"),
            "objects": [
                [token, entries[token].get("content_identity")]
                for token in sorted(entries)
            ],
        }
    )


def _validate_snapshot(snapshot: Any, label: str) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        raise ValueError(f"{label} must be a JSON object")
    required = {
        "schema_id", "repo_token", "head", "scope", "epoch", "validator_id",
        "dependency_id", "execution_purpose", "verification_status",
        "writer_free_asserted", "path_set_sha256", "entry_count", "entries",
        "capture_metrics", "verification_key_sha256", "snapshot_sha256",
    }
    if set(snapshot) != required:
        raise ValueError(f"{label} fields do not match schema V3")
    if snapshot.get("schema_id") != SCHEMA_ID:
        raise ValueError(f"{label} schema is incompatible; capture a fresh V3 baseline")
    for field in ("repo_token", "head", "epoch", "validator_id", "dependency_id", "execution_purpose"):
        _require_identity(snapshot.get(field), field)
    if snapshot.get("scope") not in {"changed", "all"}:
        raise ValueError(f"{label} scope is malformed")
    if snapshot.get("verification_status") not in {"PASS", "UNVERIFIED", "BLOCKED"}:
        raise ValueError(f"{label} verification status is malformed")
    if not isinstance(snapshot.get("writer_free_asserted"), bool):
        raise ValueError(f"{label} writer assertion is malformed")
    entries = _baseline_entries(snapshot)
    entry_fields = {
        "path_token", "kind", "exists", "stat_key", "content_identity", "identity_source",
    }
    for entry in entries.values():
        if set(entry) != entry_fields:
            raise ValueError(f"{label} entry fields are malformed")
        if entry.get("kind") not in {"tracked", "untracked"}:
            raise ValueError(f"{label} entry kind is malformed")
        if not isinstance(entry.get("exists"), bool) or not isinstance(entry.get("content_identity"), str):
            raise ValueError(f"{label} entry identity is malformed")
        stat_key = entry.get("stat_key")
        if entry["exists"] and (
            not isinstance(stat_key, list)
            or len(stat_key) != 6
            or not all(isinstance(value, int) and not isinstance(value, bool) for value in stat_key)
        ):
            raise ValueError(f"{label} entry stat key is malformed")
        if not entry["exists"] and stat_key is not None:
            raise ValueError(f"{label} missing entry has a stat key")
    if snapshot.get("entry_count") != len(entries):
        raise ValueError(f"{label} entry_count mismatch")
    if snapshot.get("path_set_sha256") != _canonical_sha256(sorted(entries)):
        raise ValueError(f"{label} path-set hash mismatch")
    if snapshot.get("verification_key_sha256") != _verification_key(snapshot):
        raise ValueError(f"{label} verification-key hash mismatch")
    metrics = snapshot.get("capture_metrics")
    if not isinstance(metrics, dict) or set(metrics) != {
        "content_hash_reads", "metadata_hash_reuses", "git_oid_reuses"
    } or not all(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0
        for value in metrics.values()
    ):
        raise ValueError(f"{label} capture metrics are malformed")
    payload = {key: value for key, value in snapshot.items() if key != "snapshot_sha256"}
    if snapshot.get("snapshot_sha256") != _canonical_sha256(payload):
        raise ValueError(f"{label} snapshot hash mismatch")
    return snapshot


def capture(
    *,
    repo: Path,
    scope: str,
    paths_from: str | None,
    epoch: str,
    validator_id: str,
    dependency_id: str,
    verification_status: str,
    execution_purpose: str = "GENERAL_ENGINEERING",
    baseline: dict[str, Any] | None = None,
    force_content_hash: bool = False,
    writer_free: bool = False,
) -> dict[str, Any]:
    if verification_status == "PASS" and not writer_free:
        raise ValueError("PASS snapshot requires an independently proven writer-free checkpoint")
    _require_identity(epoch, "epoch")
    _require_identity(validator_id, "validator_id")
    _require_identity(dependency_id, "dependency_id")
    _require_identity(execution_purpose, "execution_purpose")
    if baseline is not None:
        _validate_snapshot(baseline, "baseline")
    repo = repo.resolve()
    head = _run(["git", "rev-parse", "HEAD"], repo).decode().strip()
    repo_token = _path_token("repository", str(repo))
    selected, tracked, dirty = _enumerate_paths(repo, scope, paths_from)
    index = _tracked_index(repo)
    old_entries = _baseline_entries(baseline)
    same_epoch = isinstance(baseline, dict) and baseline.get("epoch") == epoch

    entries: list[dict[str, Any]] = []
    content_hash_reads = 0
    metadata_hash_reuses = 0
    git_oid_reuses = 0

    for relative_path in selected:
        kind = "tracked" if relative_path in tracked else "untracked"
        token = _path_token(kind, relative_path)
        absolute_path = repo / relative_path
        if not absolute_path.exists() and not absolute_path.is_symlink():
            entries.append(
                {
                    "path_token": token,
                    "kind": kind,
                    "exists": False,
                    "stat_key": None,
                    "content_identity": "MISSING",
                    "identity_source": "missing",
                }
            )
            continue

        stat_key = _stat_key(absolute_path)
        clean_tracked = kind == "tracked" and relative_path not in dirty
        old = old_entries.get(token)
        if clean_tracked and not force_content_hash:
            content_identity = f"git-blob:{index[relative_path]}"
            identity_source = "git_blob"
            git_oid_reuses += 1
        elif (
            not force_content_hash
            and writer_free
            and same_epoch
            and isinstance(old, dict)
            and old.get("stat_key") == stat_key
            and isinstance(old.get("content_identity"), str)
            and old.get("content_identity") != "MISSING"
        ):
            content_identity = str(old["content_identity"])
            identity_source = "metadata_guarded_cache"
            metadata_hash_reuses += 1
        else:
            content_identity = f"sha256:{_hash_file(absolute_path, stat_key)}"
            identity_source = "fresh_content_hash"
            content_hash_reads += 1

        entries.append(
            {
                "path_token": token,
                "kind": kind,
                "exists": True,
                "stat_key": stat_key,
                "content_identity": content_identity,
                "identity_source": identity_source,
            }
        )

    snapshot: dict[str, Any] = {
        "schema_id": SCHEMA_ID,
        "repo_token": repo_token,
        "head": head,
        "scope": scope,
        "epoch": epoch,
        "validator_id": validator_id,
        "dependency_id": dependency_id,
        "execution_purpose": execution_purpose,
        "verification_status": verification_status,
        "writer_free_asserted": writer_free,
        "path_set_sha256": _canonical_sha256(
            sorted(entry["path_token"] for entry in entries)
        ),
        "entry_count": len(entries),
        "entries": entries,
        "capture_metrics": {
            "content_hash_reads": content_hash_reads,
            "metadata_hash_reuses": metadata_hash_reuses,
            "git_oid_reuses": git_oid_reuses,
        },
    }
    snapshot["verification_key_sha256"] = _verification_key(snapshot)
    snapshot["snapshot_sha256"] = _canonical_sha256(snapshot)
    return snapshot


def plan(
    baseline: dict[str, Any],
    current: dict[str, Any],
    *,
    trust_boundary: bool,
) -> dict[str, Any]:
    _validate_snapshot(baseline, "baseline")
    _validate_snapshot(current, "current snapshot")
    before = _baseline_entries(baseline)
    after = _baseline_entries(current)
    before_tokens = set(before)
    after_tokens = set(after)
    new_tokens = sorted(after_tokens - before_tokens)
    removed_tokens = sorted(before_tokens - after_tokens)

    global_reasons: list[str] = []
    if baseline.get("schema_id") != current.get("schema_id"):
        global_reasons.append("PLANNER_SCHEMA_CHANGED")
    if baseline.get("repo_token") != current.get("repo_token"):
        global_reasons.append("PROJECT_CHANGED")
    if baseline.get("verification_status") != "PASS":
        global_reasons.append("BASELINE_NOT_VERIFIED_PASS")
    if current.get("writer_free_asserted") is not True:
        global_reasons.append("WRITER_STATE_UNPROVEN")
    if baseline.get("epoch") != current.get("epoch"):
        global_reasons.append("EPOCH_CHANGED")
    if baseline.get("validator_id") != current.get("validator_id"):
        global_reasons.append("VALIDATOR_CHANGED")
    if baseline.get("dependency_id") != current.get("dependency_id"):
        global_reasons.append("DEPENDENCY_CLOSURE_CHANGED")
    if baseline.get("execution_purpose") != current.get("execution_purpose"):
        global_reasons.append("EXECUTION_PURPOSE_CHANGED")
    if baseline.get("scope") != current.get("scope"):
        global_reasons.append("SCOPE_CHANGED")
    if trust_boundary:
        global_reasons.append("TRUST_BOUNDARY_FRESH_CHECK")

    revalidate: dict[str, list[str]] = {}
    reusable: list[str] = []
    for token in sorted(after_tokens):
        reasons = list(global_reasons)
        if token in new_tokens:
            reasons.append("NEW_OBJECT")
        elif before[token].get("content_identity") != after[token].get("content_identity"):
            reasons.append("CONTENT_IDENTITY_CHANGED")
        elif before[token].get("exists") != after[token].get("exists"):
            reasons.append("EXISTENCE_CHANGED")
        if reasons:
            revalidate[token] = sorted(set(reasons))
        else:
            reusable.append(token)

    status = "REVALIDATION_REQUIRED" if revalidate or removed_tokens else "REUSE_ALL"
    reuse_decision = (
        "R4_FRESH_SEAL_REQUIRED"
        if trust_boundary
        else "R2_VALIDATION_REUSE"
        if status == "REUSE_ALL"
        else "R1_IDENTITY_REUSE_WITH_REVALIDATION"
    )
    result = {
        "status": status,
        "reuse_decision": reuse_decision,
        "global_reasons": sorted(set(global_reasons)),
        "revalidate_count": len(revalidate),
        "reusable_count": len(reusable),
        "new_count": len(new_tokens),
        "removed_count": len(removed_tokens),
        "revalidate": revalidate,
        "reusable_path_tokens": reusable,
        "removed_path_tokens": removed_tokens,
        "capture_metrics": current["capture_metrics"],
        "verification_key_sha256": current["verification_key_sha256"],
        "current_snapshot_sha256": current["snapshot_sha256"],
    }
    result["plan_sha256"] = _canonical_sha256(result)
    return result


def _load_json(value: str) -> dict[str, Any]:
    text = sys.stdin.read() if value == "-" else Path(value).read_text(encoding="utf-8")
    return _strict_json_text(text, "verification JSON input")


def _add_capture_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--scope", choices=("changed", "all"), default="changed")
    parser.add_argument("--paths-from")
    parser.add_argument("--epoch", required=True)
    parser.add_argument("--validator-id", required=True)
    parser.add_argument("--dependency-id", required=True)
    parser.add_argument("--execution-purpose", default="GENERAL_ENGINEERING")
    parser.add_argument(
        "--writer-free",
        action="store_true",
        help="assert that writer absence was independently proven for this checkpoint",
    )


def _reseal_test_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    snapshot["verification_key_sha256"] = _verification_key(snapshot)
    snapshot.pop("snapshot_sha256", None)
    snapshot["snapshot_sha256"] = _canonical_sha256(snapshot)
    return snapshot


def _self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="verification-economy-") as temp_root:
        repo = Path(temp_root)
        _run(["git", "init", "-q"], repo)
        (repo / "stable.txt").write_text("stable\n", encoding="utf-8")
        (repo / "mutable.txt").write_text("v1\n", encoding="utf-8")
        _run(["git", "add", "."], repo)
        _run(
            [
                "git",
                "-c",
                "user.name=Closure Guard",
                "-c",
                "user.email=closure@example.invalid",
                "commit",
                "-qm",
                "baseline",
            ],
            repo,
        )
        (repo / "mutable.txt").write_text("v2\n", encoding="utf-8")

        try:
            capture(
                repo=repo,
                scope="all",
                paths_from=None,
                epoch="E1",
                validator_id="V1",
                dependency_id="D1",
                verification_status="PASS",
            )
        except ValueError:
            pass
        else:
            raise AssertionError("PASS snapshot accepted without writer-free proof")

        baseline = capture(
            repo=repo,
            scope="all",
            paths_from=None,
            epoch="E1",
            validator_id="V1",
            dependency_id="D1",
            verification_status="PASS",
            writer_free=True,
        )
        current = capture(
            repo=repo,
            scope="all",
            paths_from=None,
            epoch="E1",
            validator_id="V1",
            dependency_id="D1",
            verification_status="UNVERIFIED",
            baseline=baseline,
            writer_free=True,
        )
        same_plan = plan(baseline, current, trust_boundary=False)
        assert same_plan["status"] == "REUSE_ALL"
        assert same_plan["reuse_decision"] == "R2_VALIDATION_REUSE"
        assert current["capture_metrics"]["metadata_hash_reuses"] == 1

        purpose_changed = capture(
            repo=repo,
            scope="all",
            paths_from=None,
            epoch="E1",
            validator_id="V1",
            dependency_id="D1",
            verification_status="UNVERIFIED",
            execution_purpose="FINAL_REMOTE",
            baseline=baseline,
            writer_free=True,
        )
        purpose_plan = plan(baseline, purpose_changed, trust_boundary=False)
        assert "EXECUTION_PURPOSE_CHANGED" in purpose_plan["global_reasons"]
        assert purpose_plan["reuse_decision"] == "R1_IDENTITY_REUSE_WITH_REVALIDATION"
        assert purpose_changed["verification_key_sha256"] != baseline["verification_key_sha256"]

        no_writer_proof = capture(
            repo=repo,
            scope="all",
            paths_from=None,
            epoch="E1",
            validator_id="V1",
            dependency_id="D1",
            verification_status="UNVERIFIED",
            baseline=baseline,
        )
        assert no_writer_proof["capture_metrics"]["content_hash_reads"] == 1
        assert "WRITER_STATE_UNPROVEN" in plan(
            baseline, no_writer_proof, trust_boundary=False
        )["global_reasons"]

        wrong_project = dict(current)
        wrong_project["repo_token"] = "different-project"
        _reseal_test_snapshot(wrong_project)
        wrong_project_plan = plan(baseline, wrong_project, trust_boundary=False)
        assert "PROJECT_CHANGED" in wrong_project_plan["global_reasons"]

        (repo / "mutable.txt").write_text("v3\n", encoding="utf-8")
        changed = capture(
            repo=repo,
            scope="all",
            paths_from=None,
            epoch="E1",
            validator_id="V1",
            dependency_id="D1",
            verification_status="UNVERIFIED",
            baseline=baseline,
            writer_free=True,
        )
        changed_plan = plan(baseline, changed, trust_boundary=False)
        assert changed_plan["revalidate_count"] == 1
        assert "CONTENT_IDENTITY_CHANGED" in next(iter(changed_plan["revalidate"].values()))

        validator_changed = dict(current)
        validator_changed["validator_id"] = "V2"
        _reseal_test_snapshot(validator_changed)
        validator_changed_plan = plan(baseline, validator_changed, trust_boundary=False)
        assert validator_changed_plan["revalidate_count"] == 2
        assert "VALIDATOR_CHANGED" in validator_changed_plan["global_reasons"]

        boundary = capture(
            repo=repo,
            scope="all",
            paths_from=None,
            epoch="E1",
            validator_id="V1",
            dependency_id="D1",
            verification_status="UNVERIFIED",
            baseline=baseline,
            force_content_hash=True,
            writer_free=True,
        )
        boundary_plan = plan(baseline, boundary, trust_boundary=True)
        assert boundary["capture_metrics"]["content_hash_reads"] == 2
        assert "TRUST_BOUNDARY_FRESH_CHECK" in boundary_plan["global_reasons"]
        assert boundary_plan["reuse_decision"] == "R4_FRESH_SEAL_REQUIRED"
        tampered = dict(baseline)
        tampered["epoch"] = "E2"
        try:
            plan(tampered, current, trust_boundary=False)
        except ValueError:
            pass
        else:
            raise AssertionError("tampered snapshot was accepted")

        bad_key = dict(baseline)
        bad_key["verification_key_sha256"] = "0" * 64
        bad_key.pop("snapshot_sha256")
        bad_key["snapshot_sha256"] = _canonical_sha256(bad_key)
        try:
            plan(bad_key, current, trust_boundary=False)
        except ValueError:
            pass
        else:
            raise AssertionError("tampered verification key was accepted")

        try:
            capture(
                repo=repo, scope="all", paths_from=None, epoch="",
                validator_id="V1", dependency_id="D1",
                verification_status="UNVERIFIED",
            )
        except ValueError:
            pass
        else:
            raise AssertionError("empty epoch was accepted")

        stale = repo / "stale.txt"
        stale.write_text("before\n", encoding="utf-8")
        stale_key = _stat_key(stale)
        stale.write_text("after\n", encoding="utf-8")
        try:
            _hash_file(stale, stale_key)
        except ValueError as exc:
            assert "WRITER_CHANGED_DURING_CAPTURE" in str(exc)
        else:
            raise AssertionError("stale stat key was accepted")

        try:
            _strict_json_text('{"a": 1, "a": 2}', "test JSON")
        except ValueError:
            pass
        else:
            raise AssertionError("duplicate JSON key was accepted")

        try:
            _normalize_relative_path(repo, ".git/config")
        except ValueError:
            pass
        else:
            raise AssertionError(".git path was accepted")

        outside = repo / "outside-target"
        outside.mkdir(exist_ok=True)
        (repo / "escape").symlink_to(outside, target_is_directory=True)
        try:
            _reject_intermediate_symlinks(repo, "escape/file.txt")
        except ValueError:
            pass
        else:
            raise AssertionError("intermediate symlink was accepted")
    print("verification_economy_self_test=PASS scenarios=11")


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot")
    _add_capture_arguments(snapshot_parser)
    snapshot_parser.add_argument(
        "--verification-status",
        choices=("PASS", "UNVERIFIED", "BLOCKED"),
        default="UNVERIFIED",
    )

    plan_parser = subparsers.add_parser("plan")
    _add_capture_arguments(plan_parser)
    plan_parser.add_argument("--baseline", required=True)
    plan_parser.add_argument("--trust-boundary", action="store_true")

    subparsers.add_parser("self-test")
    args = parser.parse_args()

    if args.command == "self-test":
        _self_test()
        return 0

    if args.command == "snapshot":
        result = capture(
            repo=args.repo,
            scope=args.scope,
            paths_from=args.paths_from,
            epoch=args.epoch,
            validator_id=args.validator_id,
            dependency_id=args.dependency_id,
            verification_status=args.verification_status,
            execution_purpose=args.execution_purpose,
            writer_free=args.writer_free,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    baseline = _load_json(args.baseline)
    current = capture(
        repo=args.repo,
        scope=args.scope,
        paths_from=args.paths_from,
        epoch=args.epoch,
        validator_id=args.validator_id,
        dependency_id=args.dependency_id,
        verification_status="UNVERIFIED",
        execution_purpose=args.execution_purpose,
        baseline=baseline,
        force_content_hash=args.trust_boundary,
        writer_free=args.writer_free,
    )
    result = plan(baseline, current, trust_boundary=args.trust_boundary)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def main() -> int:
    try:
        return _main()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "reason_code": "VERIFICATION_INPUT_OR_CAPTURE_INVALID",
                    "message": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
