# Resumo das Skills Disponíveis

Este documento contém um resumo breve de todas as skills disponíveis na pasta `skills-henrrique/`.

---

## 1. **atomic-commits**

### O que faz
Cria commits semânticos e atômicos seguindo a especificação Conventional Commits. Cada commit representa UMA mudança lógica com um tipo claro.

### Como usar
Invoque via `/atomic-commits` ou quando for necessário fazer commits de código.

### Exemplo de uso
```bash
feat(api): add user profile endpoint

fix(auth): resolve token expiration issue

refactor(db): optimize query performance

# Breaking changes
feat(api)!: change authentication method
BREAKING CHANGE: API now requires Bearer token instead of API key
```

### Tipos disponíveis
- `feat`: Nova funcionalidade
- `fix`: Correção de bug
- `refactor`: Refatoração de código
- `docs`: Documentação
- `test`: Testes
- `perf`: Melhorias de performance
- `style`: Formatação de código
- `build`: Sistema de build
- `ci`: CI/CD
- `chore`: Tarefas gerais

---

## 2. **code-review**

### O que faz
Revisão rápida de PRs verificando regras customizadas e boas práticas, especialmente para aplicações Laravel.

### Como usar
```bash
# Quando o usuário pedir: "Review PR #123" ou "Check PR #456"
gh pr diff <PR_NUMBER>
gh pr view <PR_NUMBER> --json commits
```

### O que verifica

**Crítico 🔴:**
- Eloquent `update/delete` sem `get/first` (pode atualizar múltiplos registros)
- SQL raw com concatenação (risco de SQL injection)
- Mass assignment com `request->all()` (vulnerabilidade)
- Blade unescaped `{!! $variable !!}` (XSS)

**Alta Prioridade 🟡:**
- Problemas N+1 (acessar relacionamentos em loops)
- Rotas sem middleware de autenticação
- Controllers sem validação

**Média Prioridade 🟠:**
- `env()` fora de config/ (não funciona com cache)
- Código de debug deixado (dd, dump, var_dump)
- DTOs não usando ValidatedDTO

---

## 3. **jira-searcher**

### O que faz
Integração read-only com Jira para buscar contexto de epics e planejamento de tarefas.

### Como usar
```bash
~/.claude/tools/jira_read.py <action> <ISSUE-KEY>
```

### Comandos disponíveis
```bash
# Detalhes de um epic
~/.claude/tools/jira_read.py epic PROJ-123

# Listar todas as tarefas de um epic
~/.claude/tools/jira_read.py epic-children PROJ-123
```

### Exemplo de uso
Quando o usuário menciona uma chave de epic/task (ex: "implementar PROJ-123"), use esta skill para buscar o contexto completo.

---

## 4. **laravel-patterns**

### O que faz
Guia de boas práticas Laravel 12, padrões Eloquent, Service classes, Form Requests e recursos PHP 8.x.

### Como usar
Use quando trabalhar com projetos Laravel, controllers, models, migrations ou código PHP backend.

### Padrões principais

**Arquitetura:**
- Service Layer: Controllers finos (máx 10 linhas)
- Repository Pattern: Para queries complexas
- Form Requests: Para validação

**Eloquent:**
```php
// ✅ Bom - Usar select() e with()
User::select(['id', 'name', 'email'])
    ->with('posts:id,user_id,title')
    ->get();

// ❌ Evitar - N+1
foreach ($users as $user) {
    echo $user->posts->count(); // Query a cada iteração
}

// ✅ Usar withCount
User::withCount('posts')->get();
```

**Migrations:**
```bash
create_users_table
add_status_to_orders_table
drop_legacy_users_table
```

**Helper Scripts:**
```bash
scripts/linter-formatter.sh --help
```

---

## 5. **product-management**

### O que faz
Skill de orquestração OBRIGATÓRIA para QUALQUER mudança de código. Roteia requisições pelo workflow correto (trivial→coder, complexo→feature-refiner→coder→qa).

### Como usar
Automaticamente acionada quando usuário diz: implementar, adicionar, criar, construir, refatorar, ajustar, corrigir, atualizar, mudar, "produto", "PM", "spec", "feature".

### Matriz de Complexidade

| Fator            | Simples (1pt) | Médio (2pt)  | Complexo (3pt) |
|------------------|---------------|--------------|----------------|
| Arquivos         | 1-2           | 3-5          | 6+             |
| Dependências     | Nenhuma       | 1-2 conhecidas | Novas/desconhecidas |
| Banco de dados   | Nenhum        | Adicionar colunas | Novas tabelas |
| APIs externas    | Nenhuma       | Existente    | Nova           |
| Lógica de negócio| CRUD          | Algumas regras | Regras complexas |
| Nível de risco   | Baixo         | Médio        | Alto           |

**Score:**
- **< 6**: Trivial → Delegar imediatamente ao coder
- **6-8**: Simples → Coder apenas
- **9-12**: Médio → Coder → QA
- **13-18**: Complexo → Feature-Refiner → Coder → QA

### Exemplo de uso

**Requisição trivial:**
> "Corrigir typo no título da página"
→ Score: 2 → Delegar direto ao coder

**Requisição complexa:**
> "Implementar sistema de autenticação com 2FA"
→ Score: 16 → Feature-Refiner → Criar spec → Coder → QA

### Formato da Spec
Criar em `specs/[feature].md` com:
- Context
- Complexity Assessment (sempre com score)
- User Story (As X, I want Y, So that Z)
- MVP Scope
- Acceptance Criteria (formato BDD)
- Technical Notes
- Implementation Plan

---

## 6. **python-fastapi-ai**

### O que faz
Padrões Python FastAPI, migrações Alembic, Pydantic v2 e AI Engineering (padrões raw, LangChain, Google ADK).

