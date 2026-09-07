import json
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MANIFEST = _ROOT / "shared/foci-firmware/src/commissioning/vocabulary.toml"
_BASELINE = _ROOT / "tools/vocabulary_baseline.json"


def _manifest():
    return tomllib.loads(_MANIFEST.read_text())


def test_manifest_matches_python_baseline():
    m, b = _manifest(), json.loads(_BASELINE.read_text())
    # phase: manifest (code -> label, trace_ident) equals the live host tables.
    m_phase = {
        str(e["wire_code"]): {"label": e["label"], "trace_ident": e["trace_ident"]}
        for e in m["phase"]
    }
    assert m_phase == b["phase"], "manifest phase codes/labels differ from shipping host tables"
    m_break = {str(e["wire_code"]): e["label"] for e in m["breakaway"]}
    assert m_break == b["breakaway"], "manifest breakaway differs from shipping host tables"
    m_action = {e["label"]: e["wire_code"] for e in m["action"]}
    assert m_action == b["action"], "manifest action differs from shipping ACTION_CODES"


import importlib.util  # noqa: E402

_g = importlib.util.spec_from_file_location(
    "genvocab", _ROOT / "tools/gen_commissioning_vocabulary.py"
)
genvocab = importlib.util.module_from_spec(_g)
_g.loader.exec_module(genvocab)


def _bad(mut):
    m = _manifest()
    mut(m)
    try:
        genvocab.validate(m)
    except genvocab.ManifestError:
        return
    raise AssertionError("validate accepted a malformed manifest")


def test_reserved_action_code_rejected():
    _bad(lambda m: m["action"].append({"ident": "X", "wire_code": 3, "label": "x", "doc": "d"}))


def test_reserved_phase_code_rejected():
    _bad(
        lambda m: m["phase"].append(
            {"ident": "X", "wire_code": 9, "label": "x", "trace_ident": "X", "doc": "d"}
        )
    )


def test_missing_reserved_table_rejected():
    _bad(lambda m: m.pop("reserved"))


def test_altered_reserved_values_rejected():
    _bad(lambda m: m["reserved"].__setitem__("action", [1, 2]))


def test_duplicate_wire_code_rejected():
    _bad(
        lambda m: m["breakaway"].append({"ident": "Dup", "wire_code": 0, "label": "d", "doc": "d"})
    )


def test_duplicate_ident_rejected():
    _bad(
        lambda m: m["breakaway"].append(
            {"ident": "BreakawayProbe", "wire_code": 9, "label": "d", "doc": "d"}
        )
    )


def test_out_of_range_code_rejected():
    _bad(lambda m: m["action"].__setitem__(0, {**m["action"][0], "wire_code": 256}))


def test_keyword_ident_rejected():
    _bad(lambda m: m["action"].__setitem__(0, {**m["action"][0], "ident": "match"}))


def test_missing_required_field_rejected():
    _bad(
        lambda m: m["phase"].__setitem__(
            0, {k: v for k, v in m["phase"][0].items() if k != "trace_ident"}
        )
    )


def test_non_string_label_rejected():
    _bad(lambda m: m["action"].__setitem__(0, {**m["action"][0], "label": 5}))


def test_current_manifest_accepted():
    genvocab.validate(_manifest())


def test_generator_idempotent():
    m = genvocab.load()
    genvocab.validate(m)
    for path, emit in genvocab.TARGETS:
        assert path.read_text() == emit(m)


def test_check_mode_clean():
    assert genvocab.main(["--check"]) == 0
