"""Regression guard: no test may reach files outside the foci repository."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENTS_INDEX = re.compile(r"Path\(__file__\)\.resolve\(\)\.parents\[(\d+)\]")


def _test_files() -> list[Path]:
    return [
        path
        for path in ROOT.glob("**/test*.py")
        if "target" not in path.parts and ".venv" not in path.parts
    ]


def test_test_files_do_not_resolve_paths_above_the_repository() -> None:
    """A test that climbs above the repo passes only in one checkout layout.

    It fails in a standalone clone, CI, or a git worktree, where the parent
    directories hold something else or nothing.
    """
    escapes = []
    for path in _test_files():
        for match in PARENTS_INDEX.finditer(path.read_text()):
            target = path.resolve().parents[int(match.group(1))]
            if not target.is_relative_to(ROOT):
                escapes.append(f"{path.relative_to(ROOT)}: parents[{match.group(1)}]")
    assert escapes == []
