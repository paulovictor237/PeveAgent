# subscrible-job MCP Rewrite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Python/Playwright subprocess with Claude driving browser directly via `@playwright/mcp`, deleting all scripts and moving logic into SKILL.md.

**Architecture:** Claude reads `profile.json`, navigates to job URL via playwright MCP tools, scans DOM snapshot for form fields, applies inline mapping rules to fill fields, pauses for cover letter and manual fields, then diffs final snapshot against baseline to learn new values into `profile.json`.

**Tech Stack:** `@playwright/mcp` (Microsoft), Claude Code skill system, `profile.json` as data store.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `.claude/.mcp.json` | Add playwright MCP server (global) |
| Modify | `.mcp.json` (PeveAgent) | Add playwright MCP server (project) |
| Modify | `~/.config/opencode/opencode.json` | Add playwright MCP server (opencode) |
| Rewrite | `.agents/skills/subscrible-job/SKILL.md` | New flow + mapping rules |
| Delete | `.agents/skills/subscrible-job/scripts/run.py` | Old entrypoint |
| Delete | `.agents/skills/subscrible-job/scripts/lib/browser.py` | Old browser helpers |
| Delete | `.agents/skills/subscrible-job/scripts/lib/mapping.py` | Old mapping rules |
| Delete | `.agents/skills/subscrible-job/scripts/lib/profile.py` | Old profile helpers |
| Delete | `.agents/skills/subscrible-job/scripts/requirements.txt` | Old deps |

---

### Task 1: Add @playwright/mcp to all MCP configs

**Files:**
- Modify: `/Users/peve/.claude/.mcp.json`
- Modify: `/Users/peve/workspace/PeveAgent/.mcp.json`
- Modify: `/Users/peve/.config/opencode/opencode.json`

- [ ] **Step 1: Add to global Claude MCP config**

Edit `/Users/peve/.claude/.mcp.json` — add inside `mcpServers`:

```json
"playwright": {
  "command": "npx",
  "args": ["@playwright/mcp@latest"]
}
```

Full file after edit:
```json
{
  "mcpServers": {
    "context7": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    },
    "figma-context": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "figma-developer-mcp", "--figma-api-key=_key_", "--stdio"]
    },
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  },
  "jira": {
    "type": "sse",
    "url": "https://mcp.atlassian.com/v1/sse",
    "enabled": true
  },
  "github": {
    "type": "http",
    "url": "https://api.githubcopilot.com/mcp",
    "headers": { "Authorization": "Bearer ${GITHUB_TOKEN}" },
    "enabled": true
  }
}
```

- [ ] **Step 2: Add to project MCP config**

Edit `/Users/peve/workspace/PeveAgent/.mcp.json` — add inside `mcpServers`:

```json
"playwright": {
  "command": "npx",
  "args": ["@playwright/mcp@latest"]
}
```

Full file after edit:
```json
{
  "mcpServers": {
    "ticktick": {
      "type": "http",
      "url": "https://mcp.ticktick.com/"
    },
    "notion": {
      "type": "http",
      "url": "https://mcp.notion.com/mcp"
    },
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"]
    },
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    },
    "context7": {
      "type": "http",
      "url": "https://mcp.context7.com/mcp"
    },
    "jira": {
      "type": "sse",
      "url": "https://mcp.atlassian.com/v1/sse",
      "enabled": true
    },
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/"
    }
  }
}
```

- [ ] **Step 3: Add to opencode config**

Edit `/Users/peve/.config/opencode/opencode.json` — add inside `mcp`:

```json
"playwright": {
  "type": "local",
  "command": ["npx", "@playwright/mcp@latest"]
}
```

