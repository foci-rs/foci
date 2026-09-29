"""Tests for tools/ci/release_ci_gate.py's main-branch CI verification."""

from __future__ import annotations

import json
import subprocess

import release_ci_gate as gate


def _runs_json(runs: list[dict]) -> str:
    return json.dumps(runs)


def test_find_main_push_ci_run_returns_matching_run() -> None:
    runs = [
        {
            "databaseId": 111,
            "status": "completed",
            "conclusion": "success",
            "event": "push",
            "headBranch": "main",
        },
    ]
    fake_gh = lambda *args: _runs_json(runs)  # noqa: E731
    run = gate.find_main_push_ci_run("foci-rs/foci", "abc123", gh=fake_gh)
    assert run is not None
    assert run["databaseId"] == 111


def test_find_main_push_ci_run_ignores_tag_push_event() -> None:
    runs = [
        {
            "databaseId": 222,
            "status": "completed",
            "conclusion": "success",
            "event": "push",
            "headBranch": "v0.4.0",
        },
    ]
    fake_gh = lambda *args: _runs_json(runs)  # noqa: E731
    run = gate.find_main_push_ci_run("foci-rs/foci", "abc123", gh=fake_gh)
    assert run is None


def test_find_main_push_ci_run_returns_none_when_no_runs() -> None:
    fake_gh = lambda *args: _runs_json([])  # noqa: E731
    run = gate.find_main_push_ci_run("foci-rs/foci", "abc123", gh=fake_gh)
    assert run is None


def test_find_main_push_ci_run_picks_earliest_when_several_match() -> None:
    runs = [
        {
            "databaseId": 333,
            "status": "completed",
            "conclusion": "success",
            "event": "push",
            "headBranch": "main",
            "createdAt": "2026-09-27T12:00:00Z",
        },
        {
            "databaseId": 111,
            "status": "completed",
            "conclusion": "success",
            "event": "push",
            "headBranch": "main",
            "createdAt": "2026-09-27T09:00:00Z",
        },
    ]
    fake_gh = lambda *args: _runs_json(runs)  # noqa: E731
    run = gate.find_main_push_ci_run("foci-rs/foci", "abc123", gh=fake_gh)
    assert run is not None
    assert run["databaseId"] == 111


def test_find_main_push_ci_run_raises_value_error_on_malformed_json() -> None:
    fake_gh = lambda *args: "not json"  # noqa: E731
    try:
        gate.find_main_push_ci_run("foci-rs/foci", "abc123", gh=fake_gh)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_find_main_push_ci_run_raises_value_error_on_unexpected_shape() -> None:
    fake_gh = lambda *args: json.dumps({"message": "not a list"})  # noqa: E731
    try:
        gate.find_main_push_ci_run("foci-rs/foci", "abc123", gh=fake_gh)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_wait_for_conclusion_returns_immediately_when_completed() -> None:
    fake_gh = lambda *args: json.dumps({"status": "completed", "conclusion": "success"})  # noqa: E731
    sleeps: list[float] = []
    conclusion = gate.wait_for_conclusion("foci-rs/foci", "111", gh=fake_gh, sleep=sleeps.append)
    assert conclusion == "success"
    assert sleeps == []


def test_wait_for_conclusion_polls_until_completed() -> None:
    responses = [
        json.dumps({"status": "in_progress", "conclusion": None}),
        json.dumps({"status": "completed", "conclusion": "failure"}),
    ]
    calls = iter(responses)
    fake_gh = lambda *args: next(calls)  # noqa: E731
    sleeps: list[float] = []
    conclusion = gate.wait_for_conclusion(
        "foci-rs/foci",
        "111",
        poll_seconds=5,
        gh=fake_gh,
        sleep=sleeps.append,
    )
    assert conclusion == "failure"
    assert sleeps == [5]


def test_wait_for_conclusion_raises_timeout_error_when_never_completes() -> None:
    fake_gh = lambda *args: json.dumps({"status": "in_progress", "conclusion": None})  # noqa: E731
    sleeps: list[float] = []
    try:
        gate.wait_for_conclusion(
            "foci-rs/foci",
            "111",
            timeout_seconds=10,
            poll_seconds=5,
            gh=fake_gh,
            sleep=sleeps.append,
        )
        raise AssertionError("expected TimeoutError")
    except TimeoutError:
        pass
    assert sleeps == [5, 5]


def test_main_exits_zero_when_ci_success(monkeypatch, capsys) -> None:
    monkeypatch.setattr(gate, "find_main_push_ci_run", lambda *a, **k: {"databaseId": 111})
    monkeypatch.setattr(gate, "wait_for_conclusion", lambda *a, **k: "success")
    exit_code = gate.main(["--repo", "foci-rs/foci", "--sha", "abc123"])
    assert exit_code == 0
    assert "OK" in capsys.readouterr().out


def test_main_exits_nonzero_when_ci_failed(monkeypatch, capsys) -> None:
    monkeypatch.setattr(gate, "find_main_push_ci_run", lambda *a, **k: {"databaseId": 111})
    monkeypatch.setattr(gate, "wait_for_conclusion", lambda *a, **k: "failure")
    exit_code = gate.main(["--repo", "foci-rs/foci", "--sha", "abc123"])
    assert exit_code == 1
    assert "FAIL" in capsys.readouterr().out


def test_main_exits_nonzero_when_no_matching_run_found(monkeypatch, capsys) -> None:
    monkeypatch.setattr(gate, "find_main_push_ci_run", lambda *a, **k: None)
    exit_code = gate.main(["--repo", "foci-rs/foci", "--sha", "abc123"])
    assert exit_code == 1
    assert "FAIL" in capsys.readouterr().out


def test_main_exits_nonzero_when_gh_command_fails(monkeypatch, capsys) -> None:
    def fake_find(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=["gh", "run", "list"])

    monkeypatch.setattr(gate, "find_main_push_ci_run", fake_find)
    exit_code = gate.main(["--repo", "foci-rs/foci", "--sha", "abc123"])
    assert exit_code == 1
    assert "FAIL" in capsys.readouterr().out


def test_main_exits_nonzero_when_gh_returns_malformed_json(monkeypatch, capsys) -> None:
    def fake_find(*args, **kwargs):
        raise ValueError("gh run list returned invalid JSON")

    monkeypatch.setattr(gate, "find_main_push_ci_run", fake_find)
    exit_code = gate.main(["--repo", "foci-rs/foci", "--sha", "abc123"])
    assert exit_code == 1
    assert "FAIL" in capsys.readouterr().out
