"""Verify the tagged commit's CI run on main passed before a release publishes.

`release.yml` triggers on tag push, but `ci.yml` triggers on every push with
no branch filter, so the same tag push also starts an independent `CI` run
concurrent with `release.yml` -- checking that run would race it. The
release runbook instead pushes the version-bump commit to `main` first,
waits for *that* push's CI run, then pushes the tag; this script re-checks
that same run (the one triggered by the commit's push to `main`, not by the
tag push) so a release can never publish without it, even if the runbook's
own wait step was skipped or cut short.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable

GhRunner = Callable[..., str]


def _gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=True)
    return result.stdout


def find_main_push_ci_run(
    repo: str,
    sha: str,
    workflow: str = "CI",
    gh: GhRunner = _gh,
) -> dict | None:
    """Return the CI run triggered by `sha`'s push to `main`, or None.

    Filters in Python rather than relying solely on `gh run list`'s own
    --branch/--event flags: a tag push and a branch push can both list the
    same commit SHA, and only the branch-push run on `main` is the one this
    gate trusts.
    """

    raw = gh(
        "run",
        "list",
        "--repo",
        repo,
        "--commit",
        sha,
        "--workflow",
        workflow,
        "--json",
        "databaseId,status,conclusion,event,headBranch,createdAt",
        "--limit",
        "20",
    )
    try:
        runs = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"gh run list returned invalid JSON: {exc}") from exc
    if not isinstance(runs, list):
        raise ValueError(f"gh run list returned an unexpected JSON shape: {runs!r}")
    matches = [
        run
        for run in runs
        if isinstance(run, dict) and run.get("event") == "push" and run.get("headBranch") == "main"
    ]
    if not matches:
        return None
    # Several main-push CI runs can exist for the same SHA (e.g. a retried
    # push); the earliest one is the run the release runbook actually
    # waited on, so it is the one this gate trusts.
    matches.sort(key=lambda run: run.get("createdAt") or "")
    return matches[0]


def wait_for_conclusion(
    repo: str,
    run_id: str,
    timeout_seconds: int = 1800,
    poll_seconds: int = 30,
    gh: GhRunner = _gh,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """Poll a run until it reaches a terminal status, then return its conclusion.

    Raises TimeoutError if `timeout_seconds` elapses before the run
    completes.
    """

    elapsed = 0
    while True:
        raw = gh("run", "view", run_id, "--repo", repo, "--json", "status,conclusion")
        try:
            run = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"gh run view returned invalid JSON: {exc}") from exc
        if not isinstance(run, dict):
            raise ValueError(f"gh run view returned an unexpected JSON shape: {run!r}")
        if run.get("status") == "completed":
            return run.get("conclusion") or ""
        if elapsed >= timeout_seconds:
            raise TimeoutError(
                f"CI run {run_id} in {repo} did not complete within {timeout_seconds}s"
            )
        sleep(poll_seconds)
        elapsed += poll_seconds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/repo, e.g. mjonuschat/foci")
    parser.add_argument("--sha", required=True, help="Commit SHA the release tag points at")
    parser.add_argument("--workflow", default="CI", help="Workflow name to check (default: CI)")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=1800,
        help="Maximum time to wait for the CI run to complete (default: 1800)",
    )
    args = parser.parse_args(argv)

    try:
        run = find_main_push_ci_run(args.repo, args.sha, args.workflow)
        if run is None:
            print(
                f"FAIL: no {args.workflow} run triggered by a push of {args.sha} "
                f"to main was found in {args.repo}"
            )
            return 1
        conclusion = wait_for_conclusion(
            args.repo, str(run["databaseId"]), timeout_seconds=args.timeout_seconds
        )
    except subprocess.CalledProcessError as exc:
        print(f"FAIL: gh command failed: {exc}")
        return 1
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1
    except TimeoutError as exc:
        print(f"FAIL: {exc}")
        return 1

    if conclusion != "success":
        print(f"FAIL: {args.workflow} run for {args.sha} on main concluded '{conclusion}'")
        return 1

    print(f"OK: {args.workflow} run for {args.sha} on main succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
