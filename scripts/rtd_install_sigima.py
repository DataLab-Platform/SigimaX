# -*- coding: utf-8 -*-
"""
Install the development version of Sigima for Read the Docs builds.

SigimaX is developed alongside Sigima: development branches and pull requests
may require a Sigima version which is not yet published on PyPI, so installing
``sigimax[doc]`` from PyPI alone would fail.

This script mirrors the GitHub Actions test workflows:

- tag builds and the ``main`` branch: nothing is done, Sigima is installed from
  PyPI by the regular ``python.install`` step;
- other branches and pull requests: Sigima is installed from the GitHub branch
  with the same name as the SigimaX branch if it exists, otherwise from
  ``develop``. The regular ``python.install`` step then keeps this version as it
  already satisfies SigimaX requirements.

It is intended to be run as a ``build.jobs.pre_install`` step and only relies
on the standard library and ``git``.
"""

from __future__ import annotations

import os
import subprocess
import sys

SIGIMA_REPO = "https://github.com/DataLab-Platform/Sigima.git"
SIGIMAX_REPO = "https://github.com/DataLab-Platform/SigimaX.git"
DEFAULT_BRANCH = "develop"
RELEASE_BRANCH = "main"


def get_remote_branches(url: str) -> dict[str, str]:
    """Return the branches of a remote Git repository.

    Args:
        url: Remote repository URL

    Returns:
        Mapping of branch names to the commit hash of their head
    """
    output = subprocess.run(
        ["git", "ls-remote", "--heads", url],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    branches = {}
    for line in output.splitlines():
        commit, ref = line.split("\t", 1)
        branches[ref.removeprefix("refs/heads/")] = commit
    return branches


def get_sigimax_branch() -> str | None:
    """Return the SigimaX branch being built, if it can be determined.

    For pull request builds, Read the Docs only provides the pull request number,
    so the branch is the one of the SigimaX repository whose head is the commit
    being built.

    Returns:
        Branch name, or None for tag builds and pull requests from forks
    """
    version_type = os.environ.get("READTHEDOCS_VERSION_TYPE")
    if version_type == "branch":
        return os.environ["READTHEDOCS_GIT_IDENTIFIER"]
    if version_type == "external":
        commit = os.environ["READTHEDOCS_GIT_COMMIT_HASH"]
        for branch, head in get_remote_branches(SIGIMAX_REPO).items():
            if head == commit:
                return branch
    return None


def main() -> None:
    """Install Sigima from GitHub for development builds."""
    version_type = os.environ.get("READTHEDOCS_VERSION_TYPE")
    if version_type not in ("branch", "external"):
        print(f"Version type {version_type!r}: Sigima will be installed from PyPI")
        return
    sigimax_branch = get_sigimax_branch()
    if sigimax_branch == RELEASE_BRANCH:
        print(f"Branch {RELEASE_BRANCH!r}: Sigima will be installed from PyPI")
        return
    if sigimax_branch in get_remote_branches(SIGIMA_REPO):
        sigima_branch = sigimax_branch
    else:
        sigima_branch = DEFAULT_BRANCH
    print(f"SigimaX branch: {sigimax_branch!r} -> Sigima branch: {sigima_branch!r}")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-cache-dir",
            f"sigima @ git+{SIGIMA_REPO}@{sigima_branch}",
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
