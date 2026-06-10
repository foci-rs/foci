"""Board command/reply parity gate.

Compares the generated Klipper data dictionaries embedded in the OpenFFBoard
and Ouroboros firmware ELFs and fails when their command, reply, enumeration,
or constant surface diverges outside the hardware-topology allowlist.
"""

from __future__ import annotations

import json
from pathlib import Path

from elftools.elf.elffile import ELFFile

DICT_MARKER = b'{"commands":'


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

# Enumerations whose CONTENT may differ between boards (hardware topology). The
# name must still be present in both dictionaries. The dictionary emits
# enumeration names in snake_case; the exact "pins" key is confirmed against a
# real build in Task 5.
ALLOWED_ENUM_CONTENT_DIFFERENCES = frozenset({"pins"})


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
    problems += _compare_config(
        openffboard.get("config", {}), ouroboros.get("config", {})
    )
    problems += _compare_enumerations(
        openffboard.get("enumerations", {}), ouroboros.get("enumerations", {})
    )
    problems += _compare_metadata(openffboard, ouroboros)
    return problems


def find_dictionary_json(blob: bytes) -> dict:
    """Locate and parse the uncompressed dictionary JSON in a byte blob.

    Scans for the dictionary's opening marker, decodes one JSON object from
    that offset, and accepts it only if it carries the expected top-level
    sections. Raises ``ValueError`` if no valid dictionary object is present.
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
        if isinstance(obj, dict) and {"commands", "responses", "config"} <= obj.keys():
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
