# subscrible-job Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar o arquivo `SKILL.md` da skill `subscrible-job` que instrui o Claude a preencher formulários de candidatura a vagas usando o browser do Claude Code, baseando-se exclusivamente nos dados do `profile.json`.

**Architecture:** Skill baseada em arquivo Markdown (SKILL.md) com instruções declarativas para o Claude. Sem código executável — o Claude interpreta as instruções e usa as ferramentas de browser disponíveis no Claude Code para inspecionar e preencher formulários via JavaScript injetado.

**Tech Stack:** Claude Code browser extension, JavaScript (injetado no browser), JSON (profile.json)

---

## Estrutura de Arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `.agents/skills/subscrible-job/SKILL.md` | Criar | Instruções completas da skill para o Claude |
| `.agents/skills/subscrible-job/assets/profile.json` | Já existe | Fonte de dados do candidato |
| `.agents/skills/subscrible-job/assets/Profile.pdf` | Já existe | Currículo para upload automático |

---

## Task 1: Criar esqueleto do SKILL.md com frontmatter e trigger

**Files:**
- Create: `.agents/skills/subscrible-job/SKILL.md`

- [ ] **Step 1: Criar o arquivo com frontmatter e seção de trigger**

Criar `.agents/skills/subscrible-job/SKILL.md` com o conteúdo:

```markdown
---
name: subscrible-job
description: Especialista em preencher formulários de candidatura a vagas de emprego. Use quando o usuário quiser se inscrever em uma vaga, preencher um formulário de candidatura, ou aplicar para uma posição. Exemplos: "me inscreve nessa vaga", "preenche o formulário da vaga", "aplica pra essa posição".
---

# subscrible-job

Skill especialista em preencher formulários de candidatura a vagas de emprego.

## Regras Hard — leia antes de qualquer ação

1. **NUNCA clique em submit / enviar / finalizar / candidatar / apply**
2. **NUNCA invente dados** — use exclusivamente o que está em `profile.json`
3. **SEMPRE persista** no `profile.json` qualquer dado novo fornecido pelo usuário durante o preenchimento
4. **SEMPRE pause** quando encontrar campo de cover letter e peça o texto ao usuário
5. **SEMPRE faça upload** do `Profile.pdf` quando encontrar campo de upload de arquivo
```

- [ ] **Step 2: Commitar o esqueleto**

```bash
git add .agents/skills/subscrible-job/SKILL.md
git commit -m "feat(subscrible-job): add SKILL.md skeleton with frontmatter and hard rules"
```

---

## Task 2: Adicionar seção de carregamento do profile e inicialização

**Files:**
- Modify: `.agents/skills/subscrible-job/SKILL.md`

- [ ] **Step 1: Adicionar seção de inicialização ao SKILL.md**

Adicionar após as regras hard:

```markdown
## Inicialização

Ao ser invocada, execute este checklist antes de abrir o browser:

1. Leia o arquivo `.agents/skills/subscrible-job/assets/profile.json` e carregue todos os dados em memória
2. Confirme que o arquivo `.agents/skills/subscrible-job/assets/Profile.pdf` existe
3. Se a URL da vaga foi fornecida como argumento, abra-a no browser
4. Se não foi fornecida, pergunte ao usuário: "Qual é a URL da vaga?"
5. Aguarde o formulário renderizar completamente antes de inspecionar os campos

**Caminho absoluto do profile:** `.agents/skills/subscrible-job/assets/profile.json`
**Caminho absoluto do PDF:** `.agents/skills/subscrible-job/assets/Profile.pdf`
```

- [ ] **Step 2: Commitar**

```bash
git add .agents/skills/subscrible-job/SKILL.md
git commit -m "feat(subscrible-job): add initialization section"
```

---

## Task 3: Adicionar algoritmo de inspeção e mapeamento de campos

**Files:**
- Modify: `.agents/skills/subscrible-job/SKILL.md`

- [ ] **Step 1: Adicionar seção de inspeção de campos**

Adicionar após a seção de inicialização:

