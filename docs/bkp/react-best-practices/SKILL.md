---
name: react-best-practices
description: Modern React 18+ patterns with TypeScript, hooks, state management, and performance optimization. Use when building React components, debugging frontend issues, or reviewing React code.
allowed-tools: Read, Grep, Glob
---

# React Best Practices Skill (Vite + React SPA)

Guia de boas práticas React otimizado para consumo por agentes de IA.
Stack: **React + Vite** (SPA, sem SSR/Server Components).

---

## 1. Práticas Críticas (Alto Impacto)

### Eliminar Waterfalls com Promise.all

Nunca use `await` sequencial quando as chamadas não dependem uma da outra.

```tsx
// ❌ Ruim — execução sequencial desnecessária
const user = await fetchUser(id);
const posts = await fetchPosts(id);

// ✅ Bom — execução paralela
const [user, posts] = await Promise.all([
  fetchUser(id),
  fetchPosts(id),
]);
```

### Evitar Barrel Imports

Não crie arquivos `index.ts` que reexportam tudo de uma pasta. Isso prejudica o tree shaking do Vite e aumenta o bundle.

```tsx
// ❌ Ruim — importa tudo do barrel
import { Button } from "@/components";

// ✅ Bom — importação direta
import { Button } from "@/components/Button";
```

### Composição ao invés de Props Booleanas

Divida componentes grandes com muitas props de configuração em microcomponentes combináveis.

```tsx
// ❌ Ruim — componente inchado com flags
<Card showHeader showFooter variant="primary" />

// ✅ Bom — composição explícita
<Card>
  <Card.Header />
  ...
  <Card.Footer>
    <Button>Ação</Button>
  </Card.Footer>
</Card>
```

### Compound Components com Context

Quando microcomponentes precisam compartilhar estado, use Context interno ao compound component.

```tsx
const CardContext = createContext(null);

function useCardContext() {
  const ctx = useContext(CardContext);
  if (!ctx) throw new Error("Card.* deve ser usado dentro de <Card>");
  return ctx;
}

function Card({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <CardContext.Provider value={{ open, setOpen }}>
      {children}
    </CardContext.Provider>
  );
}

Card.Toggle = function Toggle() {
  const { open, setOpen } = useCardContext();
  return <button onClick={() => setOpen(!open)}>Toggle</button>;
};

Card.Content = function Content({ children }: { children: ReactNode }) {
  const { open } = useCardContext();
  return open ? <div>{children}</div> : null;
};
```

### Keys para Resetar Estado de Componentes

Use a prop `key` para forçar o React a desmontar e remontar um componente, resetando todo seu estado interno.

```tsx
// ✅ Ao mudar o userId, o componente é recriado do zero
<UserProfile key={userId} userId={userId} />
```

---

## 2. Lógica de Estado e Renderização

### Calcular Estado Derivado durante o Render

Nunca crie `useState` + `useEffect` para dados que podem ser calculados a partir de estado existente. Derive direto no corpo do componente.

```tsx
// ❌ Ruim — estado + effect desnecessários
const [filtered, setFiltered] = useState([]);
useEffect(() => {
  setFiltered(items.filter((i) => i.active));
}, [items]);

// ✅ Bom — variável derivada
const filtered = items.filter((i) => i.active);
```

Para cálculos pesados, use `useMemo`:

```tsx
const filtered = useMemo(
  () => items.filter((i) => i.active),
  [items],
);
```

### Evitar Estado Redundante com Booleanos Derivados

Se um booleano pode ser calculado a partir de outro estado, não crie um novo `useState`.

```tsx
// ❌ Ruim — estado duplicado
const [query, setQuery] = useState("");
const [hasMinLength, setHasMinLength] = useState(false);

useEffect(() => {
  setHasMinLength(query.length >= 3);
}, [query]);

// ✅ Bom — derivado direto
const [query, setQuery] = useState("");
const hasMinLength = query.length >= 3;
```

### Valores Default não Primitivos fora do Componente

Defina objetos, arrays e funções padrão fora do componente para manter referências estáveis e não quebrar memoização.

```tsx
// ❌ Ruim — nova referência a cada render
function List({ filters = {} }) { ... }

// ✅ Bom — referência estável
const DEFAULT_FILTERS = {};
function List({ filters = DEFAULT_FILTERS }) { ... }
```

### useReducer para Estado Complexo

Quando o estado tem múltiplos campos interdependentes, prefira `useReducer` a múltiplos `useState`.

```tsx
type State = { count: number; step: number };
type Action = { type: "increment" } | { type: "setStep"; payload: number };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "increment":
      return { ...state, count: state.count + state.step };
    case "setStep":
      return { ...state, step: action.payload };
  }
}

const [state, dispatch] = useReducer(reducer, { count: 0, step: 1 });
```

### useState

