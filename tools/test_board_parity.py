"""Unit tests for the board parity gate."""

import json

import pytest

import board_parity


def _dict_json(**overrides) -> bytes:
    base = {
        "commands": {"identify offset=%u count=%u": 1},
        "responses": {"identify_response offset=%u data=%.*s": 0},
        "output": {},
        "config": {"CLOCK_FREQ": 84000000, "MCU": "stm32f407"},
        "enumerations": {"pins": {"PA0": 0}},
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
        "enumerations": {"pins": {"PA0": 0}},
        "app": "foci",
        "license": "MIT OR Apache-2.0",
    }
    base.update(overrides)
    return base


def test_compare_identical_surfaces_has_no_problems():
    assert board_parity.compare_dictionaries(_dict(), _dict()) == []


def test_compare_allows_hardware_constant_value_differences():
    off = _dict(
        config={"CLOCK_FREQ": 84000000, "MCU": "stm32f407", "RECEIVE_WINDOW": 192}
    )
    our = _dict(
        config={"CLOCK_FREQ": 260000000, "MCU": "stm32h723", "RECEIVE_WINDOW": 192}
    )
    assert board_parity.compare_dictionaries(off, our) == []


def test_compare_allows_pins_enumeration_content_difference():
    off = _dict(enumerations={"pins": {"PA0": 0}})
    our = _dict(enumerations={"pins": {"PB7": 12}})
    assert board_parity.compare_dictionaries(off, our) == []


def test_compare_flags_command_only_on_one_board():
    off = _dict()
    our = _dict(commands={**off["commands"], "foci_stepper_stats oid=%c": 9})
    problems = board_parity.compare_dictionaries(off, our)
    assert any("foci_stepper_stats" in p and "Ouroboros" in p for p in problems)


def test_compare_flags_non_allowlisted_constant_value_difference():
    off = _dict(
        config={"CLOCK_FREQ": 84000000, "MCU": "stm32f407", "RECEIVE_WINDOW": 192}
    )
    our = _dict(
        config={"CLOCK_FREQ": 84000000, "MCU": "stm32f407", "RECEIVE_WINDOW": 256}
    )
    problems = board_parity.compare_dictionaries(off, our)
    assert any("RECEIVE_WINDOW" in p for p in problems)


def test_compare_flags_non_allowlisted_enumeration_content_difference():
    off = _dict(enumerations={"pins": {"PA0": 0}, "motor_kind": {"stepper": 2}})
    our = _dict(enumerations={"pins": {"PA0": 0}, "motor_kind": {"stepper": 3}})
    problems = board_parity.compare_dictionaries(off, our)
    assert any("motor_kind" in p for p in problems)


def test_compare_flags_metadata_difference():
    problems = board_parity.compare_dictionaries(_dict(), _dict(license="GPL"))
    assert any("license" in p for p in problems)


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
