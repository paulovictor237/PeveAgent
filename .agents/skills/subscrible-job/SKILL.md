---
name: subscrible-job
description: Especialista em preencher formulários de candidatura a vagas de emprego. Use quando o usuário quiser se inscrever em uma vaga, preencher um formulário de candidatura, ou aplicar para uma posição. Exemplos: "me inscreve nessa vaga", "preenche o formulário da vaga", "aplica pra essa posição".
---

# subscrible-job

Skill especialista em preencher formulários de candidatura a vagas de emprego via automação Playwright.

## Regras Hard — leia antes de qualquer ação

1. **NUNCA clique em submit / enviar / finalizar / candidatar / apply**
2. **NUNCA invente dados** — use exclusivamente o que está em `profile.json`
3. **SEMPRE persista** no `profile.json` qualquer dado novo fornecido pelo usuário durante o preenchimento
4. **SEMPRE pause** quando encontrar campo de cover letter e peça o texto ao usuário
5. **SEMPRE faça upload** do `Profile.pdf` quando encontrar campo de upload de arquivo

## Ferramentas e Runtime

- **Runtime:** `bun` (TypeScript nativo, sem compilação)
- **Biblioteca:** `playwright` (instalar via `bun add playwright` em `/tmp/subscrible-job/` na primeira execução)
- **Scripts:** escritos em `.ts`, salvos em `/tmp/subscrible-job/`

## Inicialização

Execute este checklist antes de abrir o browser:

1. Leia `.agents/skills/subscrible-job/assets/profile.json` e carregue todos os dados em memória
2. Confirme que `.agents/skills/subscrible-job/assets/Profile.pdf` existe
3. Garanta que o Playwright está instalado:
   ```bash
   mkdir -p /tmp/subscrible-job && cd /tmp/subscrible-job && bun add playwright 2>/dev/null || true
   ```
4. Se a URL da vaga foi fornecida como argumento, use-a; caso contrário, pergunte ao usuário
5. Inicie pela Fase 1 (Inspeção)

**Caminho absoluto do profile:** `.agents/skills/subscrible-job/assets/profile.json`
**Caminho absoluto do PDF:** `<working-dir>/.agents/skills/subscrible-job/assets/Profile.pdf`

## Fase 1 — Inspeção

Escreva `/tmp/subscrible-job/inspect.ts` com o template abaixo, substituindo `URL_DA_VAGA`:

```typescript
import { chromium } from "playwright";

const url = "URL_DA_VAGA";

const browser = await chromium.launch({ headless: false });
const page = await browser.newPage();
await page.goto(url);
await page.waitForLoadState("networkidle");

const fields = await page.evaluate(() => {
  const results: object[] = [];
  const els = document.querySelectorAll("input, select, textarea");

  els.forEach((el) => {
    const input = el as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
    const id = input.id;

    let label = "";
    if (id) {
      const labelEl = document.querySelector(`label[for="${id}"]`);
      if (labelEl) label = labelEl.textContent?.trim() ?? "";
    }
    if (!label) {
      const parent = input.closest("label, [class*='field'], [class*='form-group'], [class*='input-wrapper']");
      if (parent) {
        const clone = parent.cloneNode(true) as Element;
        clone.querySelectorAll("input, select, textarea").forEach((e) => e.remove());
        label = clone.textContent?.trim() ?? "";
      }
    }

    const options: string[] = [];
    if (input.tagName === "SELECT") {
      Array.from((input as HTMLSelectElement).options).forEach((o) => {
        if (o.value) options.push(o.text.trim());
      });
    }

    results.push({
      tag: input.tagName.toLowerCase(),
      type: (input as HTMLInputElement).type ?? "",
      name: input.name,
      id,
      label,
      placeholder: (input as HTMLInputElement).placeholder ?? "",
      ariaLabel: input.getAttribute("aria-label") ?? "",
      required: input.hasAttribute("required") || input.getAttribute("aria-required") === "true",
      options,
    });
  });

  return results;
});

console.log(JSON.stringify(fields, null, 2));
console.log("\n--- Pressione Enter para fechar o browser ---");
await new Promise((r) => process.stdin.once("data", r));
await browser.close();
```

Execute:
```bash
cd /tmp/subscrible-job && bun inspect.ts
```

Analise o JSON retornado e siga para o Mapeamento.

## Mapeamento de Campos → profile.json

Para cada campo inspecionado, normalize o texto (`label + placeholder + ariaLabel + name`) removendo acentos, convertendo para minúsculas e removendo pontuação. Verifique se contém alguma das palavras-chave:

