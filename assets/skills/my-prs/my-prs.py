#!/usr/bin/env python3
import subprocess, json

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip()

gh_user = run("gh api user --jq '.login'")
prs_raw = run(f"gh search prs --author {gh_user} --state open --owner px-center --limit 50 --json number,title,repository,url,isDraft")
prs = json.loads(prs_raw)

results = []
for pr in prs:
    num = pr['number']
    repo = pr['repository']['nameWithOwner']
    info_raw = run(f"gh pr view {num} --repo {repo} --json reviewDecision,reviews,mergeable,statusCheckRollup")
    info = json.loads(info_raw) if info_raw else {}

    approvals = sum(1 for r in info.get('reviews', []) if r.get('state') == 'APPROVED')
    decision = info.get('reviewDecision', '')
    mergeable = info.get('mergeable', 'UNKNOWN')
    checks = info.get('statusCheckRollup') or []

    if not checks:
        ci = 'NONE'
    elif any(c.get('conclusion') in ('FAILURE', 'ERROR') for c in checks):
        ci = 'FAIL'
    elif any(c.get('status') in ('IN_PROGRESS', 'QUEUED') for c in checks):
        ci = 'PENDING'
    else:
        ci = 'PASS'

    results.append({
        'repo': repo, 'num': num, 'title': pr['title'], 'url': pr['url'],
        'draft': pr['isDraft'], 'decision': decision, 'approvals': approvals,
        'mergeable': mergeable, 'ci': ci,
    })

total = len(results)
repos = len(set(r['repo'] for r in results))
ready = sum(1 for r in results if r['decision'] == 'APPROVED')
needs = sum(1 for r in results if r['decision'] == 'REVIEW_REQUIRED')

print(f"📋 {total} open PRs across {repos} repos — {ready} ready to merge, {needs} need review\n")

grouped = {}
for r in results:
    grouped.setdefault(r['repo'], []).append(r)

for repo, prs in grouped.items():
    print(repo)
    for r in prs:
        print(f"• [#{r['num']}] {r['title']}")
        print(f"  🔗 {r['url']}")
        if r['draft']:
            print("  🚧 Draft")
        if r['decision'] == 'APPROVED':
            print("  ✅ Ready to merge")
        elif r['decision'] == 'CHANGES_REQUESTED':
            print("  🔄 Changes requested")
        else:
            print(f"  👀 Needs review ({r['approvals']} approvals)")
        print("  ✅ No conflicts" if r['mergeable'] == 'MERGEABLE' else
              "  ⚠️ Has conflicts" if r['mergeable'] == 'CONFLICTING' else
              "  ❓ Conflict state unknown")
        print("  ✅ CI passing" if r['ci'] == 'PASS' else
              "  ❌ CI failing" if r['ci'] == 'FAIL' else
              "  ⏳ CI pending" if r['ci'] == 'PENDING' else
              "  ➖ No CI")
        print()
