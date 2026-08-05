"""Regression guard for board Ankyra USB transport adapters."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPENFFBOARD_TRANSPORT = ROOT / "boards/openffboard-fw/src/transport.rs"
OUROBOROS_TRANSPORT = ROOT / "boards/ouroboros-fw/src/transport.rs"


def test_board_transport_adapters_stay_byte_identical() -> None:
    """Keep board-local USB transport adapters structurally converged."""
    assert OPENFFBOARD_TRANSPORT.read_text() == OUROBOROS_TRANSPORT.read_text()
