"""Tests for tools/ci/release_version.py's prerelease classification."""

from __future__ import annotations

import release_version


def test_is_prerelease_true_for_hyphenated_version() -> None:
    assert release_version.is_prerelease("0.3.1-rc1") is True


def test_is_prerelease_false_for_plain_version() -> None:
    assert release_version.is_prerelease("0.4.0") is False


def test_parse_tag_strips_leading_v() -> None:
    assert release_version.parse_tag("v0.3.1-rc1") == "0.3.1-rc1"


def test_parse_tag_leaves_unprefixed_version_unchanged() -> None:
    assert release_version.parse_tag("0.4.0") == "0.4.0"


def test_main_prints_prerelease_for_rc_tag(capsys) -> None:
    exit_code = release_version.main(["--tag", "v0.3.1-rc1"])
    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "prerelease"


def test_main_prints_release_for_plain_tag(capsys) -> None:
    exit_code = release_version.main(["--tag", "v0.4.0"])
    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "release"