Full file after edit:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "context7": {
      "type": "remote",
      "url": "https://mcp.context7.com/mcp"
    },
    "figma-context": {
      "type": "local",
      "command": [
        "npx",
        "-y",
        "figma-developer-mcp",
        "--figma-api-key=YOUR_FIGMA_API_KEY",
        "--stdio"
      ]
    },
    "playwright": {
      "type": "local",
      "command": ["npx", "@playwright/mcp@latest"]
    }
  },
  "plugin": [
    "superpowers@git+https://github.com/obra/superpowers.git"
  ],
  "permission": {
    "bash": {
      "*": "allow",
      "git commit *": "ask",
      "git push *": "ask"
    }
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add /Users/peve/.claude/.mcp.json /Users/peve/workspace/PeveAgent/.mcp.json /Users/peve/.config/opencode/opencode.json
git commit -m "chore: add @playwright/mcp to all MCP configs"
```

---

### Task 2: Delete Python scripts

**Files:**
- Delete: `.agents/skills/subscrible-job/scripts/run.py`
- Delete: `.agents/skills/subscrible-job/scripts/lib/browser.py`
- Delete: `.agents/skills/subscrible-job/scripts/lib/mapping.py`
- Delete: `.agents/skills/subscrible-job/scripts/lib/profile.py`
- Delete: `.agents/skills/subscrible-job/scripts/requirements.txt`

- [ ] **Step 1: Remove scripts directory**

```bash
rm -rf /Users/peve/workspace/PeveAgent/.agents/skills/subscrible-job/scripts
```

- [ ] **Step 2: Verify deleted**

```bash
ls /Users/peve/workspace/PeveAgent/.agents/skills/subscrible-job/
```

Expected output:
```
SKILL.md
assets/
```

- [ ] **Step 3: Commit**

```bash
cd /Users/peve/workspace/PeveAgent
git add -A
git commit -m "chore(subscrible-job): delete python scripts"
```

---

### Task 3: Rewrite SKILL.md

**Files:**
- Rewrite: `/Users/peve/workspace/PeveAgent/.agents/skills/subscrible-job/SKILL.md`

- [ ] **Step 1: Write new SKILL.md**

Replace entire file with:

```markdown
# subscrible-job

Fill job application forms using playwright MCP tools. Claude drives browser directly — no scripts.

## Hard Rules

1. **NEVER click submit / enviar / finalizar / candidatar / apply**
2. **NEVER invent data** — use only what's in `profile.json`
3. **ALWAYS pause** on cover letter fields and ask user for text
4. **ALWAYS upload PDF** when file input found
5. **No retry** — mark `✗` and move on if fill fails

## Assets

```
SKILL_DIR/assets/profile.json     ← candidate data
SKILL_DIR/assets/Profile-pt.pdf   ← CV Portuguese
SKILL_DIR/assets/Profile-en.pdf   ← CV English
```

`SKILL_DIR` = the directory containing this SKILL.md file.

## How to invoke

User: `/subscrible-job <URL>`

## Execution Flow

### 1. Load profile

Read `SKILL_DIR/assets/profile.json`. Extract all candidate data.

### 2. Navigate

```
playwright_navigate(url=URL)
```

### 3. Baseline snapshot

```
baseline = playwright_snapshot()
```

Parse all form fields from the accessibility tree: inputs, selects, textareas.
For each field note: role, label, placeholder, aria-label, name/id, type, options (if select).

### 4. Fill fields

For each field, apply mapping rules below (most-specific first, first match wins).

Normalize text for matching: lowercase + remove accents + collapse whitespace.

If resolved value is found:
- `input[type=text/email/tel/url/number]` or `textarea` → `playwright_fill`
- `select` → `playwright_select_option` (match by normalized label)
- `input[type=checkbox]` or `input[type=radio]` → `playwright_click` only if value is truthy (`sim/yes/true/1`)
- `input[type=file]` → `playwright_upload_file` with PDF path (see File Upload rule)
- custom dropdown (role=combobox, listbox) → `playwright_click` to open, then `playwright_click` on matching option

If field matches cover_letter rule → **STOP, ask user** (see Cover Letter rule).

If no rule matches → mark `○ unmapped`.

If fill throws → mark `✗ failed`, continue.

### 5. Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ N campos detectados

✓ Preenchido (N):
  • Nome completo → Paulo Victor Duarte

⚠ Cover letter — preencha manualmente:
  • Carta de Apresentação

○ Não mapeados (N):
  • Campo XYZ

✗ Falhas (N):
  • Campo ABC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Preencha o restante. Quando terminar, diga "feito".
```

### 6. Wait for user

After filling all auto-fillable fields, pause. Tell user which fields need attention. Wait for user to say "feito" / "done" / "pronto".

### 7. Learn new values

```
final = playwright_snapshot()
```

Compare `final` vs `baseline`. Fields that:
- Were empty in baseline AND have a value in final AND were NOT filled by Claude
→ user manually filled them

Add each to `profile.json → extra_fields` with the field label as key. Save file.

---

## Mapping Rules

Ordered most-specific → most-generic. First match wins.
Match against: label + placeholder + aria-label + name + id (all concatenated, normalized).

### Identity
| Keywords | Value |
|---|---|
| `full name` / `nome completo` | `profile.name` |
| `first name` / `primeiro nome` / `given name` | first word of `profile.name` |
| `last name` / `sobrenome` / `surname` / `ultimo nome` | remaining words of `profile.name` |

### Contact
| Keywords | Value |
|---|---|
| `email` / `e-mail` / `e mail` / `correio` | `profile.email` |
| `telefone` / `celular` / `phone` / `whatsapp` / `fone` | `profile.phone` |
| `cpf` | `profile.cpf` |
| `rg` / `documento de identidade` / `numero do rg` | `profile.rg` |

### Birth
| Keywords | Value |
|---|---|
| `data de nascimento` / `nascimento` / `birth` / `aniversario` / `birthday` / `date of birth` | `profile.birth_date` (convert to YYYY-MM-DD if field type=date) |

### Links
| Keywords | Value |
|---|---|
| `linkedin` | `profile.linkedin` |
| `github` / `portfolio` | `profile.github` |

### Address
| Keywords | Value |
|---|---|
| `cidade` / `city` / `municipio` | `profile.address.city` |
| `estado` / `state` / `uf` | `profile.address.state` or `profile.address.state_abbr` (match dropdown option) |
| `pais` / `country` / `nacao` | `profile.address.country` |
| `endereco` / `rua` / `street` / `logradouro` | `"{profile.address.street}, {profile.address.number}"` |
| `cep` / `zip` / `postal code` | `profile.extra_fields.cep` |
| `bairro` / `neighborhood` / `district` | `profile.extra_fields.bairro` |

### Education
| Keywords | Value |
|---|---|
| `universidade` / `faculdade` / `institution` / `school name` / `college` / `nome da instituicao` | `profile.education[0].institution` |
| `curso` / `field of study` / `major` / `disciplina` / `area de formacao` | `profile.education[0].field` |
| `grau` / `degree` / `nivel de ensino` / `escolaridade` / `nivel superior` | `profile.education[0].degree` (match dropdown option) |
| `status da formacao` / `situacao` / `concluiu` / `completou` | `Completo` if `education[0].end` year ≤ 2026, else `Cursando` (match dropdown) |
| `ano de conclusao` / `graduation year` / `ano formacao` | year part of `profile.education[0].end` |
| `mes de conclusao` / `graduation month` / `mes de termino` | month name from `profile.education[0].end` (e.g. `Novembro`) |
| `formacao` / `graduacao` (generic) | `"{degree} em {field} — {institution} ({year})"` |

### Experience
| Keywords | Value |
|---|---|
| `empresa atual` / `current company` / `onde trabalha` / `nome da empresa` / `employer` | `profile.experience[0].company` |
| `cargo atual` / `current role` / `posicao atual` / `current position` / `titulo atual` | `profile.current_role` |
| `experiencia` / `anos de experiencia` / `tempo de experiencia` | `"{total_duration} na {company} como {title}"` |

### Salary / Contract
| Keywords | Value |
|---|---|
| `salario` / `pretensao` / `remuneracao` / `expectativa salarial` / `salary` | `"PJ: R$ {pj.min}~{pj.max} / CLT: R$ {clt.min}~{clt.max}"` |
| `contrato` / `regime` / `tipo de contrato` / `contract type` | `profile.job_preferences.primary.contract` (match dropdown) |

### Availability
| Keywords | Value |
|---|---|
| `modalidade` / `modelo de trabalho` / `work model` | `profile.job_preferences.primary.modality` (match dropdown) |
| `modelo hibrido` / `disponibilidade hibrido` | `Sim` if modality contains `hibrido`, else `Nao` |
| `disponibilidade` / `quando pode comecar` / `start date` / `notice period` | `"{availability_days/30} mês"` |
| `viagem` / `travel` / `disponivel para viagens` | `Sim` or `Nao` from `profile.job_preferences.willing_to_travel` |
| `mudanca` / `relocate` / `relocation` | `Sim` or `Nao` from `profile.job_preferences.willing_to_relocate` |

### Diversity
| Keywords | Value |
|---|---|
| `pcd` / `deficiencia` / `disability` / `portador` | `Sim` or `Nao` from `profile.pcd` (match dropdown) |
| `genero` / `gender` / `sexo` | `profile.gender` (match dropdown) |
| `pronome` | `profile.pronoun` (match dropdown) |
| `raca` / `etnia` / `cor` / `race` / `ethnicity` | `profile.ethnicity` (match dropdown) |

### Recruitment
| Keywords | Value |
|---|---|
| `parentesco` / `parente` / `familiar` / `conhece funcionario` | `Não` |
| `como ficou sabendo` / `como soube` / `source` / `indicacao` / `canal` / `referral` | `profile.job_preferences.job_source` |

### Other
| Keywords | Value |
|---|---|
| `idioma` / `lingua` / `language` | comma-joined: `"{language} ({level}), ..."` |
| `sobre voce` / `resumo` / `summary` / `bio` / `apresentacao pessoal` | `profile.summary` |
| `habilidade` / `skill` / `competencia` / `tecnologia` | comma-joined `profile.skills` |
| `nome` (generic — must be last) | `profile.name` |

---

## Special Cases

### File Upload
Any `input[type=file]`:
- If page language appears to be English → upload `SKILL_DIR/assets/Profile-en.pdf`
- Otherwise → upload `SKILL_DIR/assets/Profile-pt.pdf`

Use `playwright_upload_file`.

### Cover Letter
Any textarea whose label/placeholder/aria matches:
`cover letter` / `carta de apresentacao` / `carta de motivacao` / `apresentacao` / `motivacao` / `por que voce quer`

→ **Do NOT fill. Report `⚠` and ask user:**
> "Campo de cover letter encontrado: '{label}'. Cole o texto que devo usar."

After user provides text → `playwright_fill`.

### Dropdown Option Matching
When selecting from a dropdown, normalize both the target value and each option (lowercase + remove accents). Pick the option whose normalized text best matches. If no match found → mark `○ unmapped`.

### Checkbox / Radio
Only interact if resolved value is truthy (`sim` / `yes` / `true` / `1`). Skip entirely otherwise.

---

## profile.json extra_fields

Structure after learning:
```json
{
  "extra_fields": {
    "cep": "89201-100",
    "bairro": "Centro"
  }
}
```

These are consulted by mapping rules for `cep` and `bairro`. Any other manually-filled field gets added here with its label as the key, available for future runs.
```

- [ ] **Step 2: Verify file saved**

```bash
wc -l /Users/peve/workspace/PeveAgent/.agents/skills/subscrible-job/SKILL.md
```

Expected: > 150 lines.

- [ ] **Step 3: Commit**

```bash
cd /Users/peve/workspace/PeveAgent
git add .agents/skills/subscrible-job/SKILL.md
git commit -m "feat(subscrible-job): rewrite skill to use playwright MCP directly"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Covered by |
|---|---|
| Add @playwright/mcp to configs | Task 1 |
| Delete Python scripts | Task 2 |
| Mapping rules inline in SKILL.md | Task 3 |
| Navigate + snapshot flow | Task 3 (flow section) |
| Cover letter pause | Task 3 (special cases) |
| File upload | Task 3 (special cases) |
| Report format | Task 3 (report section) |
| Learn from manual edits | Task 3 (step 7) |
| Hard rules preserved | Task 3 (hard rules section) |
| profile.json extra_fields | Task 3 (learning section) |

All spec requirements covered. No gaps.

### Placeholder scan

No TBD, TODO, or vague steps. All code blocks complete.

### Type consistency

No shared types across tasks — each task is self-contained file edits.