```markdown
## Inspeção de Campos

Para cada página/step do formulário, inspecione todos os elementos:
- `input` (text, email, tel, date, number, radio, checkbox, file)
- `select`
- `textarea`

Para cada elemento, colete:
- `label` associado (via `for` ou elemento pai)
- `placeholder`
- `name`
- `aria-label`
- `aria-labelledby`
- Se é `required`

Normalize o texto coletado: remova acentos, converta para minúsculas, remova pontuação.

## Mapeamento de Campos → profile.json

Use heurística por palavras-chave. Para cada campo, verifique se o texto normalizado contém alguma das palavras-chave abaixo:

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
| estado, state, uf, estado | `address.state_abbr` → "SC" (ou `address.state` conforme o contexto) |
| cep, zip, postal | perguntar ao usuário |
| endereço, rua, street, logradouro | concatenar `address.street` + ", " + `address.number` |
| número, number, num | `address.number` → "610" |
| bairro, neighborhood, district | perguntar ao usuário |
| pais, country, nação | `address.country` → "Brasil" |
| cargo atual, posição atual, current role, titulo | `current_role` |
| salário, pretensão, remuneração, expectativa salarial | formatar conforme contrato preferido: "PJ: R$ 18.000 ~ R$ 21.000 / CLT: R$ 14.000 ~ R$ 16.000" |
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
| idioma, língua, language | formatar: "Inglês (Professional Working), Português (Nativo)" |
| sobre você, resumo, summary, apresentação pessoal | `summary` |
| habilidades, skills, competências, tecnologias | juntar `skills` com vírgula: "Liderança, React Native, Tailwind CSS" |
| formação, escolaridade, graduação, education | última entrada de `education`: "Bacharelado em Mecatrônica — UFSC (2020)" |
| experiência, anos de experiência, tempo de experiência | calcular a partir de `experience`: "3 anos 9 meses na Motorista PX como Tech Lead" |
```

- [ ] **Step 2: Commitar**

```bash
git add .agents/skills/subscrible-job/SKILL.md
git commit -m "feat(subscrible-job): add field inspection and mapping table"
```

---

## Task 4: Adicionar lógica de preenchimento, cover letter e upload

**Files:**
- Modify: `.agents/skills/subscrible-job/SKILL.md`

- [ ] **Step 1: Adicionar seção de preenchimento**

Adicionar após o mapeamento:

```markdown
## Preenchimento de Campos

### Campos de texto (input text, email, tel, number, textarea)
```javascript
// Localize o elemento e preencha
const el = document.querySelector('selector');
el.focus();
el.value = 'valor';
el.dispatchEvent(new Event('input', { bubbles: true }));
el.dispatchEvent(new Event('change', { bubbles: true }));
```

### Campos select (dropdown)
```javascript
const el = document.querySelector('select[name="campo"]');
// Tente match exato primeiro, depois match parcial
const options = Array.from(el.options);
const match = options.find(o => o.text.toLowerCase().includes('valor'));
if (match) {
  el.value = match.value;
  el.dispatchEvent(new Event('change', { bubbles: true }));
}
```

### Radio buttons e checkboxes
```javascript
// Encontre o radio/checkbox cujo label contém o valor desejado
const labels = document.querySelectorAll('label');
const target = Array.from(labels).find(l => l.textContent.toLowerCase().includes('valor'));
if (target) {
  const input = target.querySelector('input') || document.getElementById(target.htmlFor);
  if (input) input.click();
}
```

### Campos de data
Formate conforme o campo pede:
- Se `type="date"` → formato `YYYY-MM-DD`: `1992-10-25`
- Se texto livre → use o formato do placeholder como referência: `25/10/1992`

## Cover Letter

Quando detectar campo de cover letter:
1. **Pare de preencher outros campos**
2. Avise o usuário: "Encontrei um campo de carta de apresentação. Por favor, forneça o texto que deseja usar:"
3. Aguarde o usuário fornecer o texto
4. Preencha o campo com o texto fornecido
5. Continue o preenchimento dos demais campos

## Upload de Arquivo (CV/Currículo)

Quando detectar campo de upload:
1. Use o caminho absoluto: `.agents/skills/subscrible-job/assets/Profile.pdf`
2. Injete o arquivo via JavaScript ou use a interação direta do browser extension
3. Aguarde o upload completar antes de continuar

## Campos Sem Mapeamento

- Se o campo tem `required` ou `aria-required="true"`:
  1. Avise o usuário: "Encontrei o campo obrigatório '[label do campo]' que não tenho dados para preencher. O que devo usar?"
  2. Aguarde a resposta
  3. Preencha com o valor fornecido
  4. Salve no `profile.json` sob uma chave descritiva em `extra_fields`

- Se o campo é opcional:
  - Deixe em branco
  - Adicione à lista de "campos deixados em branco" do relatório
```

- [ ] **Step 2: Commitar**

```bash
git add .agents/skills/subscrible-job/SKILL.md
git commit -m "feat(subscrible-job): add fill logic, cover letter and upload sections"
```

---

## Task 5: Adicionar lógica de navegação multi-step

**Files:**
- Modify: `.agents/skills/subscrible-job/SKILL.md`

