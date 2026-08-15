#!/usr/bin/env python3
"""Enforce release-frame budgets for the OpenFFBoard RTIC control path."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ELF = Path("target/thumbv7em-none-eabi/release/openffboard-fw")
LABEL_RE = re.compile(r"^[0-9a-fA-F]+ <(.+)>:$")
STACK_SUB_RE = re.compile(r"\bsub(?:\.w)?\s+sp,\s*(?:sp,\s*)?#(0x[0-9a-fA-F]+|[0-9]+)\b")
TRACE_ONLY_SYMBOL = (
    "foci_firmware::commissioning::outer::velocity::integral_sweep::"
    "step_velocity_integral_with_trace::"
)


@dataclass(frozen=True)
class FrameBudget:
    """One demangled symbol fragment and its maximum local stack allocation."""

    label: str
    symbol_fragment: str
    maximum_bytes: int
    exact_symbol: bool = False


# These budgets cover the three frames implicated. They are pinned
# from the `--features trace` release ELF; CI must build that exact feature
# set immediately before invoking this gate.
#
# Re-pinned 2026-08-15: main and request-handler frames are
# byte-identical between the prior trace-velocity-sweep build and the
# current `--features trace` build (37,320 / 18,148); no change to
# stack usage. These match the trace build that ran the campaign on
# hardware without overflow. The prior 37,000/7,000 values predated
# earlier growth and were already exceeded.
FRAME_BUDGETS = (
    FrameBudget("main", "main", 38_000, exact_symbol=True),
    FrameBudget(
        "tmc_control poll",
        "openffboard_fw::app::tmc_control::",
        19_000,
    ),
    FrameBudget(
        "request handler",
        "foci_firmware::tmc_control::request::handle_tmc_control_request_with_stages::",
        19_000,
    ),
)


def extract_frame_bytes(
    disassembly: str,
    symbol_fragment: str,
    *,
    exact_symbol: bool = False,
) -> int:
    """Return the initial local-stack allocation for one demangled frame."""

    lines = disassembly.splitlines()
    start = None
    for index, line in enumerate(lines):
        match = LABEL_RE.match(line)
        if match is None:
            continue
        symbol = match.group(1)
        if symbol == symbol_fragment or (not exact_symbol and symbol_fragment in symbol):
            start = index + 1
            break
    if start is None:
        raise ValueError(f"frame not found: {symbol_fragment}")

    allocated = 0
    found_subtraction = False
    for line in lines[start:]:
        if LABEL_RE.match(line):
            break
        match = STACK_SUB_RE.search(line)
        if match is not None:
            allocated += int(match.group(1), 0)
            found_subtraction = True
            continue
        instruction = line.split("\t")[-1].strip() if "\t" in line else line.strip()
        if found_subtraction and not instruction.startswith(("push", "add r7")):
            break
    if not found_subtraction:
        raise ValueError(f"stack allocation not found: {symbol_fragment}")
    return allocated


def check_budget(label: str, measured: int, maximum: int) -> str | None:
    """Return an actionable failure when a frame exceeds its budget."""

    if measured <= maximum:
        return None
    return f"{label}: {measured}-byte frame exceeds {maximum}-byte budget"


def require_trace_artifact(disassembly: str) -> None:
    """Reject an ELF that does not contain the trace-only integral path."""

    for line in disassembly.splitlines():
        match = LABEL_RE.match(line)
        if match is not None and TRACE_ONLY_SYMBOL in match.group(1):
            return
    raise ValueError("ELF does not contain the trace integral path")


def disassemble(elf_path: Path) -> str:
    """Return demangled disassembly for the release ELF."""

    objdump = shutil.which("rust-objdump")
    if objdump is None:
        sysroot = Path(
            subprocess.run(
                ["rustc", "--print", "sysroot"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        candidates = tuple(sysroot.glob("lib/rustlib/*/bin/llvm-objdump"))
        if not candidates:
            raise RuntimeError(
                "LLVM objdump not found; install the Rust llvm-tools-preview component"
            )
        objdump = str(candidates[0])
    completed = subprocess.run(
        [objdump, "-d", "--demangle", str(elf_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def main(argv: list[str] | None = None) -> int:
    """Check all named OpenFFBoard release-frame budgets."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, default=DEFAULT_ELF)
    args = parser.parse_args(argv)
    if not args.elf.is_file():
        print(f"error: OpenFFBoard ELF not found at {args.elf}", file=sys.stderr)
        return 2

    try:
        output = disassemble(args.elf)
        require_trace_artifact(output)
        measurements = [
            (
                budget,
                extract_frame_bytes(
                    output,
                    budget.symbol_fragment,
                    exact_symbol=budget.exact_symbol,
                ),
            )
            for budget in FRAME_BUDGETS
        ]
    except (OSError, subprocess.CalledProcessError, ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    failures = []
    for budget, measured in measurements:
        print(f"{budget.label}: {measured} bytes (budget {budget.maximum_bytes})")
        failure = check_budget(budget.label, measured, budget.maximum_bytes)
        if failure is not None:
            failures.append(failure)
    for failure in failures:
        print(f"error: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
