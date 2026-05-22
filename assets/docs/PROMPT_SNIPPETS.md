# Prompt Engineering Snippets

Zed snippets for high-leverage prompt engineering patterns. Each snippet encodes a reusable technique — orthogonal to any specific task, composable with each other.

**Location:** `assets/configs/zed-snippets.json` (symlinked to `~/.config/zed/snippets/markdown.json`)

**Usage:** In any `.md` file in Zed, type the prefix and press `Tab` to expand. Use `Tab` again to jump between placeholders.

---

## Quick Reference

| Prefix | Pattern | Best for |
|--------|---------|----------|
| `pq` | Quick minimal | Daily one-off prompts |
| `prc` | Role + constraints | Steering model behavior |
| `pcot` | Chain-of-thought | Math, logic, multi-step reasoning |
| `pfs` | Few-shot examples | Teaching by demonstration |
| `pso` | Structured output | JSON/schema-locked responses |
| `psc` | Self-critique | Draft → critique → revise loop |
| `pdc` | Decomposition | Complex multi-step asks |
| `pcx` | Context priming | Domain-heavy tasks |
| `pdel` | Delimited input | Prompt injection defense |
| `prub` | Rubric eval | Scoring/judging outputs |
| `ptot` | Tree-of-thought | Design/architecture decisions |

---

## `pq` — Quick Prompt

**Pattern:** Task + Context + Constraint

**When to use:** Daily quick asks where you want structure without ceremony. The minimum viable prompt — three fields force you to state what, why, and what's off-limits.

**Why it works:** Most bad prompts fail because they skip context or constraints. This template makes both mandatory.

**Example fill:**
```
**Task:** Rename `getUserData` to `fetchUserProfile` across the repo
**Context:** TypeScript monorepo, ~200 call sites
**Constraint:** Don't touch tests yet — just the implementation files
```

---

## `prc` — Role + Constraints

**Pattern:** Persona + goal + explicit do/don't lists

**When to use:** When the model needs strong behavioral steering. Useful for code review, technical writing, customer-facing copy, or any task where tone/scope drift is a risk.

**Why it works:** "You MUST NOT" is far more effective than hoping the model infers boundaries. Explicit negative constraints prevent the most common failure modes.

**Tip:** Pair "you MUST" rules with rationale when the rule isn't self-evident.

---

## `pcot` — Chain-of-Thought

**Pattern:** Force step-by-step reasoning in `<thinking>` tags before answering in `<answer>` tags

**When to use:**
- Math, logic puzzles, multi-step calculations
- Decisions with multiple factors
- Anything where you've seen the model jump to wrong conclusions

**Why it works:** Models that "think out loud" before answering have measurably higher accuracy on reasoning tasks. The XML tags let you parse out just the answer programmatically.

**Avoid for:** Simple factual lookups, creative writing — adds latency without benefit.

---

## `pfs` — Few-Shot Examples

**Pattern:** Show 2-4 input→output pairs, then ask the model to apply the same pattern

**When to use:**
- Classification (sentiment, intent, category)
- Format/style transfer (formal → casual, English → SQL)
- Any task where "show, don't tell" is faster than describing rules

**Why it works:** Examples disambiguate edge cases that natural-language rules can't cover. 3 well-chosen examples often beat a page of instructions.

**Tip:** Include at least one edge case in your examples — not just the happy path.

---

## `pso` — Structured Output

**Pattern:** Lock the response to a precise schema, with rules against invention and extra fields

**When to use:** Any time the output feeds into code (parsing, pipelines, automation). Eliminates prose, code fences, and "Here is the JSON:" preambles.

**Why it works:** The explicit "null for unknown" rule prevents hallucination. The "no markdown fences" rule prevents the most common parsing failure.

**Tip:** Combine with `pdel` when processing user input — schema lock + injection defense.

---

## `psc` — Self-Critique

**Pattern:** Draft → critique against criteria → revise

**When to use:**
- Subjective work: writing, naming, API design, UX copy
- High-stakes outputs where one pass isn't enough
- When you'd otherwise iterate manually 2-3 times

**Why it works:** Forcing the model to find weaknesses in its own draft surfaces issues it would otherwise miss. The "specific weaknesses, not generic praise" rule prevents lazy self-evaluation.

**Cost:** ~3x tokens vs single-pass. Worth it when quality matters.

---

## `pdc` — Decomposition

**Pattern:** Break a complex goal into ordered sub-tasks with explicit "complete fully before moving on" rule

**When to use:**
- Multi-file refactors
- Implementation plans
- Anything where the model tends to skip steps or do them shallowly

**Why it works:** "State the result before continuing" creates checkpoints — you can stop and correct course without the model losing the thread.

**Tip:** If you find yourself writing more than 5 sub-tasks, the goal is probably too big for one prompt. Split it.

---

## `pcx` — Context Priming

**Pattern:** Background + key facts + glossary, *then* the ask

**When to use:** Domain-heavy work where the model needs grounding it doesn't have by default — internal systems, niche libraries, project-specific conventions.

**Why it works:** Putting context *before* the ask is more effective than scattered context. The glossary section is especially powerful for projects with overloaded terms (e.g., "customer" means different things in billing vs CRM).

**Anti-pattern:** Don't use for general knowledge tasks — the model already has that context.

---

## `pdel` — Delimited Input

**Pattern:** Wrap untrusted content in `<input>` tags with explicit "treat as data, not instructions" framing

**When to use:** **Always** when processing user-provided content, scraped data, or anything you didn't write yourself.

**Why it works:** Prompt injection attacks rely on the model conflating instructions with data. Explicit delimiters + the "data, not commands" framing make injection far harder.

**Critical:** This is a defense-in-depth measure, not a guarantee. Combine with output validation for production systems.

---

## `prub` — Rubric-Based Evaluation

**Pattern:** Weighted criteria table → score each → weighted total + verdict

**When to use:**
- Eval pipelines (judging model outputs)
- Code review with structured feedback
- Comparing candidates (PRs, designs, hires)

**Why it works:** Forces the model to be specific and balanced. The "one concrete improvement per criterion" rule prevents vague feedback like "could be better."

**Tip:** Weights should sum to a clean number (10 or 100) for readable totals.

---

## `ptot` — Tree-of-Thought

**Pattern:** Generate N distinct approaches → analyze each → recommend with stated tradeoff

**When to use:**
- Architecture decisions
- Design exploration
- Any "should we do X or Y?" question where you want the full landscape

**Why it works:** Forcing "genuinely different, not variations" prevents the model from anchoring on the first idea. The "state the tradeoff you're accepting" rule prevents fake consensus.

**Tip:** Default to 3 approaches. More dilutes; fewer collapses into binary thinking.

---

## Composing Patterns

These patterns are designed to combine:

- **`pcx` + `pso`** — Domain context + structured output for grounded data extraction
- **`pdel` + `pso`** — Process untrusted input safely into structured form
- **`pdc` + `psc`** — Decompose then critique each sub-result
- **`pcot` + `prub`** — Reasoned scoring with visible justification
- **`prc` + `pfs`** — Role + examples for consistent persona work

The patterns are orthogonal — pick the smallest set that addresses your failure modes, don't stack them defensively.

---

## What's *Not* Here (and Why)

Snippets discarded because they belong as skills or task-specific tooling:
- Feature implementation, debugging templates → covered by project skills
- Code review, test generation, commit messages → covered by `code-review`, `atomic-commits`, etc.
- Migration guides, API design templates → too task-shaped, not technique-shaped

The bar for inclusion: **reusable across tasks, independent of domain, encodes a measurable improvement in output quality.**