- [ ] **Step 1: Adicionar seção de navegação**

Adicionar após a seção de preenchimento:

```markdown
## Navegação Multi-Step

Após preencher todos os campos visíveis na página atual:

### 1. Detectar tipo de botão disponível

Execute este JavaScript para identificar os botões:
```javascript
const buttons = Array.from(document.querySelectorAll('button, input[type="submit"], a[role="button"]'));
const labels = buttons.map(b => ({ text: b.textContent.trim().toLowerCase(), el: b }));
```

### 2. Classificar botões

**Botões de AVANÇO** (clique nestes):
- Texto contém: `próximo`, `next`, `continue`, `continuar`, `avançar`, `prosseguir`, `seguinte`, `›`, `→`

**Botões de SUBMIT** (NUNCA clique):
- Texto contém: `enviar`, `submit`, `finalizar`, `candidatar`, `aplicar`, `apply`, `concluir`, `terminar`, `send`

### 3. Ação

- Se encontrou botão de AVANÇO → clique, aguarde a próxima página carregar, repita o processo de inspeção e preenchimento
- Se encontrou APENAS botão de SUBMIT → **não clique**, siga para o relatório final
- Se não encontrou nenhum botão → siga para o relatório final

### 4. Indicador de progresso

Informe o usuário a cada step: "Preenchendo step 2 de N..." (se o formulário indicar o total de steps)
```

- [ ] **Step 2: Commitar**

```bash
git add .agents/skills/subscrible-job/SKILL.md
git commit -m "feat(subscrible-job): add multi-step navigation logic"
```

---

## Task 6: Adicionar persistência de dados e relatório final

**Files:**
- Modify: `.agents/skills/subscrible-job/SKILL.md`

- [ ] **Step 1: Adicionar seção de persistência**

Adicionar após a navegação:

```markdown
## Persistência de Novos Dados

Quando o usuário fornecer dados para campos obrigatórios sem mapeamento:

1. Identifique uma chave descritiva para o dado (ex: `cep`, `bairro`, `portfolio_url`)
2. Adicione ao `profile.json` dentro de um objeto `extra_fields`:

```json
{
  "extra_fields": {
    "cep": "89201-000",
    "bairro": "América"
  }
}
```

3. Use o Write tool para salvar o arquivo atualizado
4. Na próxima candidatura, inclua `extra_fields` nas verificações de mapeamento

## Relatório Final

Ao finalizar o preenchimento de todos os steps, exiba:

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
  • [... demais campos ...]

⛔ FORMULÁRIO PAUSADO
  O botão "Enviar candidatura" foi detectado mas NÃO foi clicado.
  Revise o formulário e submeta manualmente quando estiver pronto.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Campos Adicionais no profile.json (extra_fields)

Ao inicializar, verifique se existe `extra_fields` no `profile.json` e inclua esses dados no mapeamento, usando o nome da chave como palavra-chave de busca.
```

- [ ] **Step 2: Commitar**

```bash
git add .agents/skills/subscrible-job/SKILL.md
git commit -m "feat(subscrible-job): add persistence and final report sections"
```

---

## Task 7: Verificação manual da skill

**Files:**
- Read: `.agents/skills/subscrible-job/SKILL.md` (verificação final)

- [ ] **Step 1: Verificar cobertura do spec**

Leia o spec em `docs/superpowers/specs/2026-04-16-subscrible-job-design.md` e confirme que cada requisito tem cobertura no SKILL.md:

| Requisito | Coberto em |
|---|---|
| Carrega profile.json | Task 2 — Inicialização |
| Abre URL no browser | Task 2 — Inicialização |
| Inspeciona campos | Task 3 — Inspeção |
| Mapeia campos → profile | Task 3 — Mapeamento |
| Preenche via JavaScript | Task 4 — Preenchimento |
| Cover letter → pausa/pede | Task 4 — Cover Letter |
| Upload Profile.pdf | Task 4 — Upload |
| Campo obrigatório sem mapa → pede usuário | Task 4 — Campos Sem Mapeamento |
| Campo opcional sem mapa → deixa vazio | Task 4 — Campos Sem Mapeamento |
| Multi-step → clica Próximo | Task 5 — Navegação |
| Nunca clica Submit | Task 5 — Navegação |
| Persiste dados novos | Task 6 — Persistência |
| Relatório final | Task 6 — Relatório |

- [ ] **Step 2: Commitar versão final**

```bash
git add .agents/skills/subscrible-job/SKILL.md
git commit -m "feat(subscrible-job): skill complete and verified"
```
