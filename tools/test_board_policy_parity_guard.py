"""Regression guards for board-local motor-control policy drift."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPENFFBOARD_MAIN = Path("boards/openffboard-fw/src/main.rs")
OUROBOROS_MAIN = Path("boards/ouroboros-fw/src/main.rs")
OPENFFBOARD_REQUEST = Path("boards/openffboard-fw/src/tmc_control/request.rs")
OUROBOROS_REQUEST = Path("boards/ouroboros-fw/src/tmc_control/request.rs")
OPENFFBOARD_TRIGGER_DOMAIN = Path("boards/openffboard-fw/src/trigger_domain.rs")
OUROBOROS_TRIGGER_DOMAIN = Path("boards/ouroboros-fw/src/trigger_domain.rs")
OPENFFBOARD_USB_TRACE = Path("boards/openffboard-fw/src/usb_trace.rs")
OUROBOROS_USB_TRACE = Path("boards/ouroboros-fw/src/usb_trace.rs")
SHARED_DRIVER = Path("shared/foci-firmware/src/tmc_control/driver.rs")


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
        "stepper_state(channel)\n"
        "                        .position\n"
        "                        .store(0" not in text
    )


def test_both_boards_use_shared_shutdown_safe_state_policy():
    for rel_path in [OPENFFBOARD_MAIN, OUROBOROS_MAIN]:
        text = read(rel_path)

        assert "apply_shutdown_safe_state(" in text


def test_physical_trigger_stop_helpers_do_not_dearm_motor_policy():
    for rel_path in [OPENFFBOARD_TRIGGER_DOMAIN, OUROBOROS_TRIGGER_DOMAIN]:
        text = read(rel_path)

        # The real GPIO/state-reset logic lives in the shared inner
        # function; the two entry points below are thin delegates, so the
        # policy check belongs on the inner function's body.
        stop_physical_inner = extract_fn(text, "stop_physical_stepper_inner")
        assert "motor_armed.store(false" not in stop_physical_inner

        for fn_name in ["stop_physical_stepper_unmasked", "stop_physical_stepper_masked"]:
            wrapper = extract_fn(text, fn_name)

            assert "stop_physical_stepper_inner(" in wrapper


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


def test_ouroboros_emit_metadata_reports_real_values_not_placeholders():
    emit_metadata = extract_fn(read(OUROBOROS_USB_TRACE), "emit_metadata")

    assert "skipped_sample_counter_count: 0" not in emit_metadata
    assert "critical_hz: 0" not in emit_metadata
    assert "control_detail_hz: 0" not in emit_metadata
    assert "status_hz: 0" not in emit_metadata
    assert "pre_configuration_elapsed_ms: 0" not in emit_metadata
    assert 'serial: ""' not in emit_metadata
    assert "serial: trace_serial()" in emit_metadata


def test_both_boards_emit_the_same_lifecycle_event_stream():
    for declaration in [
        "const EVENT_FIRMWARE_BOOT: u16 = 1;",
        "const EVENT_USB_CONFIGURED: u16 = 2;",
        "const EVENT_MOTOR_ARM: u16 = 3;",
        "const EVENT_MOTOR_DISARM: u16 = 4;",
        "const EVENT_STATUS_INTERRUPT: u16 = 9;",
    ]:
        assert declaration in read(OPENFFBOARD_USB_TRACE), f"OpenFFBoard missing {declaration}"
        assert declaration in read(OUROBOROS_USB_TRACE), f"Ouroboros missing {declaration}"


def test_ouroboros_disarm_does_not_zero_stepper_position_policy():
    text = read(OUROBOROS_REQUEST)
    disarm_motor = extract_fn(text, "disarm_motor")

    assert "position" not in disarm_motor


def test_ouroboros_slow_pid_homing_policy_uses_shared_helper():
    # Both boards drive slow-channel maintenance through the shared
    # `ChannelDriver`, not a per-board copy in main.rs -- Ouroboros no longer
    # calls `apply_slow_channel_maintenance_tick` directly, and the manual
    # 1000-tick `status_poll_counters` sampler it used to gate is gone: the
    # scheduler's `StatusAudit` unit class owns that cadence now.
    driver_text = read(SHARED_DRIVER)
    assert ".apply_slow_channel_maintenance_tick(" in driver_text

    text = read(OUROBOROS_MAIN)
    assert "if runtime.is_motor_enabled() {\n                    let homing_result" not in text
    assert "status_poll_counters" not in text
    assert "AuditResult" in text
