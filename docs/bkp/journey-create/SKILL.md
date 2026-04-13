---
name: journey-create
description: >
  Authoring tool for the Atomic Journey System (AJS). Use whenever the user wants to create
  a new journey, flow, feature, or automation — even if they phrase it as "criar um fluxo para X",
  "adicionar uma nova jornada", "preciso de um script para Y", "construir automação para Z",
  "adicionar nova capacidade ao sistema", or "expandir o AJS". This skill generates atomic scripts,
  journey manifests, and keeps the state dictionary (state-example.json) clean and de-duplicated.
  Always use this skill when expanding AJS capabilities — it is the AJS Compiler/Writer that ensures
  all contracts between scripts and the journey-use executor remain valid. Use even if the user
  just describes a business scenario without mentioning "journey" or "AJS" explicitly — if the
  project uses AJS, this is the right tool.
---

# Journey Create — AJS Authoring Tool

You are the **AJS Compiler** — the tool that translates business requirements into reusable
atomic scripts and journey manifests. Your outputs will be executed by `journey-use` (the Runtime).

The golden rule: **one script = one atomic action**. Scripts are agnostic, reusable building blocks.
The journey manifest is the only place that knows the full story.

## AJS File Layout

| Artefact | Location (relative to project root) |
|----------|--------------------------------------|
| Atomic scripts | `.claude/skills/journey-use/scripts/` |
| Journey manifests | `.claude/skills/journey-use/journeys/<journey-name>.md` |
| State dictionary | `.claude/skills/journey-use/state-example.json` |
| Capability index | `.claude/skills/journey-use/indice.md` |

If these directories don't exist yet, create them as part of this task.

---

## Step 1 — Understand the Requirement

Ask clarifying questions if the description is ambiguous. Once you understand the goal:

1. **Explore the codebase** — search for Models, Services, Controllers relevant to the domain.
   For "driver rating flow", look for `DriverRating`, `RatingService`, `RatingController`, etc.
2. **Read `state-example.json`** — catalog every key that already exists.
3. **List existing scripts** in `.claude/skills/journey-use/scripts/` — identify what can be reused.
4. **Read `indice.md`** — understand what journeys already exist.

Then tell the user your plan explicitly:
> "Encontrei os seguintes scripts reutilizáveis: [list]. Precisarei criar os seguintes novos: [list]."

Get a quick thumbs-up before writing code.

---

## Step 2 — Validate & Map State Keys

Every input and output in the journey must map to a key in `state-example.json`.

- **Key exists** → use it exactly as-is. Never create aliases or camelCase versions.
- **Key doesn't exist** → propose it using `snake_case` English, matching the naming
  convention of nearby keys in the file.
- **User proposes a non-standard name** → correct it automatically and explain:
  > "Usei `driver_id` em vez de `id_motorista` para manter consistência com o dicionário de estado."

State integrity is the foundation of AJS. A single broken key name can cause runtime failures
across multiple journeys, so be strict here.

---

## Step 3 — Generate Atomic Scripts

For each new script needed, follow the **AJS Script Contract** (full rules in `references/ajs-contract.md`):

### The 5 Rules
1. **Single Responsibility** — one script does exactly one thing.
2. **Input from state.json** — read ALL inputs from the state file path passed as `argv[1]`.
3. **Output to state.json** — on success, write the result back to the same file.
4. **Exit codes** — `exit(0)` success, `exit(1)` business error (message on stdout).
5. **Agnosticism** — the script must not know which journey uses it.

### Before Creating a New Script

Search for similar scripts first:
```bash
ls .claude/skills/journey-use/scripts/ | grep -i <keyword>
grep -r "<functionality>" .claude/skills/journey-use/scripts/
```

If an existing script covers 80%+ of the need, extend it or create a thin wrapper.
Avoid inflating the scripts directory with near-duplicates.

### Script Template (PHP)

```php
<?php
// submit_rating.php — Submits a driver rating
// Input:  state.json -> driver_id, rating_value, trip_id
// Output: state.json -> rating_id

$statePath = $argv[1] ?? 'state.json';
$state = json_decode(file_get_contents($statePath), true);

$driverId    = $state['driver_id']    ?? null;
$ratingValue = $state['rating_value'] ?? null;
$tripId      = $state['trip_id']      ?? null;

if (!$driverId || !$ratingValue || !$tripId) {
    echo "Erro: driver_id, rating_value e trip_id são obrigatórios.";
    exit(1);
}

// ... business logic (DB call, API call, etc.) ...

$state['rating_id'] = $newRatingId;
file_put_contents($statePath, json_encode($state, JSON_PRETTY_PRINT));

echo "Rating {$newRatingId} criado com sucesso.";
exit(0);
```

Adapt to the language that fits the existing project — check what's already in `scripts/`
and match the convention (PHP, Python, or JS).

Keep each script under ~100 lines. If it's growing larger, that's a signal to split it.

---

## Step 4 — Write the Journey Manifest

Create `.claude/skills/journey-use/journeys/<journey-name>.md`:

```markdown
# Journey: <Nome da Jornada>

## Objetivo
<One-sentence description of what this journey accomplishes for the end user.>

## Estado Necessário (Inputs)
| Chave           | Tipo   | Descrição                    |
|-----------------|--------|------------------------------|
| driver_id       | string | ID do motorista no sistema   |
| rating_value    | int    | Nota de 1 a 5                |

## Estado Produzido (Outputs)
| Chave     | Tipo | Descrição                   |
|-----------|------|-----------------------------|
| rating_id | int  | ID da avaliação criada      |

## Sequência de Scripts
1. `get_driver.php` — Verifica se o motorista existe e carrega seus dados base
2. `validate_trip.php` — Confirma que a corrida pertence ao usuário corrente
3. `submit_rating.php` — Submete a avaliação e registra no banco

## Notas
- <Pré-condições, regras de negócio especiais, ou advertências.>
- <Ex: "O motorista deve ter status ACTIVE. Se SUSPENDED, o script retorna exit(1).">
```

---

## Step 5 — Update state-example.json

If new keys were added, append them to `state-example.json` with realistic example values.

```json
{
  "driver_id": "drv_abc123",
  "rating_value": 5,
  "trip_id": "trip_xyz789",
  "rating_id": 42
}
```

**Never remove or rename existing keys.** Other journeys depend on them.
If the purpose of a new key isn't obvious from the name, add a `_doc_<key>` entry:
```json
{
  "rating_value": 5,
  "_doc_rating_value": "Integer 1-5 representing the user's rating for the driver"
}
```

---

## Step 6 — Register in indice.md

Add the new journey to `.claude/skills/journey-use/indice.md`:

```markdown
- [Avaliação de Motorista](journeys/avaliar-motorista.md) — Submete nota do usuário após uma corrida
```

Group related journeys under thematic headers if the index already has sections.

---

## Checklist Before Delivering

- [ ] All input/output keys exist in `state-example.json`
- [ ] Each new script follows the 5-rule AJS Contract (see `references/ajs-contract.md`)
- [ ] No duplicate scripts were created (searched before writing)
- [ ] Journey manifest includes clear Inputs/Outputs tables and Script Sequence
- [ ] `state-example.json` updated with new keys (if any)
- [ ] `indice.md` updated with new journey link
- [ ] Scripts are in the language matching the project convention

For the full AJS Contract with language-specific templates, read `references/ajs-contract.md`.