| Palavras-chave | Valor a usar |
|---|---|
| nome, name, first name, primeiro nome | `name` — primeira palavra |
| sobrenome, last name, último nome, surname | `name` — palavras restantes |
| email, e-mail, correio | `email` |
| telefone, celular, phone, whatsapp, fone, tel | `phone` |
| cpf | `cpf` |
| nascimento, birth, data de nasc, aniversario | `birth_date` → "25/10/1992" |
| linkedin | `linkedin` |
| github, portfolio, portfólio | `github` |
| cidade, city, municipio | `address.city` → "Joinville" |
| estado, state, uf | `address.state_abbr` → "SC" (ou `address.state` conforme contexto) |
| cep, zip, postal | verificar `extra_fields.cep`; se ausente, perguntar ao usuário |
| endereço, rua, street, logradouro | `address.street` + ", " + `address.number` |
| número, number, num | `address.number` → "610" |
| bairro, neighborhood, district | verificar `extra_fields.bairro`; se ausente, perguntar ao usuário |
| pais, country, nação | `address.country` → "Brasil" |
| cargo atual, posição atual, current role, titulo | `current_role` |
| salário, pretensão, remuneração, expectativa salarial | "PJ: R$ 18.000 ~ R$ 21.000 / CLT: R$ 14.000 ~ R$ 16.000" |
| contrato, regime, pj, clt, tipo de contrato | `job_preferences.primary.contract` → "PJ" |
| modalidade, modelo, remoto, híbrido, presencial | `job_preferences.primary.modality` → "Remoto" |
| disponibilidade, inicio, quando pode começar | "1 mês" |
| viagem, travel, disponível para viagens | "Não" |
| mudança, relocate, disponível para mudança | "Não" |
| pcd, deficiência, disability, portador | "Não" |
| gênero, gender, sexo | `gender` → "Masculino" |
| pronome | `pronoun` → "Ele/Dele" |
| raça, etnia, cor, race | `ethnicity` → "Branca" |
| como soube, source, indicação, canal | `job_preferences.job_source` → "Google" |
| carta, cover letter, apresentação, motivação | **PAUSA** — veja seção Cover Letter |
| currículo, cv, resume, arquivo, upload | **UPLOAD** — veja seção Upload |
| idioma, língua, language | "Inglês (Professional Working), Português (Nativo)" |
| sobre você, resumo, summary, apresentação pessoal | `summary` |
| habilidades, skills, competências, tecnologias | "Liderança, React Native, Tailwind CSS" |
| formação, escolaridade, graduação, education | "Bacharelado em Mecatrônica — UFSC (2020)" |
| experiência, anos de experiência, tempo de experiência | "3 anos 9 meses na Motorista PX como Tech Lead" |

Inclua também as chaves de `extra_fields` (se existirem no `profile.json`) como palavras-chave adicionais.

### Campos sem mapeamento

- Se `required`: avise o usuário, aguarde resposta, salve em `extra_fields` do `profile.json`
- Se opcional: deixe em branco, registre no relatório final

## Fase 2 — Preenchimento

Após mapear todos os campos (e coletar cover letter / campos desconhecidos do usuário), escreva `/tmp/subscrible-job/fill.ts` com o template abaixo. Preencha `URL_DA_VAGA` e a lista `actions` com os dados mapeados:

