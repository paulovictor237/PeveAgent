---
name: subscrible-job
description: Especialista em preencher formulários de candidatura a vagas de emprego. Use quando o usuário fornecer uma URL de vaga e quiser se candidatar automaticamente.
---

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

`SKILL_DIR` = `/Users/peve/workspace/PeveAgent/.agents/skills/subscrible-job`

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
