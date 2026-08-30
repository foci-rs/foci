"""Board protocol and runtime-safety parity gate.

Compares the generated Klipper data dictionaries embedded in the OpenFFBoard
and Ouroboros firmware ELFs and fails when their command, reply, enumeration,
or constant surface diverges outside the hardware-topology allowlist. It also
checks the RTIC task priorities that isolate watchdog service from sustained
commissioning work, and that neither board's interrupt service routines call
defmt -- an ISR that logs risks a reentrant defmt-rtt panic if it preempts a
lower-priority task already mid-log-call.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile

DICT_MARKER = b'{"commands":'

# Default release ELF locations, relative to the foci workspace root.
DEFAULT_OPENFFBOARD_ELF = "target/thumbv7em-none-eabi/release/openffboard-fw"
DEFAULT_OUROBOROS_ELF = "target/thumbv7em-none-eabihf/release/ouroboros-fw"
DEFAULT_OPENFFBOARD_SOURCE = "boards/openffboard-fw/src/main.rs"
DEFAULT_OUROBOROS_SOURCE = "boards/ouroboros-fw/src/main.rs"
DEFAULT_OPENFFBOARD_INTERRUPTS = "boards/openffboard-fw/src/interrupts.rs"
DEFAULT_OUROBOROS_INTERRUPTS = "boards/ouroboros-fw/src/interrupts.rs"

REQUIRED_RTIC_TASK_PRIORITIES = {
    "tmc_control": 1,
    "stats": 1,
    "watchdog": 2,
}

_RTIC_TASK_RE = re.compile(
    r"#\[task\((?P<args>.*?)\)\]\s*async\s+fn\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)",
    re.DOTALL,
)
_RTIC_PRIORITY_RE = re.compile(r"\bpriority\s*=\s*(?P<priority>\d+)\b")


# Constants whose VALUE may differ between boards (hardware topology). Their
# names must still be present in both dictionaries.
ALLOWED_CONSTANT_VALUE_DIFFERENCES = frozenset(
    {
        "CLOCK_FREQ",
        "MCU",
        "RESERVE_PINS_DRV",
        "RESERVE_PINS_LED",
        "RESERVE_PINS_SPI",
        "RESERVE_PINS_STEP",
        "RESERVE_PINS_SWD",
        "RESERVE_PINS_TMC",
        "RESERVE_PINS_USB",
    }
)

# Capability differences are not generic board topology. Each value is pinned
# so either board changing its evidence authority fails parity review.
EXPECTED_CONSTANT_VALUE_DIFFERENCES = {
    "VELOCITY_LIMIT_EVIDENCE_CAPABILITY": (1, 0),
}

# Enumerations whose CONTENT may differ between boards (hardware topology). The
# name must still be present in both dictionaries. The dictionary emits the pin
# enumeration as "pin" (singular); its members are board-specific physical pins,
# and Ouroboros additionally carries a second stepper channel (DIR1/ENA1/STEP1),
# a channel-count-derived difference. Verified against real builds of both
# boards. The "static_string_id" enumeration is intentionally NOT listed: it is
# identical across boards and must stay that way.
ALLOWED_ENUM_CONTENT_DIFFERENCES = frozenset({"pin"})

REQUIRED_STATIC_STRINGS = frozenset({"TMC current limit invalid"})


def _compare_key_sets(kind: str, off: dict, our: dict) -> list[str]:
    problems = []
    for key in sorted(set(off) - set(our)):
        problems.append(f"{kind} only on OpenFFBoard: {key!r}")
    for key in sorted(set(our) - set(off)):
        problems.append(f"{kind} only on Ouroboros: {key!r}")
    return problems


def _compare_config(off: dict, our: dict) -> list[str]:
    problems = _compare_key_sets("constant", off, our)
    for name in sorted(set(off) & set(our)):
        if name in ALLOWED_CONSTANT_VALUE_DIFFERENCES:
            continue
        expected = EXPECTED_CONSTANT_VALUE_DIFFERENCES.get(name)
        if expected is not None:
            actual = (off[name], our[name])
            if actual != expected:
                problems.append(
                    f"constant {name!r} expected "
                    f"OpenFFBoard={expected[0]!r} Ouroboros={expected[1]!r}, got "
                    f"OpenFFBoard={actual[0]!r} Ouroboros={actual[1]!r}"
                )
            continue
        if off[name] != our[name]:
            problems.append(
                f"constant {name!r} value differs: "
                f"OpenFFBoard={off[name]!r} Ouroboros={our[name]!r}"
            )
    return problems


def _compare_enumerations(off: dict, our: dict) -> list[str]:
    problems = _compare_key_sets("enumeration", off, our)
    for name in sorted(set(off) & set(our)):
        if name in ALLOWED_ENUM_CONTENT_DIFFERENCES:
            continue
        if off[name] != our[name]:
            problems.append(f"enumeration {name!r} content differs")
    return problems


def _check_required_static_strings(board: str, enumerations: dict) -> list[str]:
    static_strings = enumerations.get("static_string_id", {})
    return [
        f"required static string missing on {board}: {message!r}"
        for message in sorted(REQUIRED_STATIC_STRINGS - set(static_strings))
    ]


def _compare_metadata(off: dict, our: dict) -> list[str]:
    problems = []
    for field in ("app", "license"):
        if off.get(field) != our.get(field):
            problems.append(
                f"metadata {field!r} differs: "
                f"OpenFFBoard={off.get(field)!r} Ouroboros={our.get(field)!r}"
            )
    return problems


def compare_dictionaries(openffboard: dict, ouroboros: dict) -> list[str]:
    """Return messages for every unexpected surface difference.

    An empty list means the two boards present the same protocol surface within
    the hardware-topology allowlist. Numeric command/response IDs and the
    ``version``/``build_versions`` trailer fields are intentionally not
    compared.
    """
    problems: list[str] = []
    problems += _compare_key_sets(
        "command", openffboard.get("commands", {}), ouroboros.get("commands", {})
    )
    problems += _compare_key_sets(
        "response", openffboard.get("responses", {}), ouroboros.get("responses", {})
    )
    problems += _compare_key_sets(
        "output", openffboard.get("output", {}), ouroboros.get("output", {})
    )
    problems += _compare_config(openffboard.get("config", {}), ouroboros.get("config", {}))
    problems += _compare_enumerations(
        openffboard.get("enumerations", {}), ouroboros.get("enumerations", {})
    )
    problems += _check_required_static_strings("OpenFFBoard", openffboard.get("enumerations", {}))
    problems += _check_required_static_strings("Ouroboros", ouroboros.get("enumerations", {}))
    problems += _compare_metadata(openffboard, ouroboros)
    return problems


def _extract_rtic_task_priorities(source: str) -> dict[str, int]:
    priorities = {}
    for task_match in _RTIC_TASK_RE.finditer(source):
        priority_match = _RTIC_PRIORITY_RE.search(task_match.group("args"))
        if priority_match is not None:
            priorities[task_match.group("name")] = int(priority_match.group("priority"))
    return priorities


def compare_runtime_task_priorities(openffboard_source: str, ouroboros_source: str) -> list[str]:
    """Return messages for missing or unsafe RTIC task priorities."""
    problems = []
    for board, source in (
        ("OpenFFBoard", openffboard_source),
        ("Ouroboros", ouroboros_source),
    ):
        priorities = _extract_rtic_task_priorities(source)
        for task, expected in REQUIRED_RTIC_TASK_PRIORITIES.items():
            actual = priorities.get(task)
            if actual is None:
                problems.append(f"{board} RTIC task {task!r} has no explicit priority")
            elif actual != expected:
                problems.append(
                    f"{board} RTIC task {task!r} priority is {actual}, expected {expected}"
                )
    return problems


def check_no_isr_logging(source: str, board: str) -> list[str]:
    """Return messages for any defmt call found in an ISR-body source file.

    Both boards' interrupts.rs files hold only hardware ISR bodies (see that
    file's own module doc), so any defmt:: call anywhere in it is a real
    reentrant-logging hazard, not a false positive worth narrowing further.
    """
    if "defmt::" in source:
        return [f"{board} interrupts.rs calls defmt:: from an ISR body"]
    return []


def find_dictionary_json(blob: bytes) -> dict:
    """Locate and parse the uncompressed dictionary JSON in a byte blob.

    Scans for the dictionary's opening marker, decodes one JSON object from
    that offset, and accepts it only if its expected top-level sections are
    present and are themselves objects. Raises ``ValueError`` if no valid
    dictionary object is present.

    The remainder of a read-only section continues past the dictionary with
    arbitrary binary, so the slice is decoded with ``errors="replace"``;
    ``raw_decode`` stops at the end of the JSON object and never reads the
    replaced tail. The real dictionary is ASCII, so no replacement character
    can land inside it. The section-type checks below reject a marker
    lookalike whose ``commands`` is, say, a string rather than an object.
    """
    decoder = json.JSONDecoder()
    start = 0
    while True:
        index = blob.find(DICT_MARKER, start)
        if index == -1:
            raise ValueError("no data dictionary marker found")
        text = blob[index:].decode("utf-8", errors="replace")
        try:
            obj, _ = decoder.raw_decode(text)
        except json.JSONDecodeError:
            start = index + 1
            continue
        if (
            isinstance(obj, dict)
            and isinstance(obj.get("commands"), dict)
            and isinstance(obj.get("responses"), dict)
            and isinstance(obj.get("config"), dict)
        ):
            return obj
        start = index + 1


# ELF section header flags (see the ELF spec).
_SHF_WRITE = 0x1
_SHF_ALLOC = 0x2


def extract_dictionary(elf_path: Path) -> dict:
    """Extract the data dictionary JSON from a firmware ELF.

    The dictionary is a ``pub const`` string with no stable symbol, so it is
    located by content within the ELF's allocated, non-writable sections.
    Raises ``FileNotFoundError`` if the ELF is missing and ``ValueError`` if no
    dictionary is found.
    """
    with elf_path.open("rb") as handle:
        elf = ELFFile(handle)
        for section in elf.iter_sections():
            flags = section["sh_flags"]
            if (flags & _SHF_ALLOC) and not (flags & _SHF_WRITE):
                data = section.data()
                if DICT_MARKER in data:
                    try:
                        return find_dictionary_json(data)
                    except ValueError:
                        continue
    raise ValueError(f"no data dictionary found in {elf_path}")


def main(argv: list[str] | None = None) -> int:
    """Run the parity gate. Returns the process exit code."""
    parser = argparse.ArgumentParser(description="Board command/reply parity gate.")
    parser.add_argument(
        "--openffboard",
        type=Path,
        default=Path(DEFAULT_OPENFFBOARD_ELF),
        help="path to the OpenFFBoard release ELF",
    )
    parser.add_argument(
        "--ouroboros",
        type=Path,
        default=Path(DEFAULT_OUROBOROS_ELF),
        help="path to the Ouroboros release ELF",
    )
    parser.add_argument(
        "--openffboard-source",
        type=Path,
        default=Path(DEFAULT_OPENFFBOARD_SOURCE),
        help="path to the OpenFFBoard RTIC application source",
    )
    parser.add_argument(
        "--ouroboros-source",
        type=Path,
        default=Path(DEFAULT_OUROBOROS_SOURCE),
        help="path to the Ouroboros RTIC application source",
    )
    parser.add_argument(
        "--openffboard-interrupts",
        type=Path,
        default=Path(DEFAULT_OPENFFBOARD_INTERRUPTS),
        help="path to the OpenFFBoard ISR-body source",
    )
    parser.add_argument(
        "--ouroboros-interrupts",
        type=Path,
        default=Path(DEFAULT_OUROBOROS_INTERRUPTS),
        help="path to the Ouroboros ISR-body source",
    )
    args = parser.parse_args(argv)

    for label, path in (
        ("OpenFFBoard", args.openffboard),
        ("Ouroboros", args.ouroboros),
    ):
        if not path.is_file():
            print(
                f"error: {label} ELF not found at {path}\n"
                "build both board firmwares first:\n"
                "  cargo build -p openffboard-fw --release --target thumbv7em-none-eabi\n"
                "  cargo build -p ouroboros-fw --release --target thumbv7em-none-eabihf",
                file=sys.stderr,
            )
            return 2

    for label, path in (
        ("OpenFFBoard", args.openffboard_source),
        ("Ouroboros", args.ouroboros_source),
        ("OpenFFBoard", args.openffboard_interrupts),
        ("Ouroboros", args.ouroboros_interrupts),
    ):
        if not path.is_file():
            print(f"error: {label} source not found at {path}", file=sys.stderr)
            return 2

    try:
        openffboard = extract_dictionary(args.openffboard)
        ouroboros = extract_dictionary(args.ouroboros)
    except ValueError as exc:
        print(
            f"error: {exc}\n"
            "the ELF carries no data dictionary; rebuild both board firmwares:\n"
            "  cargo build -p openffboard-fw --release --target thumbv7em-none-eabi\n"
            "  cargo build -p ouroboros-fw --release --target thumbv7em-none-eabihf",
            file=sys.stderr,
        )
        return 2

    problems = compare_dictionaries(openffboard, ouroboros)
    problems += compare_runtime_task_priorities(
        args.openffboard_source.read_text(), args.ouroboros_source.read_text()
    )
    problems += check_no_isr_logging(args.openffboard_interrupts.read_text(), "OpenFFBoard")
    problems += check_no_isr_logging(args.ouroboros_interrupts.read_text(), "Ouroboros")

    if problems:
        print("Board parity gate FAILED:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(
        "Board parity gate passed: protocol surfaces and RTIC priorities match, no ISR logs defmt."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
