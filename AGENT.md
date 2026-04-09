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

**Use codegraph tools for faster exploration.** These tools provide instant lookups via the code graph instead of scanning files:

| Tool | Use For |
|------|---------|
| `codegraph_search` | Find symbols by name (functions, classes, types) |
| `codegraph_context` | Get relevant code context for a task |
| `codegraph_callers` | Find what calls a function |
| `codegraph_callees` | Find what a function calls |
| `codegraph_impact` | See what's affected by changing a symbol |
| `codegraph_node` | Get details + source code for a symbol |

**When spawning Explore agents in a codegraph-enabled project:**

Tell the Explore agent to use codegraph tools for faster exploration.

**For quick lookups in the main session:**
- Use `codegraph_search` instead of grep for finding symbols
- Use `codegraph_callers`/`codegraph_callees` to trace code flow
- Use `codegraph_impact` before making changes to see what's affected

### If `.codegraph/` does NOT exist

At the start of a session, ask the user if they'd like to initialize CodeGraph:

"I notice this project doesn't have CodeGraph initialized. Would you like me to run `codegraph init -i` to build a code knowledge graph?"
<!-- CODEGRAPH_END -->

@RTK.md
