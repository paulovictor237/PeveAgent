---
name: backend-review
description: "Code review for backend Pull Requests (PHP/Laravel). Use with a PR ID or URL. Ex: /backend-review 4359 or /backend-review 4359 /path/to/repo"
user-invocable: true
allowed-tools: Read, Bash, Grep, Glob
argument-hint: "[pr-id] | [pr-url]"
---

# Backend code review

## Usage

```
/backend-review <PR_ID | PR_URL> [DIRECTORY]
```

Without `DIRECTORY`, ask which repository to use before running any `gh` command.

## 1. Resolve the repository

- Directory given as an argument → use it directly.
- No directory → `AskUserQuestion`:
  - "px-torre-core" — `~/Code/PX-Center/Torre/`
  - "Current directory" — the working directory
  - (the user can also type a custom path via "Other")

Once the directory is resolved, run this once, before any other command:

```bash
cd <DIRECTORY> && unset GITHUB_TOKEN
```

Every `gh` command from here on runs in that same shell — no repeating `cd` or `GITHUB_TOKEN=`.

## 2. Collect the PR

```bash
gh pr view <PR_ID> --json title,body,author,baseRefName,headRefName,files,additions,deletions,changedFiles,reviews,comments,state
gh pr diff <PR_ID>
gh pr checks <PR_ID>
gh api repos/{owner}/{repo}/pulls/<PR_ID>/comments   # owner/repo from the directory's remote
```

Read the full diff before moving on — feedback only covers what was actually read.

## 3. Review against the checklist

#### PHP code quality

- **Naming**: camelCase for variables/methods, PascalCase for classes.
- **Type hints**: parameters and return types declared where possible.
- **Formatting**: follows Pint (Laravel preset: braces on the same line, short array syntax `[]`, ordered imports, no trailing comma on multiline).
- **Imports**: organized, no unused imports.
- **Comments**: code is self-explanatory; no obvious or stale comments.
- **`Carbon::now()`**: new or edited lines must use `Carbon::now()`, not the `now()` helper. Only applies to lines added/modified in the PR — untouched legacy code doesn't count.

#### Laravel patterns

- **Eloquent**: correct relationships, no N+1.
- **Validation**: Form Requests or inline validation, as fits the case.
- **Services**: business logic in Services, not Controllers.
- **Repositories**: data access through a Repository when the module already follows that pattern.
- **Jobs/Events**: async operations where it makes sense.
- **Migrations**: reversible (`down` method), correct column types.

#### Security

- **SQL injection**: query builder/Eloquent, never a raw query without binding.
- **Mass assignment**: `$fillable`/`$guarded` defined.
- **Authorization**: Policies/Gates applied where needed.
- **Sensitive data**: no hardcoded credentials, tokens, or secrets.
- **Input validation**: all user input validated.

#### Performance

- **Queries**: no N+1, eager loading (`with`/`load`) applied.
- **Cache**: used where data is accessed frequently.
- **Indexes**: migrations add an index for search/filter columns.
- **Pagination**: large listings paginated.

#### Tests

- Coverage for new methods/features.
- Edge cases covered.
- Factories/seeders when the test needs a fixture.

#### Project architecture

- File in the right directory (`Services/`, `Models/`, etc.).
- Single responsibility per class/method.
- DTOs for complex data transfer.
- Enums for constant values (PHP 8.1+).

#### Static analysis

- PHPStan level 0 (with baseline) on `app/` — level 0 doesn't catch much; the only bar is not regressing the baseline.

## 4. Assess impact

Affected modules/features, breaking changes, migration rollback safety, dependencies between PRs.

## 5. Report

> **Mandatory rule:** every suggestion, critical issue, or caveat opens with `### path/to/file.php:line — title`, naming the file (and line, when possible) — including points outside the diff (a related model, an inherited trait), citing the file they come from. No review point without a file.

When a security or bug point competes for attention with a style point, give the security/bug point priority in the review.

Structure the review like this:

````markdown
## 📋 PR Summary

**Title**: [PR title]
**Author**: [author]
**Branch**: [head] → [base]
**Files changed**: [number]
**Additions/Deletions**: +[additions] / -[deletions]

## ✅ Strengths

- [What's well implemented]

## ⚠️ Suggestions

### [file:line] - [suggestion title]

**Issue**: [description]

**Suggestion**:

```php
// suggested code
```

**Reason**: [justification]

## 🔴 Critical Issues (if any)

### [file:line] - [issue title]

**Issue**: [issue description]
**Impact**: [the risk]
**Required fix**: [what needs to be fixed]

## 📊 Checklist

- [x] Code quality
- [x] Laravel patterns
- [ ] Tests (pending)
- [x] Security

## 🎯 Verdict

- [ ] ✅ **Approved** - Ready to merge
- [ ] 🔄 **Approved with caveats** - Can merge, but consider the suggestions
- [ ] ⏳ **Changes requested** - Needs adjustments before merge
- [ ] 🚫 **Blocked** - Critical issues preventing merge
````

## Reference: extra gh commands

```bash
gh pr diff <PR_ID> -- <path/to/file>                      # diff of one file
gh pr view <PR_ID> --json files -q '.files[].path'         # list changed files
gh pr view <PR_ID> --json reviews                          # existing reviews
gh pr comment <PR_ID> --body "Review comment"
gh pr review <PR_ID> --approve --body "LGTM! ✅"
gh pr review <PR_ID> --request-changes --body "Please check..."
```
