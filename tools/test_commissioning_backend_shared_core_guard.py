"""Regression guard for board commissioning backend shared-core delegation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD_BACKENDS = [
    ROOT / "boards/openffboard-fw/src/commissioning_backend.rs",
    ROOT / "boards/ouroboros-fw/src/commissioning_backend.rs",
]
FORBIDDEN_ACCESS_TRAITS = [
    "CommissionTmcSpiAccess",
    "CommissionTmcStateAccess",
    "CommissionEnablePinAccess",
    "CommissionConfigAccess",
    "CommissionTimingAccess",
    "CommissionTraceAccess",
]


def test_board_backends_use_shared_commissioning_backend_core() -> None:
    """Boards provide hooks and aliases instead of local access-trait impls."""
    for path in BOARD_BACKENDS:
        text = path.read_text()

        assert "SharedCommissioningBackend" in text
        assert "impl CommissionBackendHooks for" in text


def test_board_backends_do_not_reimplement_shared_access_traits() -> None:
    """Keep the access-trait behavior owned by foci-firmware."""
    for path in BOARD_BACKENDS:
        text = path.read_text()

        for trait in FORBIDDEN_ACCESS_TRAITS:
            assert f"{trait} for" not in text


def test_board_backends_do_not_drive_enable_pin_directly() -> None:
    """Enable-pin drive semantics must stay centralized in the shared backend."""
    for path in BOARD_BACKENDS:
        text = path.read_text()

        assert "enable_pin.set_high(" not in text
        assert "enable_pin.set_low(" not in text
