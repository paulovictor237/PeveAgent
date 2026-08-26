---
name: frontend-review
description: "Code review for frontend code (TypeScript/React) against Front-End Guild standards — code quality, security, performance, and architecture. Use with a file path, commit hash, or --full to diff against the base branch. Ex: /frontend-review src/components/Modal.tsx or /frontend-review --full"
user-invocable: true
allowed-tools: Read, Bash, Grep, Glob
argument-hint: "[file-path] | [commit-hash] | --full"
---

# Frontend code review

## Usage

```
/frontend-review <file-path> | <commit-hash> | --full
```

No argument behaves like `--full`.

## 1. Resolve the scope

- **File path** (argument is an existing file) → review that file.
- **Commit hash** (argument resolves via `git cat-file -e <arg>^{commit}`) → review the files that commit touched.
- **`--full` or no argument** → review every `.ts`/`.tsx`/`.js`/`.jsx` file changed vs the base branch.

```bash
git status --porcelain
git branch --show-current
MAIN_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
```

Resolve `FILES_TO_REVIEW` per the matched case:

```bash
FILES_TO_REVIEW="$ARGUMENTS"                                                          # file path
FILES_TO_REVIEW=$(git diff-tree --no-commit-id --name-only -r "$ARGUMENTS")           # commit hash
FILES_TO_REVIEW=$(git diff --name-only "$MAIN_BRANCH"...HEAD | grep -E '\.(tsx?|jsx?)$')  # --full / no args
```

For each file in `FILES_TO_REVIEW`: read the full file, then diff it against the base (`git diff "$MAIN_BRANCH"...HEAD -- <file>`, or the commit diff for the commit-hash case) to see what actually changed — feedback only covers what was read.

## 2. Review against the checklist

Following the Front-End Guild standards:

#### File structure & naming

- **Folders**: `kebab-case` (`user-profile/`, not `UserProfile/` or `user_profile/`).
- **Component files**: explicit names (`Modal.tsx`, `Button.tsx`), not `index.tsx` as the main file — it hinders navigation. Complex components live in a folder (`modal/Modal.tsx`, `modal/ModalHeader.tsx`); `index.ts` only for barrel re-exports.
- **Types**: colocated in the component file that uses them (`export type { ComponentProps }`); a separate `types.ts` only for types shared across multiple components.
- **Naming**: state/functions `camelCase` (`isLoading`, `fetchUserData`); event handlers `handle*`/`on*` (`handleClick`/`onClick`); components `PascalCase`.

#### Component architecture

- **Size**: components ≤250 LOC; past that, extract hooks or subcomponents.
- **Custom hooks**: extract functions over ~15-20 lines and repeated `useEffect`+`useState` combinations (data fetching, form handling, click-outside detection, viewport size, localStorage, toggle/modal state, timers, debounce).
- **Hook composition**: don't call a custom hook inside another custom hook — compose them at the component level instead. Only exception is a hook explicitly designed for composition, and it must document that.
- **Reusable components**: repeated UI patterns (button variants, labeled/validated inputs, cards, modals, loaders, alerts, list items) should become a typed, prop-driven component instead of being copy-pasted.
- **Repetitive JSX**: hardcoded repetitive blocks should become an array of objects rendered with `.map()`.
- **Vanilla JS**: pure functions with no hooks/JSX (date formatting, validation, calculations) belong in `utils/`, not inside the component file.
- **Config**: API endpoints and router paths live in `config/api.ts` / `config/routes.ts` (or equivalent), not inlined at the call site.

#### TypeScript

- No `// @ts-ignore`, `any`, or `as any` — fix the underlying type instead.
- `type`, not `interface`, for component props.
- Enums use the constant-object pattern, not TS `enum`:
  ```tsx
  const DOCUMENT_KIND_ENUM = { IMAGE: "IMAGE", DIGITAL: "DIGITAL" } as const;
  type DocumentKind = (typeof DOCUMENT_KIND_ENUM)[keyof typeof DOCUMENT_KIND_ENUM];
  ```
