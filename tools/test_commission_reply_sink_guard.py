"""Regression guard for board-local commissioning reply adapters."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD_REPLY_FILES = [
    Path("boards/openffboard-fw/src/ankyra/replies.rs"),
    Path("boards/ouroboros-fw/src/ankyra/replies.rs"),
]
STAGE_B_V3_FORWARDERS = {
    "foci_velocity_stage_b_reproduction_v3_core",
    "foci_velocity_stage_b_reproduction_v3_membership",
    "foci_velocity_stage_b_reproduction_v3_pooled",
    "foci_velocity_stage_b_reproduction_v3_common",
    "foci_velocity_stage_b_reproduction_v3_coverage",
    "foci_velocity_stage_b_reproduction_v3_digest",
}


def test_board_reply_emitters_delegate_to_shared_commission_sink():
    for rel_path in BOARD_REPLY_FILES:
        text = (ROOT / rel_path).read_text()

        assert "foci_firmware::commission_dispatch::emit_terminal_reply" in text
        assert "foci_firmware::commission_dispatch::emit_phase_reply" in text
        assert "impl foci_firmware::commission_dispatch::CommissionReplySink" in text
        assert "ReplyPayload::" not in text
        assert "match payload" not in text
        for method in STAGE_B_V3_FORWARDERS:
            assert method in text, f"{rel_path} is missing {method}"
