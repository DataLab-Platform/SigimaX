# -*- coding: utf-8 -*-
"""
CI helpers used by the GitHub release workflow (``.github/workflows/release.yml``).

Release tags are either ``vX.Y.Z`` (final release, published on PyPI) or
``vX.Y.Z-rcN`` (release candidate, published on TestPyPI). The matching
``sigimax.__version__`` is ``X.Y.Z`` or ``X.Y.ZrcN`` (PEP 440).

Subcommands
-----------

``tag-info``
    Validate a release tag and print ``key=value`` lines that can be appended
    to ``$GITHUB_OUTPUT``: ``version`` (PEP 440 version) and ``prerelease``
    (``true`` or ``false``).

``check-tag``
    Check that a release tag matches ``sigimax.__version__`` exactly.
    Fails with exit code 1 on mismatch.

``release-notes``
    Extract the section of ``doc/release_notes/release_<MAJ>.<MIN:02d>.md``
    for the given tag (from its ``## SigimaX Version X.Y.Z`` heading up to the
    next version) to stdout (or to ``--output`` file). Fails with exit code 1
    if there is no such section, except for release candidates, whose notes
    may not be written yet.

``check-unpublished``
    Check with the GitHub API that no release has been published yet for the
    given tag: the release workflow creates the release itself, as a draft.
    Fails with exit code 1 if a published release exists. Uses the
    ``GITHUB_REPOSITORY``, ``GITHUB_API_URL`` and ``GH_TOKEN`` (or
    ``GITHUB_TOKEN``) environment variables.

These commands are intentionally dependency-free (stdlib only) so they
can run on a minimal Python install at the very start of a CI job.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RELEASE_NOTES_DIR = REPO_ROOT / "doc" / "release_notes"

TAG_RE = re.compile(
    r"^v(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-rc(?P<rc>[1-9]\d*))?$"
)


@dataclass(frozen=True)
class ReleaseTag:
    """Release tag ``vX.Y.Z`` or ``vX.Y.Z-rcN``."""

    major: int
    minor: int
    patch: int
    rc: int | None

    @property
    def base_version(self) -> str:
        """Final version targeted by the tag (``X.Y.Z``)."""
        return f"{self.major}.{self.minor}.{self.patch}"

    @property
    def version(self) -> str:
        """PEP 440 version of the tag (``X.Y.Z`` or ``X.Y.ZrcN``)."""
        if self.rc is None:
            return self.base_version
        return f"{self.base_version}rc{self.rc}"

    @property
    def prerelease(self) -> bool:
        """Whether the tag is a release candidate."""
        return self.rc is not None


def _parse_tag(tag: str) -> ReleaseTag:
    """Parse a release tag, exiting with an error if it is not valid."""
    match = TAG_RE.match(tag)
    if not match:
        raise SystemExit(
            f"::error::Tag {tag!r} is not a release tag: expected vX.Y.Z "
            "(final release) or vX.Y.Z-rcN (release candidate)"
        )
    return ReleaseTag(
        int(match["major"]),
        int(match["minor"]),
        int(match["patch"]),
        int(match["rc"]) if match["rc"] else None,
    )


def cmd_tag_info(args: argparse.Namespace) -> int:
    tag = _parse_tag(args.tag)
    print(f"version={tag.version}")
    print(f"prerelease={str(tag.prerelease).lower()}")
    return 0


def _read_sigimax_version() -> str:
    metadata = REPO_ROOT / "sigimax" / "_metadata.py"
    text = metadata.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit(f"Could not find __version__ in {metadata}")
    return match.group(1)


def cmd_check_tag(args: argparse.Namespace) -> int:
    tag = _parse_tag(args.tag)
    code_version = _read_sigimax_version()
    if tag.version != code_version:
        print(
            f"::error::Tag {args.tag} requires sigimax.__version__ = "
            f"{tag.version!r}, found {code_version!r}",
            file=sys.stderr,
        )
        return 1
    print(f"Tag {args.tag} matches sigimax.__version__={code_version}")
    return 0


def _release_notes_path(tag: ReleaseTag) -> Path:
    return RELEASE_NOTES_DIR / f"release_{tag.major}.{tag.minor:02d}.md"


def _extract_version_section(text: str, version: str) -> str | None:
    """Return the ``## SigimaX Version <version>`` section of release notes."""
    heading_re = re.compile(rf"^## SigimaX Version {re.escape(version)}(?![\w.])")
    lines = text.splitlines()
    for start, line in enumerate(lines):
        if heading_re.match(line):
            break
    else:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith(("# ", "## ")):
            end = index
            break
    return "\n".join(lines[start:end]).rstrip() + "\n"


