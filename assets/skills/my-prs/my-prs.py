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

    owner, repo_name = repo.split("/")
    unresolved_raw = run(
        "gh api graphql -f query='query($owner:String!,$repo:String!,$pr:Int!){"
        "repository(owner:$owner,name:$repo){pullRequest(number:$pr){"
        "reviewThreads(first:100){nodes{isResolved}}}}}' "
        f"-f owner={owner} -f repo={repo_name} -F pr={num} "
        "--jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved==false)] | length'"
    )
    unresolved_comments = int(unresolved_raw) if unresolved_raw.isdigit() else 0

    reviewers_info = []
    approvers = []
    pending_squads = []
    pending_people = []
    for rev in info.get("reviews", []):
        u = rev.get("author", {}) or {}
        login = u.get("login", "")
        name = u.get("name") or login
        if login:
            reviewers_info.append(
                {"login": login, "name": name, "state": rev.get("state")}
            )

    latest_state = {}
    for r in reviewers_info:
        if r["state"] in ("APPROVED", "CHANGES_REQUESTED"):
            latest_state[r["login"]] = r["state"]

    requesters = []
    for login, state in latest_state.items():
        if state == "APPROVED":
            approvers.append(login)
        elif state == "CHANGES_REQUESTED":
            requesters.append(login)

    for req in info.get("reviewRequests", []):
        if req.get("__typename") == "Team" or req.get("slug"):
            slug = req.get("slug") or req.get("name")
            if slug and slug not in pending_squads:
                pending_squads.append(slug)
        else:
            login = req.get("login") or req.get("name")
            if login and login not in pending_people:
                pending_people.append(login)

    decision = info.get("reviewDecision", "")
    mergeable = info.get("mergeable", "UNKNOWN")
    merge_state = info.get("mergeStateStatus", "UNKNOWN")
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
            "approvers": approvers,
            "requesters": requesters,
            "pending_squads": pending_squads,
            "pending_people": pending_people,
            "mergeable": mergeable,
            "merge_state": merge_state,
            "ci": ci,
            "unresolved_comments": unresolved_comments,
        }
    )


def is_ready(r):
    return (
        not r["draft"]
        and r["decision"] == "APPROVED"
        and r["mergeable"] in ("MERGEABLE", "UNKNOWN")
        and not r["pending_squads"]
        and not r["pending_people"]
        and r["ci"] in ("PASS", "NONE")
        and r["merge_state"] != "DIRTY"
        and r["unresolved_comments"] == 0
    )


ready_prs = [r for r in results if is_ready(r)]
attention_prs = [r for r in results if not is_ready(r)]

total = len(results)
repos = len(set(r["repo"] for r in results))


def short_repo(repo):
    return repo.split("/")[-1]


def approvers_line(r):
    n = len(r["approvers"])
    verb = "aprovaram" if n != 1 else "aprovou"
    who = f": {', '.join(r['approvers'])}" if n else ""
    return f"┗━ ✅ {n} já {verb}{who}"


def status_lines(r):
    """Only what matters — link always, then just actionable/negative lines."""
    lines = [f"┗━ 🔗 {r['url']}"]

    if r["draft"]:
        lines.append("┗━ 🚧 rascunho (draft)")

    lines.append(approvers_line(r))

    has_pending = bool(r["pending_squads"] or r["pending_people"])

    if r["decision"] == "CHANGES_REQUESTED":
        lines.append(f"┗━ 🔄 mudanças solicitadas: {', '.join(r['requesters'])}")
    elif r["decision"] != "APPROVED" and not has_pending:
        lines.append("┗━ 👀 review pendente")

    if r["mergeable"] == "CONFLICTING" or r["merge_state"] == "DIRTY":
        lines.append("┗━ ☢️ tem conflitos")
    elif r["merge_state"] == "BEHIND":
        lines.append("┗━ ⬇️ atrás da base")

    if r["ci"] == "FAIL":
        lines.append("┗━ 💥 CI falhando")
    elif r["ci"] == "PENDING":
        lines.append("┗━ ⏳ CI rodando")

    lines.append(comments_line(r))

    if r["pending_people"]:
        lines.append("┗━ ⛔ reviewers pendentes:")
        lines += [f"   ┗━ {p}" for p in r["pending_people"]]

    if r["pending_squads"]:
        lines.append("┗━ ⛔ squads pendentes:")
        lines += [f"   ┗━ {s}" for s in r["pending_squads"]]

    return lines


def comments_line(r):
    n = r["unresolved_comments"]
    comment_word = "comentário" if n == 1 else "comentários"
    suffix = "s" if n != 1 else ""
    return f"┗━ 💬 {n} {comment_word} não resolvido{suffix}"


def ready_lines(r):
    """Clean PRs — link + comment count."""
    return [f"┗━ 🔗 {r['url']}", comments_line(r)]


print(f"📋 Meus PRs abertos — {total} no total em {repos} repo(s)")
print(f"   ✅ {len(ready_prs)} prontos pra merge · ⚠️ {len(attention_prs)} precisam de atenção")
print()


def group_by_repo(prs):
    groups = {}
    for r in prs:
        groups.setdefault(r["repo"], []).append(r)
    return groups


def print_group(repo, prs, line_fn):
    count = len(prs)
    print(f"📦 {short_repo(repo)} · {count} PR{'s' if count != 1 else ''}")
    print()
    for r in prs:
        print(f"[#{r['num']}] {r['title']}")
        for line in line_fn(r):
            print(line)
        print()


if ready_prs:
    print("━━━ ✅ PRONTOS PRA MERGE ━━━")
    print()
    for repo, prs in group_by_repo(ready_prs).items():
        print_group(repo, prs, ready_lines)

if attention_prs:
    print("━━━ ⚠️ PRECISAM DE ATENÇÃO ━━━")
    print()
    for repo, prs in group_by_repo(attention_prs).items():
        print_group(repo, prs, status_lines)

if not results:
    print("Nenhum PR aberto encontrado.")
