"""Regression guard for active diagnostic reply sink delegation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPENFFBOARD_DIAGNOSTICS = Path("boards/openffboard-fw/src/tmc_diagnostics.rs")
OUROBOROS_DIAGNOSTICS = Path("boards/ouroboros-fw/src/tmc_diagnostics.rs")
OUROBOROS_REQUEST = Path("boards/ouroboros-fw/src/tmc_control/request.rs")
SINK_MARKER = (
    "impl foci_firmware::tmc_diagnostics::DiagnosticReplySink "
    "for BoardDiagnosticReplySink"
)
DIAGNOSTIC_REPLY_TYPES = [
    "FociCurrentStepResult",
    "FociCurrentVectorStepResult",
    "FociCurrentTorqueSampleResult",
    "FociCurrentTorqueSampleDetailResult",
    "FociVoltageStepResult",
    "FociImpedanceProfile",
    "FociImpedanceFit",
    "FociImpedanceRun",
]


def read(rel_path: Path) -> str:
    return (ROOT / rel_path).read_text()


def extract_sink_impl(text: str) -> str:
    start = text.index(SINK_MARKER)
    brace_start = text.index("{", start)
    depth = 0
    for index in range(brace_start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError("unterminated BoardDiagnosticReplySink impl")


def test_board_diagnostic_reply_sink_impls_are_byte_identical():
    openffboard = extract_sink_impl(read(OPENFFBOARD_DIAGNOSTICS))
    ouroboros = extract_sink_impl(read(OUROBOROS_DIAGNOSTICS))

    assert openffboard == ouroboros


def test_board_diagnostic_modules_delegate_report_matching_to_shared_firmware():
    for rel_path in [OPENFFBOARD_DIAGNOSTICS, OUROBOROS_DIAGNOSTICS]:
        text = read(rel_path)

        assert SINK_MARKER in text
        assert "foci_firmware::tmc_diagnostics::emit_diagnostic_report" in text
        assert "DiagnosticReport::" not in text
        assert "fn emit_diagnostic_report" not in text


def test_ouroboros_request_no_longer_contains_diagnostic_reply_emission():
    text = read(OUROBOROS_REQUEST)

    assert "crate::tmc_diagnostics::run_diagnostic_request" in text
    assert "DiagnosticReport::" not in text
    for reply_type in DIAGNOSTIC_REPLY_TYPES:
        assert reply_type not in text
