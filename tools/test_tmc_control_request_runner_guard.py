"""Regression guards for shared TMC control request runner delegation."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPENFFBOARD_REQUEST = Path("boards/openffboard-fw/src/tmc_control/request.rs")
OUROBOROS_REQUEST = Path("boards/ouroboros-fw/src/tmc_control/request.rs")
OUROBOROS_EFFECTS = Path("boards/ouroboros-fw/src/tmc_control/effects.rs")
SHARED_REQUEST = Path("shared/foci-firmware/src/tmc_control/request.rs")
SHARED_POLICY_KINDS = [
    "TmcRequestKind::SetEnable",
    "TmcRequestKind::Calibrate",
    "TmcRequestKind::Commission",
    "TmcRequestKind::Tune",
    "TmcRequestKind::SelfTest",
    "TmcRequestKind::SetPidGains",
    "TmcRequestKind::SetPositionGains",
]


def read(path: Path) -> str:
    return (ROOT / path).read_text()


def extract_async_fn(text: str, name: str) -> str:
    marker = f"async fn {name}"
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


def test_board_request_handlers_delegate_to_shared_runner():
    for rel_path in [OPENFFBOARD_REQUEST, OUROBOROS_REQUEST]:
        text = read(rel_path)

        assert "handle_tmc_control_request_with_stages(" in text
        assert "TmcRequestBoard" in text
        assert (
            "use foci_firmware::tmc_control::request::"
            "handle_tmc_control_request_with_stages;" in text
        )


def test_board_request_files_do_not_match_shared_policy_arms_locally():
    for rel_path in [OPENFFBOARD_REQUEST, OUROBOROS_REQUEST]:
        text = read(rel_path)

        for marker in SHARED_POLICY_KINDS:
            assert marker not in text


def test_no_board_local_no_gains_calibrate_constructor():
    for rel_path in [OPENFFBOARD_REQUEST, OUROBOROS_REQUEST]:
        text = read(rel_path)

        assert "new_calibrate_for_tmc_with_trace_seq" not in text


def test_shared_runner_owns_gain_seeded_calibration_and_tune_restore():
    text = read(SHARED_REQUEST)

    assert "new_calibrate_for_tmc_with_gains_and_trace_seq" in text
    assert "runtime.stored_gains()" in text
    assert "new_outer_for_tmc_with_breakaway_campaign" in text
    assert "tune_route" in text
    assert "restore_phase_advance_now" in text


def test_extracted_arm_motor_hooks_do_not_disarm():
    for rel_path in [OPENFFBOARD_REQUEST, OUROBOROS_REQUEST]:
        text = read(rel_path)
        arm_motor = extract_async_fn(text, "arm_motor")

        assert "disarm_motor" not in arm_motor


def test_openffboard_preserves_no_commission_active_gate():
    text = read(OPENFFBOARD_REQUEST)
    hook = extract_fn(text, "commissioning_blocked")

    assert "false" in hook
    assert "is_commission_active" not in hook
    assert "commission_in_flight" not in hook


def test_disable_stop_actions_use_stepper_stop():
    openffboard = read(OPENFFBOARD_REQUEST.parent / "effects.rs")
    ouroboros = read(OUROBOROS_EFFECTS)

    assert "BoardAction::Stepper(StepperAction::StopNow) => stepper_stop_from_p1(0)" in openffboard
    assert "BoardAction::Stepper(StepperAction::StopNow) => {" in ouroboros
    assert "stepper_stop_from_p1(channel)" in ouroboros


def test_ouroboros_effects_use_shared_pre_request_disposition():
    text = read(OUROBOROS_EFFECTS)

    assert "TmcPreRequestDisposition" in text
    assert "enum ActionDisposition" not in text
