"""Classify a release tag/version as a normal release or a pre-release.

A tag such as v0.3.1-rc.1 carries a SemVer pre-release identifier and must
never become the repository's "Latest" release; a plain vX.Y.Z tag is a
normal release. This one-line classification decides whether
`gh release create` gets `--prerelease`.
"""

from __future__ import annotations

import argparse
import sys


def parse_tag(tag: str) -> str:
    """Strip a leading "v" from a release tag, e.g. "v0.3.1-rc.1" -> "0.3.1-rc.1"."""

    return tag[1:] if tag.startswith("v") else tag


def is_prerelease(version: str) -> bool:
    """Return True if `version` carries a SemVer pre-release identifier.

    SemVer marks a pre-release with a hyphen before the identifier
    (MAJOR.MINOR.PATCH-identifier), checked before any build-metadata
    suffix. Build metadata ("+...") is stripped first because it may itself
    contain a hyphen (e.g. "0.3.1+build-meta") without making the version a
    pre-release.
    """

    core = version.split("+", 1)[0]
    return "-" in core


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="Release tag, e.g. v0.3.1-rc.1")
    args = parser.parse_args(argv)
    version = parse_tag(args.tag)
    print("prerelease" if is_prerelease(version) else "release")
    return 0


if __name__ == "__main__":
    sys.exit(main())
