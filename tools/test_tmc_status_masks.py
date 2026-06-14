"""Safety checks for board-local TMC4671 STATUS flag masks."""

from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
OUROBOROS_SRC = WORKSPACE / "boards" / "ouroboros-fw" / "src"


def test_ouroboros_does_not_treat_status_bit_19_as_pll_fault():
    """TMC4671-LA Rev 1, 02/2024 Table 30 marks STATUS_FLAGS[19] reserved."""
    source = "\n".join(path.read_text() for path in OUROBOROS_SRC.rglob("*.rs"))

    assert "STATUS_NOT_PLL_LOCKED" not in source
    assert "not_PLL_locked" not in source
    assert "PLL not locked" not in source
    assert "1 << 19" not in source