- Use functional updates for derived state: `setCount(c => c + 1)`
- Prefer multiple states over one object
- Initialize expensive state with function: `useState(() => computeExpensive())`

### useEffect

- One effect per concern
- Always include cleanup when needed
- Avoid objects in dependency arrays (use primitives)

```tsx
useEffect(() => {
  const handler = () => setWidth(window.innerWidth);
  window.addEventListener("resize", handler);
  return () => window.removeEventListener("resize", handler);
}, []);
```

### Custom Hooks

- Extract reusable logic into `use`-prefixed functions
- Return tuple or object consistently

```tsx
function useLocalStorage<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : initial;
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);

  return [value, setValue] as const;
}
```

---

## 3. Performance e Arquitetura

### Lazy Loading com React.lazy + Suspense

No Vite, use `React.lazy` para code-splitting de componentes pesados.

```tsx
import { lazy, Suspense } from "react";

const HeavyChart = lazy(() => import("@/components/HeavyChart"));

function Dashboard() {
  return (
    <Suspense fallback={<Spinner />}>
      <HeavyChart />
    </Suspense>
  );
}
```

### Múltiplas Suspense Boundaries

Divida a UI em várias fronteiras de Suspense para que cada seção carregue de forma independente.

```tsx
function Page() {
  return (
    <main>
      <Suspense fallback={<HeaderSkeleton />}>
        <Header />
      </Suspense>
      <Suspense fallback={<ContentSkeleton />}>
        <Content />
      </Suspense>
      <Suspense fallback={<SidebarSkeleton />}>
        <Sidebar />
      </Suspense>
    </main>
  );
}
```

### Composição com children para Evitar Prop Drilling

Antes de recorrer ao Context, tente resolver prop drilling passando componentes como `children`.

```tsx
// ❌ Ruim — prop drilling por 3 níveis
<Layout user={user}>
  <Sidebar user={user}>
    <Avatar user={user} />
  </Sidebar>
</Layout>

// ✅ Bom — composição com children
<Layout>
  <Sidebar>
    <Avatar user={user} />
  </Sidebar>
</Layout>
```

### State Management Hierarchy (prefer top to bottom)

1. **Local state** - Component-specific
2. **Lifted state** - Shared between siblings
3. **Context** - Cross-cutting (theme, auth, i18n, feature flags)
4. **External store** - Complex global state (Zustand, Jotai)

### Zustand Pattern

```tsx
const useStore = create<State>((set) => ({
  items: [],
  addItem: (item) => set((s) => ({ items: [...s.items, item] })),
  removeItem: (id) =>
    set((s) => ({
      items: s.items.filter((i) => i.id !== id),
    })),
}));
```

### Set e Map para Lookups Rápidos

Use `Set` e `Map` para buscas frequentes em vez de arrays.

```tsx
// ❌ Ruim — O(n) a cada verificação
const isSelected = selectedIds.includes(id);

// ✅ Bom — O(1)
const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);
const isSelected = selectedSet.has(id);
```

### React.memo

- Wrap components receiving same props repeatedly
- Combine with useCallback for function props
- Don't use everywhere (adds overhead)

### Adiar Scripts de Terceiros

Carregue scripts de analytics, chat widgets ou login social de forma assíncrona e após o carregamento inicial.

```tsx
useEffect(() => {
  const script = document.createElement("script");
  script.src = "https://analytics.example.com/script.js";
  script.async = true;
  document.body.appendChild(script);
}, []);
```

---

## 4. TypeScript Patterns

### Props Types

```tsx
interface Props {
  required: string;
  optional?: number;
  children: React.ReactNode;
  onClick: (event: React.MouseEvent) => void;
  as?: React.ElementType;
}
```

### Generic Components

```tsx
interface ListProps<T> {
  items: T[];
  renderItem: (item: T) => React.ReactNode;
  keyExtractor: (item: T) => string;
}

function List<T>({ items, renderItem, keyExtractor }: ListProps<T>) {
  return (
    <ul>
      {items.map((item) => (
        <li key={keyExtractor(item)}>{renderItem(item)}</li>
      ))}
    </ul>
  );
}
```

### Functional Components Only

```tsx
interface UserCardProps {
  user: User;
  onSelect?: (user: User) => void;
}

function UserCard({ user, onSelect }: UserCardProps) {
  return (
    <article onClick={() => onSelect?.(user)}>
      <h2>{user.name}</h2>
    </article>
  );
}
```

### Props Destructuring

- Always destructure props in function signature
- Use default values: `{ size = 'md' }: Props`
- Spread remaining props: `{ className, ...rest }`

---

## 5. Testing (Vitest + Testing Library)

```tsx
import { render, screen, fireEvent } from "@testing-library/react";

describe("Button", () => {
  it("calls onClick when clicked", () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click</Button>);

    fireEvent.click(screen.getByRole("button"));

    expect(handleClick).toHaveBeenCalledOnce();
  });
});
```
