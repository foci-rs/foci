"""Unit tests for the board parity gate."""

import json

import board_parity
import pytest


def _dict_json(**overrides) -> bytes:
    base = {
        "commands": {"identify offset=%u count=%u": 1},
        "responses": {"identify_response offset=%u data=%.*s": 0},
        "output": {},
        "config": {"CLOCK_FREQ": 84000000, "MCU": "stm32f407"},
        "enumerations": {
            "pin": {"PA0": 0},
            "static_string_id": {"TMC current limit invalid": 1},
        },
        "app": "foci",
        "version": "0.1.0",
        "build_versions": "",
        "license": "MIT OR Apache-2.0",
    }
    base.update(overrides)
    return json.dumps(base, separators=(",", ":")).encode("utf-8")


def test_find_dictionary_json_extracts_object_with_surrounding_noise():
    blob = b"\x00\x01rodata-noise" + _dict_json() + b"\xff\xfetrailing"
    result = board_parity.find_dictionary_json(blob)
    assert result["commands"] == {"identify offset=%u count=%u": 1}
    assert result["config"]["MCU"] == "stm32f407"


def test_find_dictionary_json_skips_marker_lookalikes():
    decoy = b'{"commands":"not really a dict"}'
    blob = b"junk" + decoy + b"more" + _dict_json()
    result = board_parity.find_dictionary_json(blob)
    assert result["responses"] == {"identify_response offset=%u data=%.*s": 0}


def test_find_dictionary_json_skips_lookalike_with_all_keys_but_wrong_types():
    # A marker lookalike that has commands/responses/config keys but whose
    # commands is a string, not an object. The real dictionary follows it.
    decoy = b'{"commands":"x","responses":{},"config":{}}'
    blob = b"junk" + decoy + b"more" + _dict_json()
    result = board_parity.find_dictionary_json(blob)
    assert result["responses"] == {"identify_response offset=%u data=%.*s": 0}


def test_find_dictionary_json_raises_when_absent():
    with pytest.raises(ValueError, match="no data dictionary"):
        board_parity.find_dictionary_json(b"no dictionary here")


def _dict(**overrides) -> dict:
    base = {
        "commands": {"queue_step oid=%c interval=%u count=%hu add=%hi": 5},
        "responses": {"stepper_position oid=%c pos=%i": 3},
        "output": {},
        "config": {
            "CLOCK_FREQ": 84000000,
            "MCU": "stm32f407",
            "RECEIVE_WINDOW": 192,
        },
        "enumerations": {
            "pin": {"PA0": 0},
            "static_string_id": {"TMC current limit invalid": 1},
        },
        "app": "foci",
        "license": "MIT OR Apache-2.0",
    }
    base.update(overrides)
    return base


def test_compare_identical_surfaces_has_no_problems():
    assert board_parity.compare_dictionaries(_dict(), _dict()) == []


def test_compare_allows_hardware_constant_value_differences():
    off = _dict(config={"CLOCK_FREQ": 84000000, "MCU": "stm32f407", "RECEIVE_WINDOW": 192})
    our = _dict(config={"CLOCK_FREQ": 260000000, "MCU": "stm32h723", "RECEIVE_WINDOW": 192})
    assert board_parity.compare_dictionaries(off, our) == []


def test_compare_allows_ouroboros_omitting_empty_reserve_pin_categories():
    # Ouroboros has no DRV-enable pins to reserve: the gate drivers are
    # driven entirely by TMC4671 PWM outputs, with no discrete GPIO enable
    # line. Its own host-tests (board_never_declares_an_empty_reserve_pins_
    # category) require it to omit the constant entirely rather than declare
    # an empty pin list, since Klipper's mcu_identify treats the empty
    # string as a real reserved pin. Only its absence specifically on
    # Ouroboros is allowed.
    off = _dict(
        config={
            "CLOCK_FREQ": 84000000,
            "MCU": "stm32f407",
            "RECEIVE_WINDOW": 192,
            "RESERVE_PINS_DRV": "PB0,PB1,PC4,PC5",
        }
    )
    our = _dict(config={"CLOCK_FREQ": 260000000, "MCU": "stm32h723", "RECEIVE_WINDOW": 192})
    assert board_parity.compare_dictionaries(off, our) == []


