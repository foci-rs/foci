import pytest

import stack_frame_gate

DISASSEMBLY = """
08000010 <example::domain::helper>:
 8000010: b081          sub sp, #0x4
 8000012: 4770          bx lr
0800f594 <foci_firmware::tmc_control::request::handle_tmc_control_request_with_stages::{{closure}}>:
 800f594: b5f0          push {r4, r5, r6, r7, lr}
 800f596: af03          add r7, sp, #0xc
 800f598: e92d 0f00     push.w {r8, r9, r10, r11}
 800f59c: f5ad 4db5     sub.w sp, sp, #0x5a80
 800f5a0: b08f          sub sp, #0x3c
 800f5a2: 4682          mov r10, r0
0804c71e <main>:
 804c71e: b5b0          push {r4, r5, r7, lr}
 804c720: af02          add r7, sp, #0x8
 804c722: f5ad 4d0f     sub.w sp, sp, #0x8f00
 804c726: b08a          sub sp, #0x28
 804c728: f24e 4017     movw r0, #0xe417
"""


def test_extracts_all_initial_stack_subtractions():
    assert stack_frame_gate.extract_frame_bytes(DISASSEMBLY, "main", exact_symbol=True) == 36_648
    assert (
        stack_frame_gate.extract_frame_bytes(
            DISASSEMBLY,
            "foci_firmware::tmc_control::request::handle_tmc_control_request_with_stages::",
        )
        == 23_228
    )


def test_rejects_missing_named_frame():
    with pytest.raises(ValueError, match="frame not found"):
        stack_frame_gate.extract_frame_bytes(DISASSEMBLY, "missing::frame")


def test_rejects_an_elf_without_the_trace_integral_path():
    with pytest.raises(ValueError, match="trace integral path"):
        stack_frame_gate.require_trace_artifact(DISASSEMBLY)


def test_accepts_an_elf_with_the_trace_integral_path():
    trace_label = (
        "080268d4 <foci_firmware::commissioning::outer::velocity::"
        "integral_sweep::step_velocity_integral_with_trace::{{closure}}>:\n"
    )
    trace_disassembly = DISASSEMBLY + trace_label + (" 80268d4: b081          sub sp, #0x4\n")

    stack_frame_gate.require_trace_artifact(trace_disassembly)


def test_budget_failure_reports_measured_and_allowed_bytes():
    failure = stack_frame_gate.check_budget("main", measured=36_648, maximum=30_000)

    assert failure == "main: 36648-byte frame exceeds 30000-byte budget"
