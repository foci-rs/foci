#!/usr/bin/env python3
"""Gate the size of each board's specialized RTIC `tmc_control` future.

Two measurements per board/build-variant combination:

- The `tmc_control` async-fn future's total layout size, from
  `-Zprint-type-sizes` output captured during a nightly build (this flag
  is nightly-only).
- Free main-SRAM headroom, from the release ELF's `.data`/`.bss` sizes
  (via `size`) and the SRAM region length declared in the board's
  `memory.x` linker script.

Thresholds are pinned with headroom above measured baselines (2026-09-08):

    OpenFFBoard: future <= 16,384 B (measured 4,864 B release, 4,880 B trace)
                 free SRAM >= 60 KiB (measured 102,988 B release, 91,140 B trace)
    Ouroboros:   future <= 16,384 B (measured 4,936 B release, 4,976 B trace)
                 free SRAM >= 200 KiB (measured 279,340 B release, 267,460 B trace)

To refresh a future-size baseline, capture nightly build output with:

    RUSTFLAGS="-Zprint-type-sizes" cargo +nightly build -p <board> \\
        --release --target <target> [--features trace] \\
        > type-sizes.txt 2>&1
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

TYPE_SIZE_RE = re.compile(
    r"^print-type-size type: `(?P<name>[^`]+)`: (?P<bytes>\d+) bytes,",
    re.MULTILINE,
)
MEMORY_X_REGION_RE = re.compile(
    r"^\s*(?P<name>\w+)\s*(?:\([^)]*\))?\s*:\s*ORIGIN\s*=\s*[^,]+,\s*LENGTH\s*=\s*(?P<length>.+?)\s*$",
    re.MULTILINE,
)
SIZE_SUFFIXES = {"": 1, "K": 1024, "M": 1024 * 1024}
SIZE_SUFFIX_RE = re.compile(r"^(?P<value>\d+)\s*(?P<suffix>[KkMm]?)$")


@dataclass(frozen=True)
class BoardVariant:
    """One board/build-variant combination to gate."""

    board: str
    variant: str
    task_path: str
    memory_x_region: str
    future_max_bytes: int
    free_ram_min_bytes: int
    type_sizes_path: Path
    elf_path: Path
    memory_x_path: Path


def parse_size_literal(literal: str) -> int:
    """Parse a linker-script size literal such as `128K` or `0x20000` into bytes."""

    literal = literal.strip()
    if literal.lower().startswith("0x"):
        return int(literal, 16)
    match = SIZE_SUFFIX_RE.match(literal)
    if match is None:
        raise ValueError(f"unrecognized size literal: {literal!r}")
    return int(match.group("value")) * SIZE_SUFFIXES[match.group("suffix").upper()]


def parse_memory_x_region_bytes(memory_x_text: str, region_name: str) -> int:
    """Return the LENGTH, in bytes, of a named region in a `memory.x` linker script."""

    for match in MEMORY_X_REGION_RE.finditer(memory_x_text):
        if match.group("name") == region_name:
            return parse_size_literal(match.group("length"))
    raise ValueError(f"region not found in memory.x: {region_name!r}")


def parse_future_bytes(type_sizes_text: str, task_path: str) -> int:
    """Return the byte size of one RTIC task's bare async-fn-body future.

    `task_path` is the task's path as RTIC's macro expands it, e.g.
    `app::tmc_control` -- no crate-name qualifier, since `-Zprint-type-sizes`
    reports it relative to the app module regardless of the binary crate's
    own name. Matches only the exact `{async fn body of <task_path>()}` type,
    not the `AsyncTaskExecutor<...>`/`ManuallyDrop<...>`/etc. wrapper types
    that also contain that name as a substring at a handful of bytes larger.
    """

    target = f"{{async fn body of {task_path}()}}"
    for match in TYPE_SIZE_RE.finditer(type_sizes_text):
        if match.group("name") == target:
            return int(match.group("bytes"))
    raise ValueError(f"type not found in print-type-sizes output: {target!r}")


def parse_size_output(size_text: str) -> tuple[int, int]:
    """Return (data_bytes, bss_bytes) from Berkeley-format `size` output."""

    lines = [line for line in size_text.splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError("unexpected `size` output: no data row")
    columns = lines[1].split()
    if len(columns) < 3:
        raise ValueError(f"unexpected `size` output row: {lines[1]!r}")
    return int(columns[1]), int(columns[2])


def free_ram_bytes(region_bytes: int, data_bytes: int, bss_bytes: int) -> int:
    """Return the free bytes remaining in a RAM region after static allocation."""

    return region_bytes - data_bytes - bss_bytes


def run_size(elf_path: Path) -> str:
    """Return `size` output for a release ELF, preferring the LLVM tool from rustup."""

    size_tool = shutil.which("rust-size")
    if size_tool is None:
        sysroot = Path(
            subprocess.run(
                ["rustc", "--print", "sysroot"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        candidates = tuple(sysroot.glob("lib/rustlib/*/bin/llvm-size"))
        if not candidates:
            raise RuntimeError(
                "LLVM size tool not found; install the Rust llvm-tools-preview component"
            )
        size_tool = str(candidates[0])
    completed = subprocess.run(
        [size_tool, str(elf_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def check_variant(variant: BoardVariant) -> list[str]:
    """Measure one board/variant combination and return actionable failure lines."""

    type_sizes_text = variant.type_sizes_path.read_text()
    future_bytes = parse_future_bytes(type_sizes_text, variant.task_path)

    memory_x_text = variant.memory_x_path.read_text()
    region_bytes = parse_memory_x_region_bytes(memory_x_text, variant.memory_x_region)
    data_bytes, bss_bytes = parse_size_output(run_size(variant.elf_path))
    free_bytes = free_ram_bytes(region_bytes, data_bytes, bss_bytes)

    label = f"{variant.board} ({variant.variant})"
    print(
        f"{label}: tmc_control future {future_bytes} bytes "
        f"(max {variant.future_max_bytes}), free SRAM {free_bytes} bytes "
        f"(min {variant.free_ram_min_bytes})"
    )

    failures = []
    if future_bytes > variant.future_max_bytes:
        failures.append(
            f"{label}: tmc_control future is {future_bytes} bytes, "
            f"exceeds {variant.future_max_bytes}-byte budget"
        )
    if free_bytes < variant.free_ram_min_bytes:
        failures.append(
            f"{label}: free SRAM is {free_bytes} bytes, "
            f"below {variant.free_ram_min_bytes}-byte floor"
        )
    return failures


def default_variants(workspace_root: Path) -> list[BoardVariant]:
    """Return the four board/variant combinations this gate checks by default."""

    boards = (
        ("openffboard-fw", "thumbv7em-none-eabi", 16_384, 60 * 1024),
        ("ouroboros-fw", "thumbv7em-none-eabihf", 16_384, 200 * 1024),
    )
    # Cargo builds both variants of a board into the same target-triple output
    # path, so a build's ELF must be copied out under a variant-specific name
    # before the next build overwrites it. CI does this copy immediately
    # after each build; see rtic-future-gate-artifacts in ci.yml.
    artifact_dir = workspace_root / "target" / "rtic-future-gate"
    variants = []
    for package, _target, future_max, free_min in boards:
        board_dir = workspace_root / "boards" / package
        for build_variant, features_suffix in (("release", ""), ("trace", "-trace")):
            variants.append(
                BoardVariant(
                    board=package,
                    variant=build_variant,
                    task_path="app::tmc_control",
                    memory_x_region="RAM",
                    future_max_bytes=future_max,
                    free_ram_min_bytes=free_min,
                    type_sizes_path=workspace_root / f"{package}{features_suffix}-type-sizes.txt",
                    elf_path=artifact_dir / f"{package}{features_suffix}",
                    memory_x_path=board_dir / "memory.x",
                )
            )
    return variants


def main(argv: list[str] | None = None) -> int:
    """Check all board/variant tmc_control future-size and free-SRAM budgets."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path("."),
        help="foci workspace root (default: current directory)",
    )
    args = parser.parse_args(argv)

    variants = default_variants(args.workspace_root)
    all_failures: list[str] = []
    for variant in variants:
        try:
            all_failures.extend(check_variant(variant))
        except (OSError, subprocess.CalledProcessError, ValueError, RuntimeError) as error:
            print(f"error: {variant.board} ({variant.variant}): {error}", file=sys.stderr)
            return 2

    for failure in all_failures:
        print(f"error: {failure}", file=sys.stderr)
    return 1 if all_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