def test_compare_allows_reserve_pins_led_value_difference():
    # Unlike RESERVE_PINS_DRV, Ouroboros does have a status LED (PA15) and
    # declares RESERVE_PINS_LED on both boards -- only the pin value legitimately
    # differs (hardware topology), covered by ALLOWED_CONSTANT_VALUE_DIFFERENCES.
    off = _dict(
        config={
            "CLOCK_FREQ": 84000000,
            "MCU": "stm32f407",
            "RECEIVE_WINDOW": 192,
            "RESERVE_PINS_LED": "PD7,PE0,PE1",
        }
    )
    our = _dict(
        config={
            "CLOCK_FREQ": 260000000,
            "MCU": "stm32h723",
            "RECEIVE_WINDOW": 192,
            "RESERVE_PINS_LED": "PA15",
        }
    )
    assert board_parity.compare_dictionaries(off, our) == []


def test_compare_still_flags_other_constants_missing_from_ouroboros():
    off = _dict(
        config={
            "CLOCK_FREQ": 84000000,
            "MCU": "stm32f407",
            "RECEIVE_WINDOW": 192,
            "SOME_OTHER_CONST": 1,
        }
    )
    our = _dict(config={"CLOCK_FREQ": 260000000, "MCU": "stm32h723", "RECEIVE_WINDOW": 192})
    problems = board_parity.compare_dictionaries(off, our)
    assert any("SOME_OTHER_CONST" in p for p in problems)


def test_compare_flags_reserve_pins_led_missing_from_ouroboros():
    # RESERVE_PINS_LED is no longer an allowed omission: Ouroboros must
    # declare its status LED pin.
    off = _dict(
        config={
            "CLOCK_FREQ": 84000000,
            "MCU": "stm32f407",
            "RECEIVE_WINDOW": 192,
            "RESERVE_PINS_LED": "PD7,PE0,PE1",
        }
    )
    our = _dict(config={"CLOCK_FREQ": 260000000, "MCU": "stm32h723", "RECEIVE_WINDOW": 192})
    problems = board_parity.compare_dictionaries(off, our)
    assert any("RESERVE_PINS_LED" in p for p in problems)


def test_compare_still_flags_reserve_pins_missing_from_openffboard():
    # The allowance is asymmetric: Ouroboros may omit these, but OpenFFBoard
    # (which does have LED/DRV pins) must still declare them.
    off = _dict(config={"CLOCK_FREQ": 84000000, "MCU": "stm32f407", "RECEIVE_WINDOW": 192})
    our = _dict(
        config={
            "CLOCK_FREQ": 260000000,
            "MCU": "stm32h723",
            "RECEIVE_WINDOW": 192,
            "RESERVE_PINS_DRV": "PA0",
        }
    )
    problems = board_parity.compare_dictionaries(off, our)
    assert any("RESERVE_PINS_DRV" in p and "Ouroboros" in p for p in problems)


def test_compare_requires_matching_velocity_limit_capabilities():
    off = _dict(
        config={
            "CLOCK_FREQ": 84000000,
            "MCU": "stm32f407",
            "RECEIVE_WINDOW": 192,
            "VELOCITY_LIMIT_EVIDENCE_CAPABILITY": 1,
        }
    )
    our = _dict(
        config={
            "CLOCK_FREQ": 260000000,
            "MCU": "stm32h723",
            "RECEIVE_WINDOW": 192,
            "VELOCITY_LIMIT_EVIDENCE_CAPABILITY": 1,
        }
    )

    assert board_parity.compare_dictionaries(off, our) == []

    our["config"]["VELOCITY_LIMIT_EVIDENCE_CAPABILITY"] = 0
    problems = board_parity.compare_dictionaries(off, our)
    assert problems == [
        "constant 'VELOCITY_LIMIT_EVIDENCE_CAPABILITY' value differs: OpenFFBoard=1 Ouroboros=0"
    ]


