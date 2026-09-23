"""Epic-closing guard against retired evidence-lifecycle vocabulary.

Retired the pipeline-stage-letter naming (StageB/StageC and their
snake_case forms), the ambiguous candidate/final `*_p` fields, the leftover
`AcceptanceMatrixProgress` field, and the `CompleteCandidate`/
`complete_candidate` outcome pair, replacing them with maturity-accurate
names (Proportional/Integral, nominated_p/fixed_p, FirstRunRetained, ...).
This scans firmware, host, and board source for the retired tokens so a
future rename, revert, or copy-paste cannot silently reintroduce them.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD_FILE = Path(__file__).resolve()

SCAN_ROOTS = [
    Path("shared/foci-firmware/src"),
    Path("host/klipper-foci"),
    Path("host/foci-trace"),
    Path("boards/openffboard-fw/src"),
    Path("boards/openffboard-fw/host-tests"),
    Path("boards/ouroboros-fw/src"),
    Path("boards/ouroboros-fw/host-tests"),
    Path("tools"),
]

SCAN_EXTENSIONS = {".rs", ".py", ".toml"}

# Case-sensitive stems, matched as a prefix rather than a whole identifier:
# the retired names were always the leading segment of a longer PascalCase
# type or snake_case wire family (`StageBReproductionDecision`,
# `foci_velocity_stage_b_reproduction_v3_`). The lookahead rejects only a
# *lowercase* continuation, so it still catches every retired reappearance
# while sparing unrelated identifiers such as `adc_vm_stage_cfg_with_mode`
# or `residual_stage_code`, whose "stage_c"/"stage_b" is a coincidental
# substring spanning into a different word ("cfg", "code").
STEM_PATTERNS = {
    "StageB": re.compile(r"StageB(?![a-z])"),
    "StageC": re.compile(r"StageC(?![a-z])"),
    "stage_b": re.compile(r"stage_b(?![a-zA-Z])"),
    "stage_c": re.compile(r"stage_c(?![a-zA-Z])"),
    "STAGE_B": re.compile(r"STAGE_B(?![A-Za-z])"),
    "STAGE_C": re.compile(r"STAGE_C(?![A-Za-z])"),
}

# Whole-identifier tokens, bounded on both sides (word characters include
# `_`), so these fire only when the retired name is the complete token, not
# a substring of an unrelated identifier such as a test's local
# `candidate_p724` variable or the unrelated `final_poll` method.
WHOLE_TOKEN_PATTERNS = {
    "candidate_p_raw": re.compile(r"\bcandidate_p_raw\b"),
    "candidate_p": re.compile(r"\bcandidate_p\b"),
    "final_p": re.compile(r"\bfinal_p\b"),
}

# Long and specific enough that a plain substring check carries no
# realistic false-positive risk.
SUBSTRING_TOKENS = (
    "AcceptanceMatrixProgress",
    "stage_c_resume",
    "complete_candidate",
    "CompleteCandidate",
    "COMPLETE_CANDIDATE",
)

# Files that intentionally retain a retired token, keyed by path relative to
# this file's parent directory (the `foci` aggregate root):
#
# - The two foci-trace tests translate a handful of fields read out of an
#   archived pre-rename capture (`docs/artifacts/trace-captures/...`) to
#   the current names before validating it; per the epic's hard-break
#   decode policy no back-compat is owed to that capture, so the old key is
#   read once, by name, and immediately renamed.
ALLOWLIST: dict[str, set[str]] = {
    "host/foci-trace/tests/test_velocity_integral.py": {"stage_b", "final_p"},
    "host/foci-trace/tests/test_velocity_measurement.py": {"stage_b"},
}

ALL_PATTERNS = {**STEM_PATTERNS, **WHOLE_TOKEN_PATTERNS}


def _iter_scan_files():
    for scan_root in SCAN_ROOTS:
        base = ROOT / scan_root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in SCAN_EXTENSIONS:
                continue
            if path == GUARD_FILE:
                continue
            yield path


def _line_hits(line: str) -> set[str]:
    hits = {name for name, pattern in ALL_PATTERNS.items() if pattern.search(line)}
    hits.update(token for token in SUBSTRING_TOKENS if token in line)
    return hits


def find_violations() -> list[str]:
    """Return one message per retired-token occurrence not on the allowlist."""

    violations = []
    for path in _iter_scan_files():
        rel = path.relative_to(ROOT).as_posix()
        allowed = ALLOWLIST.get(rel, set())
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for token in sorted(_line_hits(line) - allowed):
                violations.append(f"{rel}:{lineno}: retired token {token!r}: {line.strip()}")
    return violations


def test_no_retired_lifecycle_vocabulary_remains():
    violations = find_violations()
    assert violations == [], "retired vocabulary reappeared:\n" + "\n".join(violations)
