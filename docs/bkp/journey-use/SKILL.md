---
name: journey-use
description: >
  Runtime executor for the Atomic Journey System (AJS). Use whenever the user wants to run,
  simulate, execute, or test a journey or flow — even if they phrase it as "roda a jornada X",
  "simula o fluxo de contratação", "executa o script Y", "testa o motorista 45", "continua de onde parou",
  "usa o contexto atual para...", or "preciso simular o passo Z". Also triggers when the user passes
  IDs directly in the command (e.g., "motorista 45, contrato 123"). This skill manages state.json,
  executes atomic scripts in black-box mode, and handles auto-healing when dependencies are missing.
  Use this skill for ANY execution or simulation request — it is the AJS engine.
---

# Journey Use — AJS Runtime

You are the **AJS Runtime** — the executor that runs atomic scripts in sequence, manages the
shared state, and keeps the user unblocked when something is missing.

Golden rule: **never read script source code**. You execute scripts blind, trust their exit codes,
and only read the last line of stdout. The contract is the interface; the implementation is irrelevant.

## AJS File Layout

| Artefact | Location |
|----------|----------|
| State (current session) | `.claude/skills/journey-use/state.json` |
| State contract | `.claude/skills/journey-use/state-example.json` |
| Capability index | `.claude/skills/journey-use/indice.md` |
| Scripts | `.claude/skills/journey-use/scripts/` |
| Journey manifests | `.claude/skills/journey-use/journeys/` |

---

## Step 1 — Sync State from Prompt

Before anything else, extract IDs from the user's message and write them to `state.json`.

- User says "motorista 45" → write `{"driver_id": 45}` to state.json
- User says "contrato abc-123" → write `{"contract_id": "abc-123"}`
- User provides no IDs → skip this step

To find the correct key name, check `state-example.json`. Use the exact key that matches
the entity — never invent aliases like `id_motorista` or `contractId`.

Merge into the existing state — never overwrite the full file.

---

## Step 2 — Identify the Journey

Read `indice.md` to find which journey or script the user is referring to.

If the user names a specific journey (e.g., "contratação padrão"), open the journey manifest
from `journeys/` and read the **Script Sequence**.

If the user asks to run a single script directly, proceed to Step 3.

If the journey doesn't exist, tell the user and suggest using `journey-create` to build it.

---

## Step 3 — Validate Context

Read `state.json` and compare with the journey's **Estado Necessário (Inputs)** table.

For each required input:
- **Present in state** → proceed
- **Missing** → check `indice.md` for a script that creates this resource

If a creation script exists:
> "Falta `driver_id` no estado. Encontrei `create_driver.php` no catálogo. Deseja executá-lo primeiro?"

If no creation script exists:
> "Falta `driver_id` e não há script de criação disponível. Informe o ID ou use `journey-create` para criar o script."

Do not proceed until all required inputs are present.

---

## Step 4 — Execute Scripts (Black-Box)

Execute each script in the journey sequence:

```bash
php .claude/skills/journey-use/scripts/<script-name>.php .claude/skills/journey-use/state.json
```

Or for Python/JS, adapt the interpreter accordingly.

**What to monitor:**
- Exit code: `0` = success, `1` = business error
- Last line of stdout only (the new ID or confirmation message)

**What to ignore:**
- Script source code
- Intermediate stdout lines
- Warnings that don't affect exit code

After each successful script, re-read `state.json` to get the updated state for the next step.

---

## Step 5 — Auto-Healing on Failure

If a script exits with code `1`:

1. Show the error message from stdout
2. Check if the failed resource has a creation script in `indice.md`
3. Offer auto-healing:
   > "Script `vincular_contrato.php` falhou: `driver_id 45 não encontrado no sistema`.
   > Deseja executar `create_driver.php` para criar este recurso?"

If the user confirms, run the creation script and retry the failed step.
If the user declines, stop and report the final state.

Never retry a failed script without user confirmation or a state change.

---

## Step 6 — Report Completion

When the journey finishes successfully, report:

```
Jornada concluída: <nome>
Estado final relevante:
  driver_id: 45
  contract_id: uuid-abc-123
  transport_id: 7
```

Show only keys that changed during this run — not the entire state.

---

## Token Economy Rules

- **Never** list directory contents more than once per session
- **Never** read script source code — only execute and read output
- **Never** ask "qual o ID?" if it's already in `state.json`
- `state.json` is the single source of truth — trust it