def test_compare_allows_pin_enumeration_content_difference():
    static_strings = {"TMC current limit invalid": 1}
    off = _dict(enumerations={"pin": {"PA0": 0}, "static_string_id": static_strings})
    our = _dict(enumerations={"pin": {"PB7": 12}, "static_string_id": static_strings})
    assert board_parity.compare_dictionaries(off, our) == []


def test_compare_flags_command_only_on_one_board():
    off = _dict()
    our = _dict(commands={**off["commands"], "foci_stepper_stats oid=%c": 9})
    problems = board_parity.compare_dictionaries(off, our)
    assert any("foci_stepper_stats" in p and "Ouroboros" in p for p in problems)


def test_compare_flags_non_allowlisted_constant_value_difference():
    off = _dict(config={"CLOCK_FREQ": 84000000, "MCU": "stm32f407", "RECEIVE_WINDOW": 192})
    our = _dict(config={"CLOCK_FREQ": 84000000, "MCU": "stm32f407", "RECEIVE_WINDOW": 256})
    problems = board_parity.compare_dictionaries(off, our)
    assert any("RECEIVE_WINDOW" in p for p in problems)


def test_compare_flags_non_allowlisted_enumeration_content_difference():
    static_strings = {"TMC current limit invalid": 1}
    off = _dict(
        enumerations={
            "pin": {"PA0": 0},
            "static_string_id": static_strings,
            "motor_kind": {"stepper": 2},
        }
    )
    our = _dict(
        enumerations={
            "pin": {"PA0": 0},
            "static_string_id": static_strings,
            "motor_kind": {"stepper": 3},
        }
    )
    problems = board_parity.compare_dictionaries(off, our)
    assert any("motor_kind" in p for p in problems)


def test_compare_requires_current_limit_shutdown_on_both_boards():
    missing = _dict(enumerations={"pin": {"PA0": 0}, "static_string_id": {}})

    problems = board_parity.compare_dictionaries(missing, missing)

    assert problems == [
        "required static string missing on OpenFFBoard: 'TMC current limit invalid'",
        "required static string missing on Ouroboros: 'TMC current limit invalid'",
    ]


def test_compare_flags_metadata_difference():
    problems = board_parity.compare_dictionaries(_dict(), _dict(license="GPL"))
    assert any("license" in p for p in problems)


def _runtime_source(*, tmc_priority=1, stats_priority=1, watchdog_priority=2):
    return f"""
    #[task(priority = {tmc_priority})]
    async fn tmc_control(_ctx: tmc_control::Context) {{}}

    #[task(priority = {stats_priority})]
    async fn stats(_ctx: stats::Context) {{}}

    #[task(priority = {watchdog_priority}, local = [wdg])]
    async fn watchdog(_ctx: watchdog::Context) {{}}
    """


def test_compare_runtime_priorities_accepts_watchdog_above_commissioning():
    source = _runtime_source()
    assert board_parity.compare_runtime_task_priorities(source, source) == []


def test_compare_runtime_priorities_rejects_watchdog_at_commissioning_priority():
    openffboard = _runtime_source(watchdog_priority=1)
    problems = board_parity.compare_runtime_task_priorities(openffboard, _runtime_source())
    assert problems == ["OpenFFBoard RTIC task 'watchdog' priority is 1, expected 2"]


def test_check_no_isr_logging_accepts_clean_source():
    source = """
    pub fn tmc_status_irq() {
        fault_active.store(true, Ordering::Relaxed);
        tmc_disable_signal.signal(());
    }
    """
    assert board_parity.check_no_isr_logging(source, "OpenFFBoard") == []


def test_check_no_isr_logging_flags_defmt_call():
    source = """
    pub fn tmc_status_irq() {
        fault_active.store(true, Ordering::Relaxed);
        tmc_disable_signal.signal(());
        defmt::warn!("TMC4671 STATUS interrupt: fault detected, step timer disabled");
    }
    """
    problems = board_parity.check_no_isr_logging(source, "Ouroboros")
    assert len(problems) == 1
    assert "Ouroboros" in problems[0]
    assert "defmt" in problems[0]


def test_extract_dictionary_missing_file_raises(tmp_path):
    missing = tmp_path / "nope.elf"
    with pytest.raises(FileNotFoundError):
        board_parity.extract_dictionary(missing)


