#!/usr/bin/env python3
import json
import subprocess


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip()


gh_user = run("gh api user --jq '.login'")
prs_raw = run(
    f"gh search prs --author {gh_user} --state open --owner px-center --limit 50 --json number,title,repository,url,isDraft"
)
prs = json.loads(prs_raw)

results = []
for pr in prs:
    num = pr["number"]
    repo = pr["repository"]["nameWithOwner"]
    info_raw = run(
        f"gh pr view {num} --repo {repo} --json reviewDecision,reviews,mergeable,mergeStateStatus,reviewRequests,statusCheckRollup"
    )
    info = json.loads(info_raw) if info_raw else {}

    approvals = sum(1 for r in info.get("reviews", []) if r.get("state") == "APPROVED")
    decision = info.get("reviewDecision", "")
    mergeable = info.get("mergeable", "UNKNOWN")
    merge_state = info.get("mergeStateStatus", "UNKNOWN")
    pending_reviewers = [
        (req.get("name") or req.get("slug") or req.get("login"))
        for req in info.get("reviewRequests", [])
    ]
    checks = info.get("statusCheckRollup") or []

    if not checks:
        ci = "NONE"
    elif any(c.get("conclusion") in ("FAILURE", "ERROR") for c in checks):
        ci = "FAIL"
    elif any(c.get("status") in ("IN_PROGRESS", "QUEUED") for c in checks):
        ci = "PENDING"
    else:
        ci = "PASS"

    results.append(
        {
            "repo": repo,
            "num": num,
            "title": pr["title"],
            "url": pr["url"],
            "draft": pr["isDraft"],
            "decision": decision,
            "approvals": approvals,
            "mergeable": mergeable,
            "merge_state": merge_state,
            "pending_reviewers": pending_reviewers,
            "ci": ci,
        }
    )


def is_ready(r):
    return (
        not r["draft"]
        and r["decision"] == "APPROVED"
        and r["mergeable"] in ("MERGEABLE", "UNKNOWN")
        and not r["pending_reviewers"]
        and r["ci"] in ("PASS", "NONE")
        and r["merge_state"] != "DIRTY"
    )


ready_prs = [r for r in results if is_ready(r)]
attention_prs = [r for r in results if not is_ready(r)]

total = len(results)
repos = len(set(r["repo"] for r in results))


def short_repo(repo):
    return repo.split("/")[-1]


def attention_lines(r):
    lines = []
    if r["draft"]:
        lines.append("🚧 draft")
    if r["decision"] == "CHANGES_REQUESTED":
        lines.append("🔄 changes requested")
    elif r["decision"] != "APPROVED":
        lines.append(f"👀 needs review ({r['approvals']} approvals)")
    if r["pending_reviewers"]:
        lines.append(f"⛔ pending required review: {', '.join(r['pending_reviewers'])}")
    if r["merge_state"] == "BEHIND":
        lines.append("⬇️ behind base branch")
    if r["mergeable"] == "CONFLICTING" or r["merge_state"] == "DIRTY":
        lines.append("☢️ has conflicts")
    if r["ci"] == "FAIL":
        lines.append("💥 CI failing")
    elif r["ci"] == "PENDING":
        lines.append("⏳ CI pending")
    return lines


print("📋 MY OPEN PRs — {} total".format(total))
print(f"✓ {len(ready_prs)} ready · ⚠ {len(attention_prs)} needs attention")
print("━" * 48)
print()


def group_by_repo(prs):
    groups = {}
    for r in prs:
        groups.setdefault(r["repo"], []).append(r)
    return groups


def print_group(repo, prs, get_lines=None):
    count = len(prs)
    print(f"▸ {short_repo(repo)} ({count})")
    for i, r in enumerate(prs):
        is_last = i == len(prs) - 1
        connector = "┗━" if is_last else "┣━"
        indent = "    " if is_last else "┃   "
        print(f"  {connector} {r['title']}")
        print(f"  {indent}→ {r['url']}")
        if get_lines:
            lines = get_lines(r)
            for j, line in enumerate(lines):
                sub = "┗━" if j == len(lines) - 1 else "┣━"
                print(f"  {indent}{sub} {line}")
    print()


if ready_prs:
    print("━━━ ✅ READY TO MERGE " + "━" * 28)
    print()
    for repo, prs in group_by_repo(ready_prs).items():
        print_group(repo, prs)

if attention_prs:
    print("━━━ 🔥 NEEDS MY ATTENTION " + "━" * 24)
    print()
    for repo, prs in group_by_repo(attention_prs).items():
        print_group(repo, prs, attention_lines)