- Event handlers typed (`React.ChangeEvent<HTMLInputElement>`), utility types (`Partial`, `Pick`, `Omit`) used where they fit, explicit return types when not obvious, `useState<Type>` and custom-hook return values typed.

#### React patterns

- **Early return**: return early for error/edge cases instead of nesting; with `useQuery`, check in order `isPending` → `isError` → `!data`.
- **Props/params**: ≥2 parameters must be a typed, destructured object — never positional.
- **Hooks**: always destructure a hook's return value.
- **Lists**: every `.map()` item has a stable, unique `key`; `useEffect` dependency arrays are correct.
- **React Query**: `useQuery` only for reads (destructure `data`/`isPending`/`isError`; never `enabled: false` + manual `refetch` to fake a write). `useMutation` for all writes, invalidating related queries in `onSuccess` and handling `onError`.

#### Styling

- Avoid inline `style={{ }}` except for genuinely dynamic values (`width: `${progress}%``); static styling goes through Tailwind.
- Tailwind: use `size-*` instead of matching `w-*`/`h-*` (`size-4` not `w-4 h-4`).
- React Native: never `RFValue` for responsive sizing — it produces inconsistent UI across devices. Use fixed design-system tokens instead.

#### Accessibility & semantics

- Semantic HTML5 over `<div>` soup: `<header>`, `<nav>`, `<main>`, `<button>` for clickable elements, `<form>` for forms.
- `<img>` has `alt`; ARIA labels and keyboard navigation present where interaction requires them.

#### Security

- No XSS/injection vectors, no hardcoded secrets/API keys/passwords.
- Authentication and authorization logic checked; user input validated and sanitized.

#### Performance

- Bottlenecks, memory leaks, unnecessary re-renders; `React.memo`/`useMemo`/`useCallback` where they'd actually help (not reflexively).
- Bundle-size impact of new dependencies.

#### Testing

- Coverage for new methods/features and their edge cases; factories/fixtures used where the test needs one.

#### Documentation & constants

- TODOs carry a task reference: `// TODO: [description] - [TASK-123]` — not `// TODO: fix this`.
- Time/byte/percentage values use declarative constants from `constants/units.ts` (`5 * ONE_SECOND`), never bare numbers whose unit isn't obvious.
- Backend communication uses `snake_case` on the wire; transform to `camelCase` on receipt and back to `snake_case` before sending — never send `camelCase` to the backend.

## 3. Report

> **Mandatory rule:** every suggestion, critical issue, or caveat opens with `### path/to/file.tsx:line — title`, naming the file (and line, when possible) — including points outside the reviewed set (a shared hook, a design-system token) if they're relevant, citing the file they come from. No review point without a file.

When a security or bug point competes for attention with a style point, give the security/bug point priority.

Structure the review like this:

````markdown
## 📋 Review Summary

**Scope**: [file / commit / branch diff]
**Files reviewed**: [number]

## ✅ Strengths

- [What's well implemented]

## ⚠️ Suggestions

### [file:line] — [suggestion title]

**Issue**: [description]

**Suggestion**:

```tsx
// suggested code
```

**Reason**: [justification]

## 🔴 Critical Issues (if any)

### [file:line] — [issue title]

**Issue**: [issue description]
**Impact**: [the risk]
**Required fix**: [what needs to be fixed]

## 📊 Checklist

- [x] File structure & naming
- [x] Component architecture
- [ ] TypeScript (pending)
- [x] Security

## 🎯 Verdict

- [ ] ✅ **Approved** — ready to merge
- [ ] 🔄 **Approved with caveats** — can merge, but consider the suggestions
- [ ] ⏳ **Changes requested** — needs adjustments before merge
- [ ] 🚫 **Blocked** — critical issues preventing merge
````