### Como usar
Use quando trabalhar com APIs Python, migrações de banco de dados ou aplicações AI/LLM.

### Estrutura do projeto
```
app/
├── core/ (config, security, deps)
├── models/ (SQLAlchemy models)
├── schemas/ (Pydantic schemas)
├── api/v1/ (endpoints, router)
├── services/ (business logic)
├── repositories/ (data access)
└── main.py
```

### Exemplos

**Async Best Practices:**
```python
# ✅ Async para I/O-bound
@router.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    return await user_service.get_user(db, user_id)

# ✅ Sync para CPU-bound
@router.post("/calculate")
def calculate_complex(data: CalculationInput):
    return perform_heavy_calculation(data)
```

**Service Layer:**
```python
# ❌ NUNCA nomear métodos como 'list'
class UserService:
    def list(self): ...  # Quebra type hints list[Model]

# ✅ Usar list_all, find_all, ou get_all
class UserService:
    def list_all(self) -> list[User]: ...
```

**Pydantic v2:**
```python
from pydantic import BaseModel, Field, field_validator

class UserCreate(BaseModel):
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    age: int = Field(..., gt=0, lt=150)

    @field_validator('email')
    def validate_email(cls, v):
        if not v.endswith('@company.com'):
            raise ValueError('Must be company email')
        return v
```

**AI Patterns:**
```python
# RAG básico
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings

vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings())
results = vectorstore.similarity_search(query, k=3)
```

**Helper Scripts:**
```bash
scripts/linter-formatter.sh --help
```

---

## 7. **react-best-practices**

### O que faz
Padrões modernos React 18+ com TypeScript, hooks, gerenciamento de estado e otimização de performance para Vite SPAs.

### Como usar
Use quando construir componentes React, debugar problemas frontend ou revisar código React.

### Práticas Críticas

**1. Eliminar Waterfalls:**
```typescript
// ❌ Evitar - Sequential (lento)
const user = await fetchUser();
const posts = await fetchPosts(user.id);

// ✅ Usar Promise.all()
const [user, posts] = await Promise.all([
  fetchUser(),
  fetchPosts()
]);
```

**2. Evitar Barrel Imports:**
```typescript
// ❌ Evitar
import { Button, Input, Card } from './components';

// ✅ Import direto
import { Button } from './components/Button';
import { Input } from './components/Input';
```

**3. Composição sobre Props:**
```typescript
// ❌ Evitar boolean props
<Modal showHeader showFooter />

// ✅ Usar composição
<Modal>
  <Modal.Header>Title</Modal.Header>
  <Modal.Body>Content</Modal.Body>
  <Modal.Footer>Actions</Modal.Footer>
</Modal>
```

**4. Derivar Estado no Render:**
```typescript
// ❌ Evitar estado derivado desnecessário
const [count, setCount] = useState(0);
const [isEven, setIsEven] = useState(false);

useEffect(() => {
  setIsEven(count % 2 === 0);
}, [count]);

// ✅ Derivar durante o render
const [count, setCount] = useState(0);
const isEven = count % 2 === 0;
```

**5. Keys para Resetar:**
```typescript
// Forçar unmount/remount para resetar estado
<UserProfile key={userId} userId={userId} />
```

### Performance

```typescript
// Code-splitting
const Dashboard = lazy(() => import('./Dashboard'));

function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Dashboard />
    </Suspense>
  );
}

// Memoização
const expensiveValue = useMemo(() => {
  return computeExpensiveValue(data);
}, [data]);

// Memo em componentes
const MemoizedComponent = React.memo(ExpensiveComponent);
```

### Gerenciamento de Estado
Hierarquia: Local → Lifted → Context → External (Zustand/Jotai)

```typescript
// Local state
const [count, setCount] = useState(0);

// Context para dados compartilhados
const ThemeContext = createContext<Theme | null>(null);

// External para estado global complexo
import { create } from 'zustand';

const useStore = create((set) => ({
  count: 0,
  increment: () => set((state) => ({ count: state.count + 1 }))
}));
```

---

## Referência Rápida

| Skill | Propósito | Acionada por | Output principal |
|-------|-----------|--------------|------------------|
| **atomic-commits** | Commits semânticos | Commits de código | Mensagens Conventional Commits |
| **code-review** | Verificação de qualidade | "Review PR #X" | Issues de segurança/padrões |
| **jira-searcher** | Info de epics/tasks | "Implementar PROJ-123" | Detalhes Jira |
| **laravel-patterns** | Guia PHP/Laravel | Código Laravel | Padrões, segurança, boas práticas |
| **product-management** | Orquestração de workflow | QUALQUER requisição de código | Specs, score, roteamento |
| **python-fastapi-ai** | Guia Python/AI | Trabalho FastAPI Python | Arquitetura, async, padrões AI |
| **react-best-practices** | Guia React | Trabalho com componentes React | Hooks, estado, performance |

---

## Localização dos Arquivos

Todos os arquivos estão localizados em `/Users/paulovictor237/.claude/skills-henrrique/` com cada skill em seu próprio diretório contendo `SKILL.md` e arquivos de documentação de suporte.

### Estrutura de Diretórios
```
skills-henrrique/
├── atomic-commits/
│   ├── SKILL.md
│   ├── CONVENTIONS.md
│   └── EXAMPLES.md
├── code-review/
│   └── SKILL.md
├── jira-searcher/
│   └── SKILL.md
├── laravel-patterns/
│   └── SKILL.md
├── product-management/
│   ├── SKILL.md
│   ├── EXAMPLES.md
│   └── SPECIFICATION-FORMAT.md
├── python-fastapi-ai/
│   └── SKILL.md
└── react-best-practices/
    └── SKILL.md
```

---

**Última atualização:** 2026-02-09
