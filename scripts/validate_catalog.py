#!/usr/bin/env python3
"""Validate paths, URLs, gitlinks, and checked-out dataset contracts."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import datetime as dt
from pathlib import Path
from urllib.parse import urlparse

from catalog import read_datasets, repository_name

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_MANIFEST_FIELDS = {
    "schema_version",
    "name",
    "title",
    "description",
    "repository",
    "license",
    "created",
    "authors",
    "provenance",
    "benchmark",
    "contents",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def gitlinks() -> set[str]:
    process = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "ls-files", "--stage"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    result: set[str] = set()
    for line in process.stdout.splitlines():
        metadata, path = line.split("\t", 1)
        if metadata.split()[0] == "160000":
            result.add(path.replace("\\", "/"))
    return result


def contained_path(base: Path, relative: object, label: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        fail(f"{label} must be a non-empty relative path")
    path = Path(relative)
    if path.is_absolute():
        fail(f"{label} must be relative")
    candidate = (base / path).resolve()
    base_resolved = base.resolve()
    if candidate != base_resolved and base_resolved not in candidate.parents:
        fail(f"{label} escapes its dataset directory")
    if not candidate.exists():
        fail(f"{label} does not exist")
    return candidate


def load_object(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"{label} is invalid JSON: {exc}")
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def validate_v2_structure(name: str, checkout: Path, manifest: dict) -> None:
    benchmark = manifest.get("benchmark")
    if not isinstance(benchmark, dict):
        fail(f"{name}: benchmark must be an object")
    if benchmark.get("execution_model") != "sequential":
        fail(f"{name}: benchmark.execution_model must be sequential")
    if benchmark.get("evaluation_method") != "manual":
        fail(f"{name}: benchmark.evaluation_method must be manual")
    if not re.fullmatch(r"v[0-9]{3,}", str(benchmark.get("initial_version", ""))):
        fail(f"{name}: benchmark.initial_version must match vNNN")

    contents = manifest.get("contents")
    if not isinstance(contents, dict):
        fail(f"{name}: contents must be an object")
    if set(contents) != {"subject", "steps", "documentation"}:
        fail(f"{name}: contents must contain subject, steps, and documentation")
    subject = contained_path(checkout, contents["subject"], f"{name}: contents.subject")
    documentation = contained_path(
        checkout, contents["documentation"], f"{name}: contents.documentation"
    )
    steps_path = contained_path(checkout, contents["steps"], f"{name}: contents.steps")
    if not subject.is_dir() or not documentation.is_dir() or not steps_path.is_file():
        fail(f"{name}: subject/documentation must be directories and steps must be a file")
    if (checkout / "benchmark" / "runs").exists():
        fail(f"{name}: benchmark/runs is not part of the reusable dataset")

    index = load_object(steps_path, f"{name}: steps index")
    entries = index.get("steps")
    if not isinstance(entries, list) or not entries:
        fail(f"{name}: steps index must contain at least one step")
    ids: set[str] = set()
    expected_before = str(benchmark["initial_version"])
    for sequence, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or set(entry) != {"id", "path"}:
            fail(f"{name}: step index entry {sequence} is invalid")
        step_id = entry["id"]
        if not isinstance(step_id, str) or not re.fullmatch(r"step-[0-9]{3,}", step_id):
            fail(f"{name}: step index entry {sequence} has an invalid id")
        if step_id in ids:
            fail(f"{name}: duplicate step id {step_id}")
        ids.add(step_id)
        step_path = contained_path(
            steps_path.parent, entry["path"], f"{name}: {step_id} path"
        )
        step = load_object(step_path, f"{name}: {step_id}")
        if step.get("id") != step_id or step.get("sequence") != sequence:
            fail(f"{name}: {step_id} identity or sequence is inconsistent")
        if step.get("before_version") != expected_before:
            fail(f"{name}: {step_id} does not continue from {expected_before}")
        after_version = str(step.get("after_version", ""))
        if not re.fullmatch(r"v[0-9]{3,}", after_version):
            fail(f"{name}: {step_id} has an invalid after_version")
        expected_before = after_version

        prompts = step.get("prompts")
        if not isinstance(prompts, list) or not prompts:
            fail(f"{name}: {step_id} must contain prompts")
        for prompt_index, prompt in enumerate(prompts, 1):
            if not isinstance(prompt, dict) or prompt.get("order") != prompt_index:
                fail(f"{name}: {step_id} prompt order is invalid")
            contained_path(
                step_path.parent,
                prompt.get("path"),
                f"{name}: {step_id} prompt {prompt_index}",
            )
        if not isinstance(step.get("expected_changes"), list) or not step["expected_changes"]:
            fail(f"{name}: {step_id} must contain expected changes")

        truth_path = contained_path(
            step_path.parent, step.get("ground_truth"), f"{name}: {step_id} ground truth"
        )
        truth = load_object(truth_path, f"{name}: {step_id} ground truth")
        for artifact_name in (
            "feature_model",
            "folder_mappings",
            "file_mappings",
            "fragment_mappings",
            "interactions",
        ):
            artifact = truth.get(artifact_name)
            if not isinstance(artifact, dict):
                fail(f"{name}: {step_id} ground truth lacks {artifact_name}")
            contained_path(
                truth_path.parent,
                artifact.get("path"),
                f"{name}: {step_id} {artifact_name}",
            )
        validation = truth.get("validation")
        if not isinstance(validation, dict) or validation.get("status") not in {
            "draft",
            "reviewed",
            "adjudicated",
        }:
            fail(f"{name}: {step_id} has invalid ground-truth validation metadata")

        oracle = step.get("implementation_oracle")
        if not isinstance(oracle, dict):
            fail(f"{name}: {step_id} lacks an implementation oracle")
        contained_path(
            step_path.parent,
            oracle.get("path"),
            f"{name}: {step_id} implementation oracle",
        )


def validate_checkout(name: str, url: str, checkout: Path) -> None:
    """Inspect data only; never execute code supplied by a submodule."""
    manifest_path = checkout / "dataset.json"
    if not manifest_path.exists():
        fail(f"{name}: initialized submodule has no dataset.json")
    if not (checkout / "LICENSE").is_file():
        fail(f"{name}: initialized submodule has no LICENSE")
    manifest = load_object(manifest_path, f"{name}: dataset.json")
    missing = sorted(REQUIRED_MANIFEST_FIELDS - manifest.keys())
    if missing:
        fail(f"{name}: dataset.json is missing {', '.join(missing)}")
    if manifest.get("schema_version") != "2.0":
        fail(f"{name}: unsupported schema_version")
    if manifest.get("name") != name:
        fail(f"{name}: dataset.json name does not match")
    expected_url = url.removesuffix(".git").rstrip("/")
    if str(manifest.get("repository", "")).rstrip("/") != expected_url:
        fail(f"{name}: dataset.json repository does not match .gitmodules")
    try:
        dt.date.fromisoformat(str(manifest.get("created")))
    except ValueError:
        fail(f"{name}: created must be an ISO date")
    validate_v2_structure(name, checkout, manifest)


def main() -> None:
    try:
        datasets = read_datasets(ROOT)
    except (ValueError, KeyError) as exc:
        fail(str(exc))
    expected_paths: set[str] = set()
    names: set[str] = set()
    for item in datasets:
        repo_name = repository_name(item.url)
        expected_path = f"datasets/{repo_name}"
        if item.name != repo_name:
            fail(f"submodule name {item.name!r} must equal repository name {repo_name!r}")
        if item.name in names:
            fail(f"duplicate dataset name: {item.name}")
        names.add(item.name)
        if not re.fullmatch(r"[A-Za-z0-9._-]+", item.name):
            fail(f"invalid dataset name: {item.name}")
        parsed = urlparse(item.url)
        if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
            fail(f"{item.name}: URL must be an HTTPS GitHub URL")
        if item.path.replace('\\', '/') != expected_path:
            fail(f"{item.name}: path must be {expected_path}")
        expected_paths.add(expected_path)

        checkout = ROOT / item.path
        if checkout.is_dir() and any(checkout.iterdir()):
            validate_checkout(item.name, item.url, checkout)

    actual_gitlinks = gitlinks()
    if expected_paths != actual_gitlinks:
        fail(
            "submodule declarations and gitlinks differ: "
            f"declared-only={sorted(expected_paths - actual_gitlinks)}, "
            f"gitlink-only={sorted(actual_gitlinks - expected_paths)}"
        )
    print(f"Catalog valid: {len(datasets)} dataset(s)")


if __name__ == "__main__":
    main()