def test_main_missing_elf_reports_build_first(tmp_path, capsys):
    code = board_parity.main(
        [
            "--openffboard",
            str(tmp_path / "a.elf"),
            "--ouroboros",
            str(tmp_path / "b.elf"),
        ]
    )
    assert code == 2
    assert "build both board firmwares first" in capsys.readouterr().err


def test_main_passes_when_surfaces_match(tmp_path, monkeypatch, capsys):
    off = tmp_path / "off.elf"
    our = tmp_path / "our.elf"
    off.write_bytes(b"stub")
    our.write_bytes(b"stub")
    monkeypatch.setattr(board_parity, "extract_dictionary", lambda path: _dict())
    code = board_parity.main(["--openffboard", str(off), "--ouroboros", str(our)])
    assert code == 0
    assert "passed" in capsys.readouterr().out


def test_main_fails_when_surfaces_differ(tmp_path, monkeypatch, capsys):
    off = tmp_path / "off.elf"
    our = tmp_path / "our.elf"
    off.write_bytes(b"stub")
    our.write_bytes(b"stub")

    def fake_extract(path):
        if path.name == "our.elf":
            return _dict(commands={"extra_cmd oid=%c": 9})
        return _dict()

    monkeypatch.setattr(board_parity, "extract_dictionary", fake_extract)
    code = board_parity.main(["--openffboard", str(off), "--ouroboros", str(our)])
    assert code == 1
    assert "FAILED" in capsys.readouterr().err


def test_main_fails_when_runtime_task_priority_is_unsafe(tmp_path, monkeypatch, capsys):
    off = tmp_path / "off.elf"
    our = tmp_path / "our.elf"
    off_source = tmp_path / "openffboard.rs"
    our_source = tmp_path / "ouroboros.rs"
    off.write_bytes(b"stub")
    our.write_bytes(b"stub")
    off_source.write_text(_runtime_source(watchdog_priority=1))
    our_source.write_text(_runtime_source())
    monkeypatch.setattr(board_parity, "extract_dictionary", lambda path: _dict())

    code = board_parity.main(
        [
            "--openffboard",
            str(off),
            "--ouroboros",
            str(our),
            "--openffboard-source",
            str(off_source),
            "--ouroboros-source",
            str(our_source),
        ]
    )

    assert code == 1
    assert "watchdog" in capsys.readouterr().err


def test_main_fails_when_isr_source_logs(tmp_path, monkeypatch, capsys):
    off = tmp_path / "off.elf"
    our = tmp_path / "our.elf"
    off_interrupts = tmp_path / "openffboard_interrupts.rs"
    our_interrupts = tmp_path / "ouroboros_interrupts.rs"
    off.write_bytes(b"stub")
    our.write_bytes(b"stub")
    off_interrupts.write_text("pub fn tmc_status_irq() {}\n")
    our_interrupts.write_text('pub fn tmc_status_irq() {\n    defmt::warn!("fault");\n}\n')
    monkeypatch.setattr(board_parity, "extract_dictionary", lambda path: _dict())

    code = board_parity.main(
        [
            "--openffboard",
            str(off),
            "--ouroboros",
            str(our),
            "--openffboard-interrupts",
            str(off_interrupts),
            "--ouroboros-interrupts",
            str(our_interrupts),
        ]
    )

    assert code == 1
    assert "defmt" in capsys.readouterr().err


def test_main_dictless_elf_reports_error(tmp_path, monkeypatch, capsys):
    # The ELF exists but carries no dictionary (e.g. a stale build). main
    # should exit non-zero with a clean message, not a raw traceback.
    off = tmp_path / "off.elf"
    our = tmp_path / "our.elf"
    off.write_bytes(b"stub")
    our.write_bytes(b"stub")

    def raise_no_dict(path):
        raise ValueError(f"no data dictionary found in {path}")

    monkeypatch.setattr(board_parity, "extract_dictionary", raise_no_dict)
    code = board_parity.main(["--openffboard", str(off), "--ouroboros", str(our)])
    assert code == 2
    assert "no data dictionary" in capsys.readouterr().err
