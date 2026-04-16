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

## Inicialização

Ao ser invocada, execute este checklist antes de abrir o browser:

1. Leia o arquivo `.agents/skills/subscrible-job/assets/profile.json` e carregue todos os dados em memória
2. Confirme que o arquivo `.agents/skills/subscrible-job/assets/Profile.pdf` existe
3. Se a URL da vaga foi fornecida como argumento, abra-a no browser
4. Se não foi fornecida, pergunte ao usuário: "Qual é a URL da vaga?"
5. Aguarde o formulário renderizar completamente antes de inspecionar os campos

**Caminho absoluto do profile:** `.agents/skills/subscrible-job/assets/profile.json`
**Caminho absoluto do PDF:** `.agents/skills/subscrible-job/assets/Profile.pdf`

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
| estado, state, uf | `address.state_abbr` → "SC" (ou `address.state` conforme o contexto) |
| cep, zip, postal | perguntar ao usuário |
| endereço, rua, street, logradouro | concatenar `address.street` + ", " + `address.number` |
| número, number, num | `address.number` → "610" |
| bairro, neighborhood, district | perguntar ao usuário |
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

## Preenchimento de Campos

### Campos de texto (input text, email, tel, number, textarea)

```javascript
const el = document.querySelector('selector');
el.focus();
el.value = 'valor';
el.dispatchEvent(new Event('input', { bubbles: true }));
el.dispatchEvent(new Event('change', { bubbles: true }));
```

### Campos select (dropdown)

```javascript
const el = document.querySelector('select[name="campo"]');
const options = Array.from(el.options);
const match = options.find(o => o.text.toLowerCase().includes('valor'));
if (match) {
  el.value = match.value;
  el.dispatchEvent(new Event('change', { bubbles: true }));
}
```

### Radio buttons e checkboxes

```javascript
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

## Navegação Multi-Step

Após preencher todos os campos visíveis na página atual:

### 1. Detectar tipo de botão disponível

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

Informe o usuário a cada step: "Preenchendo step N..." (se o formulário indicar o total de steps)

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
