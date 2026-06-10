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
