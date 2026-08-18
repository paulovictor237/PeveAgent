---
name: resolving-codeowners-coverage
description: Use when CI/PR fails with "files have no CODEOWNERS entry" or you must add owners for uncovered changed paths — decides per file between a squad owner, a folder/glob rule, or a # [shared-layer] marker.
---

# Resolving CODEOWNERS Coverage Gaps

## Overview

CI reports changed files with no `.github/CODEOWNERS` entry. Each gap gets ONE of three resolutions:

1. **Squad owner** — file belongs to a team's domain.
2. **Folder / glob rule** — many cohesive files in same module → one rule beats N per-file lines.
3. **`# [shared-layer]` marker** — aggregator file many squads append to; intentionally unowned.

Core principle: **owner = domain, not git author.** Author count only hints at "shared vs owned".

## Workflow

1. **Collect the gap list** — paste the paths from the CI "no CODEOWNERS entry" block.
2. **Run the analyzer** (replaces per-file git fan-out):
   ```bash
   scripts/analyze.sh < files.txt          # or: scripts/analyze.sh path1 path2 ...
   # flags: -b BASE (default main)  -c CODEOWNERS (default .github/CODEOWNERS)
   ```
   Output per file: NEW/OLD, heuristic cluster, dominant author on base branch.
3. **Cluster the files** by domain/module (Falcon, Score, Discounts, generic resources…). Heuristic clusters are a starting point — adjust.
4. **Confirm owner per cluster with AskUserQuestion.** Never guess squad names. One question per cluster; offer the likely squad, a folder-vs-shared option, and "Leave shared-layer".
5. **Apply edits** following the rules below.
6. Re-run the project's coverage check to confirm green.

## Resolution decision

| Signal | Resolution |
|---|---|
| Cohesive module, ≥2 files, has a real dir or name prefix | folder/glob rule for whole module |
| Generic aggregator (high commit count, many authors, "everyone appends a field") | `# [shared-layer]` marker |
| Dir is mixed-owner (other squad owns siblings) | per-file or name-glob, NOT whole-dir |
| Single domain file | per-file squad line |

## CODEOWNERS rules that bite

- **Last matching pattern wins.** A broad glob placed *after* a specific line overrides it. Order sections so the intended owner's pattern is last for any contested path.
- **Avoid broad `**/*Foo*` globs** that collide across clusters (e.g. `**/*ScoreStatus*` also catches `Falcon...ScoreStatusTest`). Scope to `app/**`, a dir, or list files explicitly.
- **`# [shared-layer]` lines are comments** — they don't assign an owner, they just document intent so the coverage check passes. Put them in the shared-layer block at the top.
- Prefer trailing-slash dir rules (`app/PHP8/Services/Falcon/`) and prefix globs (`app/Http/Resources/Falcon*`) over enumerating files.

## Common mistakes

- Assigning by git author instead of domain.
- Whole-dir rule on a mixed dir (steals files from another squad).
- Broad glob that wins over an existing specific owner via last-match.
- Guessing squad names instead of asking.
