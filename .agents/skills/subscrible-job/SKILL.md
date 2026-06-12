---
name: subscrible-job
description: Use when the user wants to automatically fill out job application forms from a provided vacancy or job listing URL.
---

# subscrible-job

Fill job application forms using agent-browser CLI commands. Claude drives the browser directly via the CLI — no custom scripts.

## Hard Rules

1. **NEVER click submit / enviar / finalizar / candidatar / apply**
2. **NEVER invent data** — use only what is in `profile.json`
3. **ALWAYS pause** on cover letter fields and ask the user for text
4. **ALWAYS upload PDF** when a file input is found
5. **No retry** — mark `✗` and move on if any fill operation fails

## Assets

```
SKILL_DIR/assets/profile.json     ← candidate data
SKILL_DIR/assets/Profile-pt.pdf   ← CV Portuguese
SKILL_DIR/assets/Profile-en.pdf   ← CV English
```

`SKILL_DIR` = `/Users/paulo.duarte/workspace/outros/PeveAgent/.agents/skills/subscrible-job`

## How to invoke

User: `/subscrible-job <URL>`

## Execution Flow

### 1. Load profile

Read `SKILL_DIR/assets/profile.json`. Extract all candidate data.

### 2. Navigate

```bash
agent-browser open "<URL>"
```

### 3. Baseline snapshot

```bash
agent-browser snapshot -i
```

Parse all form fields from the interactive accessibility tree.
For each field, note its element reference (e.g., `@e1`, `@e2`), role, label, placeholder, aria-label, name/id, type, and any options (if it is a dropdown/select).

### 4. Fill fields

For each field, apply the mapping rules below (most-specific first, first match wins).
Normalize text for matching: lowercase + remove accents + collapse whitespace.

If a resolved value is found:
- `input[type=text/email/tel/url/number]` or `textarea` → `agent-browser fill @eN "value"`
- `select` (or standard dropdown) → `agent-browser select @eN "option-value"`
- `input[type=checkbox]` or `input[type=radio]` → `agent-browser check @eN` (only if the value is truthy: `sim/yes/true/1`)
- `input[type=file]` → `agent-browser upload @eN "<pdf_path>"` (see File Upload rule)
- Custom dropdown (role=combobox, listbox) → `agent-browser click @eN` to open, then run `agent-browser snapshot -i` to update references, and click the matching option.

If a field matches the cover_letter rule → **STOP, ask user** (see Cover Letter rule).
If no rule matches → mark `○ unmapped`.
If fill fails or throws an error → mark `✗ failed` and continue to the next field.

> **CRITICAL REF RULE:** Refs `@eN` become stale whenever the DOM or viewport changes (after clicks, selections, or page updates). Always run `agent-browser snapshot -i` to get fresh references after any interacting step that changes page state.

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

After filling all auto-fillable fields, pause. Tell the user which fields need manual attention. Wait for the user to say "feito" / "done" / "pronto".

### 7. Learn new values

```bash
agent-browser snapshot -i
```

Compare the final form values with the baseline values.
Fields that:
- Were empty in the baseline snapshot AND have a value in the final snapshot AND were NOT filled by Claude
→ user manually filled them.

Add each to `profile.json → extra_fields` with the field label as the key. Save the file.

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

Use `agent-browser upload @eN "<pdf_path>"`.

### Cover Letter
Any textarea whose label/placeholder/aria matches:
`cover letter` / `carta de apresentacao` / `carta de motivacao` / `apresentacao` / `motivacao` / `por que voce quer`

→ **Do NOT fill. Report `⚠` and ask user:**
> "Campo de cover letter encontrado: '{label}'. Cole o texto que devo usar."

After user provides text → `agent-browser fill @eN "<text>"`.

### Dropdown Option Matching
When selecting from a dropdown, normalize both the target value and each option (lowercase + remove accents). Use `agent-browser select @eN "<option-value>"`.

### Checkbox / Radio
Only interact if resolved value is truthy (`sim` / `yes` / `true` / `1`). Use `agent-browser check @eN`.

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
