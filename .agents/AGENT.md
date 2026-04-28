## Default Language

English is the default language. Communicate in English unless the user explicitly switches to another language.

## English Coach

When the user writes a message in English (fully or partially), only flag **genuine mistakes** (typos, wrong words, unclear grammar). Do NOT flag:
- Informal style (u, ur, gonna, wanna, y'all, etc.)
- Missing capitalization or punctuation in casual messages
- Contractions or colloquialisms

When there IS a real mistake, start your response with a single line:

`💡 **English tip:** "<corrected version>" — <brief reason>`

Skip this line if the message is correct OR if it's just informal/casual. Keep it to one line, no extra explanation.

## Code Style

- **NEVER adicione comentários no código** — nem inline, nem de bloco, nem docstrings/JSDoc. O código deve ser autoexplicativo.

## Tool Preferences

- **ALWAYS use GitHub CLI (`gh`) via the Bash tool** for all GitHub-related tasks
- **DO NOT use MCP servers** for GitHub operations
- Examples: `gh pr create`, `gh issue list`, `gh pr view`, `gh api`, etc.
- The GitHub CLI provides more reliable and direct access to GitHub functionality

- **ALWAYS use Atlassian CLI (`acli`) via the Bash tool** for all Atlassian-related tasks (Jira, Confluence)
- **DO NOT use MCP servers** for Atlassian operations
- Examples: `acli jira issue create`, `acli confluence page list`, `acli jira issue view`, etc.
- The Atlassian CLI provides more reliable and direct access to Atlassian functionality

## LSP (Language Server Protocol) Usage

- **ALWAYS use LSP when convenient** for code analysis, navigation, and understanding
- LSP provides accurate type information, definitions, references, and diagnostics
- Prefer LSP for tasks such as:
  - Finding function/class definitions and implementations
  - Discovering all references to a symbol
  - Getting accurate type information
  - Identifying compilation errors and warnings
  - Code completion suggestions
  - Refactoring operations (rename, extract, etc.)
- LSP is especially useful when working with strongly-typed languages (TypeScript, Go, Rust, Java, C#, etc.)
- Use LSP to complement other tools like Grep and Glob for more precise code navigation

## Skill Development Guidelines

- **Ao criar ou atualizar uma skill, SEMPRE otimize com scripts** para economizar tokens
- **Prefira scripts a respostas em texto**: scripts são mais rápidos, precisos e consomem muito menos tokens
- Use `bash` ou `python` — ambos são boas práticas; escolha o mais adequado para cada situação:
  - Prefira **bash** para operações de sistema, pipes, chamadas de CLI e transformações simples com `jq`, `awk`, `grep`, `sed`
  - Prefira **python** para lógica mais complexa, manipulação estruturada de dados (JSON, YAML, CSV), ou quando a legibilidade for prioritária
- Exemplos de otimizações com scripts:
  - Colete dados estruturados (JSON, listas, contagens) com um script em vez de ler arquivos um a um
  - Filtre e transforme dados diretamente no terminal sem precisar de múltiplas chamadas de ferramenta
  - Evite ler arquivos inteiros quando um script pode extrair apenas o trecho necessário
  - Prefira um único script que faça múltiplas operações a várias chamadas de ferramenta separadas
  - Use scripts para validar pré-condições antes de executar ações (ex: verificar se branch existe, se PR está aberto, etc.)
- **Regra de ouro**: se uma informação pode ser obtida com um script em vez de múltiplos `view`/`grep`/`glob`, use o script

<!-- CODEGRAPH_START -->
## CodeGraph

CodeGraph builds a semantic knowledge graph of codebases for faster, smarter code exploration.

### If `.codegraph/` exists in the project

**NEVER call `codegraph_explore` or `codegraph_context` directly in the main session.** These tools return large amounts of source code that fills up main session context. Instead, ALWAYS spawn an Explore agent for any exploration question (e.g., "how does X work?", "explain the Y system", "where is Z implemented?").

**When spawning Explore agents**, include this instruction in the prompt:

> This project has CodeGraph initialized (.codegraph/ exists). Use `codegraph_explore` as your PRIMARY tool — it returns full source code sections from all relevant files in one call.
>
> **Rules:**
> 1. Follow the explore call budget in the `codegraph_explore` tool description — it scales automatically based on project size.
> 2. Do NOT re-read files that codegraph_explore already returned source code for. The source sections are complete and authoritative.
> 3. Only fall back to grep/glob/read for files listed under "Additional relevant files" if you need more detail, or if codegraph returned no results.

**The main session may only use these lightweight tools directly** (for targeted lookups before making edits, not for exploration):

| Tool | Use For |
|------|---------|
| `codegraph_search` | Find symbols by name |
| `codegraph_callers` / `codegraph_callees` | Trace call flow |
| `codegraph_impact` | Check what's affected before editing |
| `codegraph_node` | Get a single symbol's details |

### If `.codegraph/` does NOT exist

At the start of a session, ask the user if they'd like to initialize CodeGraph:

"I notice this project doesn't have CodeGraph initialized. Would you like me to run `codegraph init -i` to build a code knowledge graph?"
<!-- CODEGRAPH_END -->

@RTK.md
