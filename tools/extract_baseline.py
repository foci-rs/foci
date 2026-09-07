"""Extract the pre-change host decode tables into vocabulary_baseline.json by
parsing the Python source with `ast` (no imports). Independent oracle for the
manifest's wire codes and labels. Run once against the pre-change tree."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KL = ROOT / "host/klipper-foci"
TR = ROOT / "host/foci-trace/foci_trace"


def _dict_literal(path: Path, name: str) -> dict:
    tree = ast.parse(path.read_text())
    for node in tree.body:
        targets = getattr(node, "targets", []) or ([node.target] if hasattr(node, "target") else [])
        for t in targets:
            if isinstance(t, ast.Name) and t.id == name and isinstance(node.value, ast.Dict):
                return ast.literal_eval(node.value)
    raise KeyError(f"{name} dict literal not found in {path}")


def main() -> int:
    kl_phase = _dict_literal(KL / "commissioning.py", "PHASE_NAMES")
    kl_break = _dict_literal(KL / "velocity_integral.py", "BREAKAWAY_PHASE_NAMES")
    kl_action = _dict_literal(KL / "acceptance_matrix.py", "ACTION_CODES")
    tr_phase = _dict_literal(TR / "protocol.py", "PHASE_NAMES")
    tr_break = _dict_literal(TR / "protocol.py", "BREAKAWAY_PHASE_NAMES")

    assert kl_break == tr_break, "klipper and trace BREAKAWAY_PHASE_NAMES disagree"
    assert set(kl_phase) == set(tr_phase), "klipper and trace PHASE_NAMES code sets disagree"

    baseline = {
        "phase": {
            str(code): {"label": kl_phase[code], "trace_ident": tr_phase[code]} for code in kl_phase
        },
        "breakaway": {str(code): kl_break[code] for code in kl_break},
        "action": dict(kl_action.items()),
    }
    (ROOT / "tools/vocabulary_baseline.json").write_text(
        json.dumps(baseline, indent=2, sort_keys=True) + "\n"
    )
    print("wrote vocabulary_baseline.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
