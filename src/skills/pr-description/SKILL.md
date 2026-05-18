---
name: pr-description
description: 'Generates a Pull Request description by filling the project template with clear and non-technical language, automatically detects the base branch, and opens the PR. Use this skill whenever the user asks to: describe a PR, write the PR description, generate the PR body, fill the PR template, "describe what changed in the PR", "write the PR", "prepare the pull request description", "fill PR description", "write PR body", or any variation of writing/preparing/assembling a pull request description. Also trigger when the user says "let''s describe the PR", "prepare the PR", "describe the PR for me", "I need the PR description", "I need the PR body", "open the PR", "create the PR".'
---

# Skill: Pull Request Description and Opening

You will generate the full text of a Pull Request description, filling the project template with accessible language — focusing on *what* and *why*, not on technical implementation details — and then **open the PR** pointing to the correct base branch.

## Step 1 — Load the template

Read the file `/.github/pull_request_template.md` at the **root of the current project** (working directory).

- If the file exists: use it as the base structure, keeping all fields and sections.
- If it doesn't exist: use the default structure below.

```markdown
## 🔖 Scope

## 🚩 Known issues

## 📁 Evidence

## Test Script: Happy Path

### Acceptance Criteria

## 💥 Impact Points
```

## Step 2 — Detect the base branch

The base branch detection script is in the **skill's own folder**. Execute it like this:

```bash
python ~/.claude/skills/pr-description/scripts/find_parent_branch.py
```

The script returns up to 3 candidates ordered by relevance (shortest commit distance). Present the candidates to the user in the format:

```
Found the following source branches with a common commit:

  #1 origin/main (recommended)
  #2 origin/feature/another-branch
  #3 origin/staging

Which branch should be the PR destination? [Enter to use #1]
```

Wait for the user's response. If the user presses Enter or confirms without specifying, use **#1 (first candidate)** as the base branch.

> **If the script doesn't exist**: use `git log --oneline -10` + `git branch -r` to infer the base branch, or ask the user.

## Step 3 — Collect context

With the base branch defined (`BASE_BRANCH`), collect information to fill the template:

1. **Changes diff** — `git diff origin/BASE_BRANCH...HEAD` to see what was changed.
2. **Branch commits** — `git log origin/BASE_BRANCH...HEAD --oneline` to understand the narrative.
3. **Modified files** — `git diff origin/BASE_BRANCH...HEAD --name-only` for a quick scope overview.
4. **Jira Ticket** — if the branch or commits have a ticket ID (e.g., `APX-1234`), **before searching**, ask the user:

```
I found ticket APX-1234 on the branch. Do you want me to search for more information in Jira to enrich the description? [Y/n]
```

If confirmed, execute: `acli jira issue view APX-1234`

Do not ask the user for information that you can discover yourself with these tools.
External sources (Jira, etc.) should be consulted **only with explicit user confirmation**.

## Step 4 — Fill the template

Fill each section of the template following these guidelines:

### 🔖 Scope
Explain **what was done and why** in 2-5 sentences. Focus on the benefit or problem solved, not on the modified files. Examples:

- ❌ "Added `calculateDiscount()` method in `DiscountService` and updated the `Contract` model"
- ✅ "Fixes the discount calculation that was generating negative values for contracts with advance payment"

If there is a linked Jira ticket, mention it at the end: *(APX-1234)*

### 🚩 Known issues
List known limitations or technical decisions left for later. If none, write "N/A".

### 📁 Evidence

If the user asks to add evidence/images, structure them using **Markdown tables with up to 4 columns**. Use the format below according to the pattern:

#### **Pattern 1: Flow (Screen 1–N)**
For flows with multiple screens (e.g., 4-step authentication). Use 4 columns and multiple rows if necessary:

```markdown
## Screens

**Goal:** 4-step authentication flow

| Screen 1: Login | Screen 2: 2FA | Screen 3: Success | Screen 4: Error |
|-----------|-----------|-----------|-----------|
| <img src="" width="250"/> | <img src="" width="250"/> | <img src="" width="250"/> | <img src="" width="250"/> |

**Notes (optional):**
- Smooth transition between screens
- Real-time validation on 2FA
```

#### **Pattern 2: Before vs After**
For comparisons (e.g., UI refactor, visual bug fix). Use 2 columns:

```markdown
## Screens

**Goal:** Improvement in contract rendering

| Before | After |
|-----------|-----------|
| <img src="" width="250"/> | <img src="" width="250"/> |

**Notes (optional):**
- Fixed button alignment
- Improved date readability
```

#### **Pattern 3: States (Error / Success / Special Cases)**
For different states of a component/screen. Use up to 3 columns:

```markdown
## Screens

**Goal:** Form validation states

| Error | Warning | Success |
|-----------|-----------|-----------|
| <img src="" width="250"/> | <img src="" width="250"/> | <img src="" width="250"/> |

**Notes (optional):**
- Error messages in red
- Clear visual feedback for each state
```

#### **Rules when adding evidence:**
- Maximum 4 columns per table (if exceeded, create a new table)
- Each column names the image (e.g., "Screen 1: Login", "Before", "Error")
- URLs in `src=""` must be filled by the user after generating the PR (e.g., upload links or GitHub)
- `width="250"` is default; adjust if necessary
- "Notes" section is optional; use only if there are important points
- If no real images are available, leave `src=""` empty as placeholders

If the user **does not explicitly ask** for images, leave a simple placeholder:
```
<!-- Add screenshots/logs/videos that prove the functionality -->
```

### Test Script: Happy Path
Describe how someone without code knowledge can verify that the change works. Use simple and concrete steps:

- "Access screen X"
- "Perform action Y"
- "Verify that Z happens"

### Acceptance Criteria
List 2-4 observable criteria (expected behavior), derived from the test steps.

### 💥 Impact Points
Identify parts of the system that may be affected. Prefer business language:

- ❌ "`Contract` Model, `PaymentService` Service, `ProcessPaymentJob` Job"
- ✅ "Freight payment calculation", "Contracts screen in the driver app"

### Checkbox fields (if they exist in the template)
Leave all checkboxes unchecked — it is the team's responsibility to fill them out.

## Step 5 — Confirm and open the PR

After generating the description, show the text to the user and ask:

```
Description generated. Do you want to open the PR now pointing to `BASE_BRANCH`? [Y/n]
```

If the user confirms (Enter or "Y"), open the PR with:

```bash
gh pr create \
  --draft \
  --base BASE_BRANCH \
  --title "SUGGESTED_TITLE" \
  --body "$(cat <<'EOF'
[GENERATED_DESCRIPTION]
EOF
)"
```

The title should be automatically generated from the branch name and/or Jira ticket, following the pattern `[APX-1234] Short description of what was done`. If there is no ticket, use a concise description of what was done.

Return the created PR URL to the user.

## Language

- Write in **Portuguese** (unless the template is in another language)
- Short and direct sentences
- No unnecessary technical jargon — imagine the reader is a QA or PM, not the dev who wrote the code
- Avoid excessive passive voice