```typescript
import { chromium, Page } from "playwright";
import * as readline from "readline";

const url = "URL_DA_VAGA";

type Action =
  | { type: "fill"; selector: string; value: string }
  | { type: "select"; selector: string; label: string }
  | { type: "click"; selector: string }
  | { type: "check"; selector: string }
  | { type: "upload"; selector: string; path: string }
  | { type: "date"; selector: string; value: string };

const actions: Action[] = [
  // Exemplos — substitua pelos campos reais mapeados:
  // { type: "fill", selector: 'input[name="firstName"]', value: "Paulo" },
  // { type: "select", selector: 'select[name="state"]', label: "Santa Catarina" },
  // { type: "click", selector: 'label:has-text("Masculino") input[type="radio"]' },
  // { type: "upload", selector: 'input[type="file"]', path: "/abs/path/Profile.pdf" },
  // { type: "date", selector: 'input[type="date"]', value: "1992-10-25" },
];

async function resolveSelector(page: Page, selector: string) {
  const locator = page.locator(selector).first();
  return locator;
}

const browser = await chromium.launch({ headless: false });
const page = await browser.newPage();
await page.goto(url);
await page.waitForLoadState("networkidle");

for (const action of actions) {
  const el = await resolveSelector(page, action.selector);
  await el.waitFor({ state: "visible", timeout: 5000 }).catch(() => {});

  switch (action.type) {
    case "fill":
      await el.fill(action.value);
      break;
    case "select":
      await el.selectOption({ label: action.label });
      break;
    case "click":
      await el.click();
      break;
    case "check":
      await el.check();
      break;
    case "upload":
      await el.setInputFiles(action.path);
      break;
    case "date":
      await el.fill(action.value);
      break;
  }

  await page.waitForTimeout(200);
}

// Detectar botão de avanço (NUNCA clicar em submit)
const advanceKeywords = ["próximo", "next", "continue", "continuar", "avançar", "prosseguir", "seguinte"];
const submitKeywords = ["enviar", "submit", "finalizar", "candidatar", "aplicar", "apply", "concluir", "terminar", "send"];

const buttons = await page.locator("button, input[type='submit'], a[role='button']").all();
let advanceButton = null;
let hasSubmit = false;

for (const btn of buttons) {
  const text = (await btn.textContent() ?? "").toLowerCase().trim();
  if (submitKeywords.some((k) => text.includes(k))) hasSubmit = true;
  if (advanceKeywords.some((k) => text.includes(k))) advanceButton = btn;
}

if (advanceButton) {
  console.log("✓ Botão de avanço encontrado — clicando...");
  await advanceButton.click();
  await page.waitForLoadState("networkidle");
  console.log("✓ Avançou para o próximo step. Feche o browser e rode nova inspeção.");
} else if (hasSubmit) {
  console.log("⛔ Botão de SUBMIT detectado — NÃO foi clicado. Revise e submeta manualmente.");
} else {
  console.log("○ Nenhum botão de navegação encontrado.");
}

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
await new Promise<void>((r) => rl.question("\nRevise o formulário e pressione Enter para fechar o browser... ", () => { rl.close(); r(); }));
await browser.close();
```

Execute:
```bash
cd /tmp/subscrible-job && bun fill.ts
```

### Estratégia de seletor (cascata)

Para cada campo, tente os seletores nesta ordem até encontrar um que funcione:
1. `[name="valor"]`
2. `[id="valor"]`
3. `[aria-label*="valor"]`
4. `label:has-text("Texto do Label") input` (ou `select`, `textarea`)
5. `[placeholder*="valor"]`

Use `.first` se houver ambiguidade.

## Cover Letter

Quando detectar campo de cover letter durante o mapeamento:
1. **Pare** — não inclua na lista de actions ainda
2. Avise: "Encontrei um campo de carta de apresentação. Por favor, forneça o texto que deseja usar:"
3. Aguarde o texto do usuário
4. Inclua na action como `{ type: "fill", selector: "...", value: "texto fornecido" }`

## Upload de Arquivo (CV/Currículo)

Use o caminho absoluto do PDF:
```typescript
{ type: "upload", selector: 'input[type="file"]', path: "/abs/path/.agents/skills/subscrible-job/assets/Profile.pdf" }
```

O caminho deve ser absoluto. Substitua `/abs/path/` pelo working directory da sessão.

## Navegação Multi-Step

Após cada execução do `fill.ts`:
- Se o script clicou no botão de avanço → aguarde o usuário confirmar, então rode `inspect.ts` novamente na nova URL/estado
- Repita Fase 1 → Mapeamento → Fase 2 até não haver mais botão de avanço
- Informe o usuário: "Preenchendo step N..."

## Persistência de Novos Dados

Quando o usuário fornecer dados para campos sem mapeamento:
1. Adicione ao `profile.json` dentro de `extra_fields`:
```json
{
  "extra_fields": {
    "cep": "89201-000",
    "bairro": "América"
  }
}
```
2. Use o Write tool para salvar o arquivo atualizado

## Relatório Final

Ao finalizar todos os steps:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RELATÓRIO DE CANDIDATURA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ PREENCHIDO AUTOMATICAMENTE (N campos)
  • Nome: Paulo Victor Duarte
  • Email: paulovictor237@gmail.com
  • [... demais campos ...]

⚠ PREENCHIDO PELO USUÁRIO (N campos)
  • Cover letter: [primeiras 50 chars...]
  • [... demais campos ...]

○ DEIXADO EM BRANCO — opcional (N campos)
  • "Portfolio pessoal" (opcional)

⛔ FORMULÁRIO PAUSADO
  O botão "Enviar candidatura" foi detectado mas NÃO foi clicado.
  Revise o formulário e submeta manualmente quando estiver pronto.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
