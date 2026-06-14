"""Regression guards for board-local motor-control policy drift."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPENFFBOARD_MAIN = Path("boards/openffboard-fw/src/main.rs")
OUROBOROS_MAIN = Path("boards/ouroboros-fw/src/main.rs")
OPENFFBOARD_REQUEST = Path("boards/openffboard-fw/src/tmc_control/request.rs")
OUROBOROS_REQUEST = Path("boards/ouroboros-fw/src/tmc_control/request.rs")
OPENFFBOARD_TRIGGER_DOMAIN = Path("boards/openffboard-fw/src/trigger_domain.rs")
OUROBOROS_TRIGGER_DOMAIN = Path("boards/ouroboros-fw/src/trigger_domain.rs")


def read(path: Path) -> str:
    return (ROOT / path).read_text()


def extract_fn(text: str, name: str) -> str:
    marker = f"fn {name}"
    start = text.index(marker)
    brace_start = text.index("{", start)
    depth = 0
    for index in range(brace_start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError(f"unterminated {name} function")


def test_ouroboros_config_reset_uses_shared_channel_reset_policy():
    text = read(OUROBOROS_MAIN)

    assert "TmcControlRuntime::reset_channel_state(" in text
    assert "velocity_limit_cfg.store(500_000" not in text
    assert "position_p_value.store(640" not in text
    assert (
        "stepper_state(channel)\n                        .position\n                        .store(0"
        not in text
    )


def test_both_boards_use_shared_shutdown_safe_state_policy():
    for rel_path in [OPENFFBOARD_MAIN, OUROBOROS_MAIN]:
        text = read(rel_path)

        assert "apply_shutdown_safe_state(" in text


def test_physical_trigger_stop_helpers_do_not_dearm_motor_policy():
    for rel_path in [OPENFFBOARD_TRIGGER_DOMAIN, OUROBOROS_TRIGGER_DOMAIN]:
        text = read(rel_path)
        stop_physical = extract_fn(text, "stop_physical_stepper_no_lock")

        assert "motor_armed.store(false" not in stop_physical


def test_request_normal_tail_policy_matches_openffboard():
    for rel_path in [OPENFFBOARD_REQUEST, OUROBOROS_REQUEST]:
        text = read(rel_path)
        normal_tail = extract_fn(text, "normal_tail")

        assert "TmcControlRequestTail::SkipTickTail" in normal_tail
        assert "TmcControlRequestTail::FallThrough" not in normal_tail


def test_ouroboros_requests_enter_shared_runner_without_local_preclassification():
    text = read(OUROBOROS_MAIN)

    assert ".classify_request(req.clone())" not in text
    assert "TmcPreRequestDisposition::ContinueRequest" in text


def test_ouroboros_slow_pid_homing_policy_uses_shared_helper():
    text = read(OUROBOROS_MAIN)

    assert ".apply_slow_channel_maintenance_tick(" in text
    assert (
        "if runtime.is_motor_enabled() {\n                    let homing_result"
        not in text
    )
    assert "status_poll_counters.fill(0)" in text
