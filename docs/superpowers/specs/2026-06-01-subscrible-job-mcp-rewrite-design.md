# subscrible-job — Playwright MCP Rewrite

**Date:** 2026-06-01  
**Status:** Approved

## Summary

Replace Python/Playwright subprocess with Claude driving browser directly via `@playwright/mcp`. No scripts. No subprocess. Claude IS the automation layer.

## Architecture

### Tools

| MCP Tool | Purpose |
|---|---|
| `playwright_navigate` | Open job URL |
| `playwright_snapshot` | Read accessibility tree (fields, labels, roles) |
| `playwright_fill` | Fill text inputs / textareas |
| `playwright_select_option` | Native `<select>` dropdowns |
| `playwright_click` | Checkboxes, radio buttons, custom dropdowns |
| `playwright_upload_file` | PDF upload |
| `playwright_screenshot` | Visual verify when uncertain |

### File Structure

```
assets/profile.json       ← candidate data
assets/Profile-pt.pdf     ← CV Portuguese
assets/Profile-en.pdf     ← CV English
SKILL.md                  ← flow + mapping rules
scripts/                  ← DELETED
```

## Execution Flow

```
1. playwright_navigate → URL
2. playwright_snapshot → parse all form fields
3. For each field: match label/placeholder/aria against mapping rules → fill
4. Report: ✓ filled / ⚠ cover_letter / ○ unmapped / ✗ failed
5. Pause: tell user which fields need manual attention
6. User fills manually → tells Claude "done"
7. playwright_snapshot → diff vs step-2 baseline → save new values to profile.json
```

## Mapping Rules (semantic, applied by Claude)

Ordered most-specific → most-generic. First match wins.

### Identity
- `full name` / `nome completo` → `profile.name`
- `first name` / `primeiro nome` → first word of `profile.name`
- `last name` / `sobrenome` → remaining words of `profile.name`

### Contact
- `email` / `e-mail` → `profile.email`
- `telefone` / `celular` / `phone` / `whatsapp` → `profile.phone`
- `cpf` → `profile.cpf`
- `rg` / `documento de identidade` → `profile.rg`

### Birth
- `data de nascimento` / `birth date` / `birthday` → `profile.birth_date` (ISO format for `type=date`)

### Links
- `linkedin` → `profile.linkedin`
- `github` / `portfolio` → `profile.github`

### Address
- `cidade` / `city` → `profile.address.city`
- `estado` / `state` / `uf` → `profile.address.state` (match dropdown option)
- `país` / `country` → `profile.address.country`
- `endereço` / `rua` / `street` → `profile.address.street + number`
- `cep` / `zip` / `postal code` → `profile.extra_fields.cep`
- `bairro` / `neighborhood` → `profile.extra_fields.bairro`

### Education
- `universidade` / `faculdade` / `institution` / `school name` → `profile.education[0].institution`
- `curso` / `field of study` / `major` → `profile.education[0].field`
- `grau` / `degree` / `nível de ensino` → `profile.education[0].degree` (match dropdown)
- `status da formação` / `situação` / `concluiu` → `Completo` if end year ≤ 2026, else `Cursando` (match dropdown)
- `ano de conclusão` / `graduation year` → year from `profile.education[0].end`
- `mês de conclusão` / `graduation month` → month name from `profile.education[0].end`
- `formação` / `escolaridade` → short string: `{degree} em {field} — {institution}`

### Experience
- `empresa atual` / `current company` / `onde trabalha` → `profile.experience[0].company`
- `cargo atual` / `current role` / `posição` → `profile.current_role`
- `experiência` / `anos de experiência` → duration string from `profile.experience[0]`

### Salary / Contract
- `salário` / `pretensão` / `salary expectation` → `PJ: R$ {min}~{max} / CLT: R$ {min}~{max}`
- `contrato` / `regime` / `contract type` → `profile.job_preferences.primary.contract` (match dropdown)

### Availability
- `modalidade` / `modelo de trabalho` / `work model` → `profile.job_preferences.primary.modality` (match dropdown)
- `disponibilidade` / `quando pode começar` / `notice period` → `{availability_days/30} mês`
- `viagem` / `travel` → `Sim`/`Não` from `profile.job_preferences.willing_to_travel`
- `mudança` / `relocate` → `Sim`/`Não` from `profile.job_preferences.willing_to_relocate`
- `modelo híbrido` → `Sim` only if modality contains `híbrido`

### Diversity
- `pcd` / `deficiência` / `disability` → `Sim`/`Não` from `profile.pcd`
- `gênero` / `gender` / `sexo` → `profile.gender` (match dropdown)
- `pronome` → `profile.pronoun` (match dropdown)
- `raça` / `etnia` / `cor` / `ethnicity` → `profile.ethnicity` (match dropdown)

### Recruitment
- `parentesco` / `parente` / `conhece funcionário` → `Não`
- `como ficou sabendo` / `como nos encontrou` / `source` / `canal` → `profile.job_preferences.job_source`

### Other
- `idioma` / `língua` / `language` → comma-joined `profile.languages`
- `sobre você` / `resumo` / `summary` / `bio` → `profile.summary`
- `habilidade` / `skill` / `tecnologia` → comma-joined `profile.skills`
- `nome` (generic fallback) → `profile.name`

## Special Cases

### File upload
Any `input[type=file]` → upload `Profile-pt.pdf`. If the form appears to be in English → `Profile-en.pdf`.

### Cover letter
Any `textarea` matching `cover letter` / `carta de apresentação` / `apresentação` / `motivação`:
1. **Stop filling**
2. Report `⚠ Cover letter — campo: "{label}"`
3. Ask user for text
4. Fill with user-provided text

### Dropdown matching
When filling a `<select>` or custom dropdown, find the option whose normalized text best matches the value. Normalize = lowercase + remove accents + collapse whitespace. If no match, leave unfilled and mark `○ unmapped`.

### Checkbox / radio
Fill only if resolved value is truthy (`sim` / `yes` / `true` / `1`). Skip otherwise.

## Hard Rules

1. **NEVER click submit / enviar / finalizar / candidatar / apply**
2. **NEVER invent data** — use only what's in `profile.json`
3. **ALWAYS pause** on cover letter fields and ask user
4. **ALWAYS upload PDF** when file input found
5. **No retry loops** — mark `✗` and move on if fill fails

## profile.json Learning

After user says "done":
1. Take final `playwright_snapshot`
2. Compare with baseline snapshot from step 2
3. Fields that changed and were NOT filled by Claude → user manually filled them
4. Add to `profile.json → extra_fields` with label as key
5. Save file

## Report Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ N campos detectados

✓ Preenchido (N):
  • Nome completo → Paulo Victor Duarte
  • Email → paulovictor237@gmail.com

⚠ Cover letter — preencha manualmente:
  • Carta de Apresentação

○ Não mapeados (N):
  • Campo XYZ (nenhuma keyword correspondeu)

✗ Falhas (N):
  • Campo ABC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Preencha o restante no browser. Quando terminar, diga "feito".
```

## MCP Configuration

Add to `claude-mcp.json` and `opencode.json`:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```