def cmd_release_notes(args: argparse.Namespace) -> int:
    tag = _parse_tag(args.tag)
    path = _release_notes_path(tag)
    section = None
    if path.is_file():
        section = _extract_version_section(
            path.read_text(encoding="utf-8"), tag.base_version
        )
    where = (
        f"'## SigimaX Version {tag.base_version}' in "
        f"{path.relative_to(REPO_ROOT).as_posix()}"
    )
    if tag.prerelease:
        if section is None:
            print(f"::warning::Release notes not found ({where})", file=sys.stderr)
            section = f"## SigimaX Version {tag.base_version} ##\n"
        section = (
            f"> Release candidate {tag.version} of SigimaX {tag.base_version}, "
            "published on TestPyPI for testing only.\n\n" + section
        )
    elif section is None:
        print(f"::error::Release notes not found ({where})", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(section, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        # Force UTF-8 on stdout so the script works on Windows consoles too.
        sys.stdout.buffer.write(section.encode("utf-8"))
    return 0


def _get_published_release(repo: str, tag: str) -> dict | None:
    """Return the published release of a tag, or None (drafts are ignored)."""
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    url = f"{api_url}/repos/{repo}/releases/tags/{urllib.parse.quote(tag)}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def cmd_check_unpublished(args: argparse.Namespace) -> int:
    _parse_tag(args.tag)
    repo = args.repo or os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise SystemExit("::error::No repository: use --repo or GITHUB_REPOSITORY")
    release = _get_published_release(repo, args.tag)
    if release is None:
        print(f"No release published yet for {args.tag}")
        return 0
    print(
        f"::error title=Release already published::A release was already "
        f"published for {args.tag} ({release['html_url']}). Releases must never "
        "be created by hand: this workflow prepares a draft release that only "
        "has to be published. See RELEASING.md to recover.",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_info = sub.add_parser(
        "tag-info", help="Validate a release tag and print its version info"
    )
    p_info.add_argument("tag", help="Release tag, e.g. v1.3.0 or v1.3.0-rc1")
    p_info.set_defaults(func=cmd_tag_info)

    p_check = sub.add_parser(
        "check-tag", help="Validate tag against sigimax.__version__"
    )
    p_check.add_argument("tag", help="Release tag, e.g. v1.3.0 or v1.3.0-rc1")
    p_check.set_defaults(func=cmd_check_tag)

    p_notes = sub.add_parser(
        "release-notes", help="Print the release notes of the given tag"
    )
    p_notes.add_argument("tag", help="Release tag, e.g. v1.3.0 or v1.3.0-rc1")
    p_notes.add_argument(
        "-o", "--output", help="Optional output file (default: stdout)"
    )
    p_notes.set_defaults(func=cmd_release_notes)

    p_unpublished = sub.add_parser(
        "check-unpublished", help="Check that no release is published for the tag"
    )
    p_unpublished.add_argument("tag", help="Release tag, e.g. v1.3.0 or v1.3.0-rc1")
    p_unpublished.add_argument(
        "--repo", help="Repository owner/name (default: $GITHUB_REPOSITORY)"
    )
    p_unpublished.set_defaults(func=cmd_check_unpublished)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
