"""Board command/reply parity gate.

Compares the generated Klipper data dictionaries embedded in the OpenFFBoard
and Ouroboros firmware ELFs and fails when their command, reply, enumeration,
or constant surface diverges outside the hardware-topology allowlist.
"""

from __future__ import annotations

import json

DICT_MARKER = b'{"commands":'


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
