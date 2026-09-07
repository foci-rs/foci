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
    m_phase = {str(e["wire_code"]): {"label": e["label"], "trace_ident": e["trace_ident"]} for e in m["phase"]}
    assert m_phase == b["phase"], "manifest phase codes/labels differ from shipping host tables"
    m_break = {str(e["wire_code"]): e["label"] for e in m["breakaway"]}
    assert m_break == b["breakaway"], "manifest breakaway differs from shipping host tables"
    m_action = {e["label"]: e["wire_code"] for e in m["action"]}
    assert m_action == b["action"], "manifest action differs from shipping ACTION_CODES"
