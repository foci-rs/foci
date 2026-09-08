"""Gate: STATUS_FLAGS is cleared only through the bootstrap and interlock modules.

TMC4671 STATUS_FLAGS bits are sticky. Every production clear outside the
bootstrap safety step must go through the guarded helpers in
tmc_control/interlock.rs so the fault interlock is consulted first. This gate
strips `#[cfg(test)]`-attributed items by brace matching and reports any raw
clear in a file outside the allowlist.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CLEAR_PATTERNS = (
    re.compile(r"STATUS_FLAGS\s*,\s*0\s*,?\s*\)"),
    re.compile(r"STATUS_FLAGS\.addr\(\)\s*,\s*0\s*,?\s*\)"),
)
ALLOWED_WRITERS = (
    Path("shared/foci-firmware/src/tmc_control/bootstrap.rs"),
    Path("shared/foci-firmware/src/tmc_control/interlock.rs"),
)
CFG_TEST = "#[cfg(test)]"


def strip_cfg_test_items(source: str) -> str:
    """Blank out every item that carries a `#[cfg(test)]` attribute.

    The item runs from the attribute to the end of its brace-balanced body
    (or to the terminating `;` for a body-less item). Blanking rather than
    deleting keeps line numbers stable for reporting.
    """

    out = list(source)
    index = 0
    while True:
        start = source.find(CFG_TEST, index)
        if start < 0:
            break
        end = _item_end(source, start + len(CFG_TEST))
        for pos in range(start, end):
            if out[pos] != "\n":
                out[pos] = " "
        index = end
    return "".join(out)


def _item_end(source: str, pos: int) -> int:
    depth = 0
    seen_brace = False
    while pos < len(source):
        char = source[pos]
        if char == "{":
            depth += 1
            seen_brace = True
        elif char == "}":
            depth -= 1
            if seen_brace and depth == 0:
                return pos + 1
        elif char == ";" and not seen_brace:
            return pos + 1
        pos += 1
    return len(source)


def find_clear_sites(source: str) -> list[int]:
    """Return 1-based line numbers of production STATUS_FLAGS clears.

    Matches tolerate rustfmt splitting the call across lines; the reported
    line is the one holding `STATUS_FLAGS`.
    """

    stripped = strip_cfg_test_items(source)
    lines = []
    for pattern in CLEAR_PATTERNS:
        for match in pattern.finditer(stripped):
            lines.append(stripped.count("\n", 0, match.start()) + 1)
    return sorted(set(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Path to the foci workspace root.",
    )
    args = parser.parse_args(argv)
    src_root = args.workspace_root / "shared" / "foci-firmware" / "src"
    failures = []
    writers = []
    for path in sorted(src_root.rglob("*.rs")):
        relative = path.relative_to(args.workspace_root)
        if relative.name == "tests.rs" or "test_support" in relative.name:
            continue
        sites = find_clear_sites(path.read_text())
        if not sites:
            continue
        writers.append(relative)
        if relative not in ALLOWED_WRITERS:
            failures.extend(f"{relative}:{line}" for line in sites)
    for relative in writers:
        print(f"STATUS_FLAGS writer: {relative}")
    for failure in failures:
        print(f"FAIL: raw STATUS_FLAGS clear outside the allowlist: {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
