#!/usr/bin/env python3
"""
find_parent_branch.py

Finds the remote branch that most likely originated the current local branch,
by looking for the remote branch whose tip commit is the most recent common
ancestor with the current branch.

Usage:
    python scripts/find_parent_branch.py
    python scripts/find_parent_branch.py --remote origin
    python scripts/find_parent_branch.py --verbose
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def run(cmd: list[str], check: bool = True) -> str:
    """Run a shell command and return its stdout as a stripped string."""
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if check and result.returncode != 0:
        print(f"[error] Command failed: {' '.join(cmd)}", file=sys.stderr)
        print(f"        {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def run_lines(cmd: list[str], check: bool = True) -> list[str]:
    """Run a shell command and return its stdout as a list of non-empty lines."""
    output = run(cmd, check=check)
    return [line for line in output.splitlines() if line.strip()]


# ──────────────────────────────────────────────
# Core logic
# ──────────────────────────────────────────────


@dataclass
class BranchCandidate:
    name: str  # full ref, e.g. origin/main
    merge_base: str  # commit hash of the merge-base with current branch
    distance: int  # number of commits between merge_base and branch tip


def get_current_branch() -> str:
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if branch == "HEAD":
        print(
            "[error] HEAD is detached. Please checkout a branch first.", file=sys.stderr
        )
        sys.exit(1)
    return branch


def get_remote_branches(remote: str) -> list[str]:
    """Return all remote tracking refs for the given remote, excluding HEAD."""
    refs = run_lines(["git", "branch", "--remotes", "--format=%(refname:short)"])
    filtered = [
        r for r in refs if r.startswith(f"{remote}/") and not r.endswith("/HEAD")
    ]
    return filtered


def merge_base(ref_a: str, ref_b: str) -> str | None:
    """Return the merge-base commit between two refs, or None if unrelated."""
    result = subprocess.run(
        ["git", "merge-base", ref_a, ref_b],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def commit_distance(from_commit: str, to_ref: str) -> int:
    """
    Return the number of commits reachable from `to_ref` that are NOT
    reachable from `from_commit` (i.e. how far ahead `to_ref` is from
    `from_commit`).

    A distance of 0 means `from_commit` IS the tip of `to_ref`.
    """
    output = run(
        ["git", "rev-list", "--count", f"{from_commit}..{to_ref}"],
        check=False,
    )
    try:
        return int(output)
    except ValueError:
        return sys.maxsize


def find_parent_branch(
    current_branch: str,
    remote: str,
    verbose: bool,
) -> list[BranchCandidate] | None:
    remote_branches = get_remote_branches(remote)

    if not remote_branches:
        print(
            f"[error] No remote branches found for remote '{remote}'.", file=sys.stderr
        )
        sys.exit(1)

    if verbose:
        print(f"[info] Current branch   : {current_branch}")

    candidates: list[BranchCandidate] = []

    for ref in remote_branches:
        # Skip if the remote branch *is* the current branch itself
        remote_branch_short = ref.removeprefix(f"{remote}/")
        if remote_branch_short == current_branch:
            continue

        base = merge_base(current_branch, ref)
        if base is None:
            continue

        dist = commit_distance(base, ref)
        candidates.append(BranchCandidate(name=ref, merge_base=base, distance=dist))

    if not candidates:
        return None

    # The parent branch is the one whose tip is *closest* (fewest commits)
    # ahead of the merge-base with the current branch.
    # Ties are broken by preferring branches whose merge-base commit is the
    # most recent (i.e. the one that appears latest in the current branch's
    # history).
    current_commits = run_lines(["git", "log", "--pretty=format:%H", current_branch])
    commit_order: dict[str, int] = {c: i for i, c in enumerate(current_commits)}

    def sort_key(c: BranchCandidate) -> tuple[int, int]:
        recency = commit_order.get(c.merge_base, sys.maxsize)
        return (c.distance, recency)

    candidates.sort(key=sort_key)
    return candidates[:3]


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find the remote branch that most likely originated the current branch.",
    )
    parser.add_argument(
        "--remote",
        default="origin",
        help="Name of the git remote to inspect (default: origin).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed information about every candidate branch.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Make sure we are inside a git repository
    run(["git", "rev-parse", "--git-dir"])

    # Fetch remote refs so we have up-to-date information
    print(f"[info] Fetching '{args.remote}'...", file=sys.stderr)
    run(["git", "fetch", args.remote, "--prune", "--quiet"])

    current = get_current_branch()
    results = find_parent_branch(current, remote=args.remote, verbose=args.verbose)

    if not results:
        print(
            f"[warn] Could not find any remote branch in '{args.remote}' "
            f"with a common commit with '{current}'.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.verbose:
        print()
        print("─" * 50)
        print(f"Top {len(results)} parent branch(es) found:\n")
        for i, candidate in enumerate(results, start=1):
            print(f"  #{i} {candidate.name}")
            print(f"     Merge base : {candidate.merge_base}")
            print(
                f"     Distance   : {candidate.distance} commit(s) ahead of merge-base"
            )
            print()
        print(f"Most likely parent: {results[0].name}")
    else:
        for candidate in results:
            print(candidate.name)


if __name__ == "__main__":
    main()
