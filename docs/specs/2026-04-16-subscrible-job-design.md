# subscrible-job — Design Spec

**Data:** 2026-04-16  
**Status:** Aprovado

---

## Visão Geral

Skill especialista em preencher formulários de candidatura a vagas de emprego. Usa a browser extension do Claude Code para navegar em formulários já abertos pelo usuário (preservando sessão/login), mapeia os campos contra o `profile.json` e preenche automaticamente. Nunca submete o formulário — apenas preenche e deixa o usuário revisar e enviar.

---

## Fluxo Principal

```
1. Carrega profile.json de .agents/skills/subscrible-job/assets/profile.json
2. Recebe a URL da vaga como argumento
3. Abre a URL no browser via Claude Code browser extension
4. Aguarda o formulário renderizar
5. Inspeciona todos os campos visíveis:
   - input, select, textarea, radio, checkbox, file
6. Para cada campo:
   a. Lê label / placeholder / name / aria-label
   b. Mapeia para dado do profile.json via heurística de palavras-chave
   c. Se mapeou → preenche via JavaScript
   d. Se é cover letter → pausa, pede texto ao usuário, preenche
   e. Se é upload de arquivo → faz upload de Profile.pdf
   f. Se não mapeou + obrigatório → pausa, pede ao usuário, salva no profile.json
   g. Se não mapeou + opcional → registra na lista "ficou vazio"
7. Ao final de cada step:
   a. Detecta botão "Próximo / Next / Continue / Avançar" → clica, repete passo 4
   b. Detecta botão "Enviar / Submit / Finalizar / Candidatar" → NÃO clica
8. Exibe relatório final
```

---

## Abordagem de Navegação

- Usa Claude Code browser extension (não Playwright/Puppeteer)
- Motivo: o usuário já está logado no browser real — Gupy, LinkedIn, Greenhouse etc. A skill herda a sessão existente sem gerenciar credenciais
- Preenchimento via JavaScript injetado (`document.querySelector`, `.value =`, `.dispatchEvent`)
- Navegação multi-step: detecta e clica em botões de avanço, nunca em botões de submissão

---

## Mapeamento de Campos

Heurística por palavras-chave no `label`, `placeholder`, `name` e `aria-label` do campo:

| Palavras-chave | Dado do profile |
|---|---|
| nome, name, first name | `name` (parte 1) |
| sobrenome, last name | `name` (parte 2) |
| email, e-mail | `email` |
| telefone, celular, phone, whatsapp | `phone` |
| cpf | `cpf` |
| nascimento, birth | `birth_date` |
| linkedin | `linkedin` |
| github, portfolio | `github` |
| cidade, city | `address.city` |
| estado, state | `address.state` / `address.state_abbr` |
| endereço, rua, street | `address.street` + `address.number` |
| cargo atual, current role | `current_role` |
| salário, pretensão, remuneração | `job_preferences.primary.salary_range` |
| contrato, regime, pj, clt | `job_preferences.primary.contract` |
| modalidade, remoto, híbrido | `job_preferences.primary.modality` |
| disponibilidade, início | `job_preferences.availability_days` → "1 mês" |
| viagem, travel | `job_preferences.willing_to_travel` → "Não" |
| mudança, relocate | `job_preferences.willing_to_relocate` → "Não" |
| pcd, deficiência, disability | `pcd` → "Não" |
| gênero, gender, sexo | `gender` |
| pronome | `pronoun` |
| raça, etnia, cor | `ethnicity` |
| como soube, source | `job_preferences.job_source` |
| carta, cover letter, apresentação | pausa → pede ao usuário |
| currículo, cv, resume, arquivo | upload de `Profile.pdf` |
| idioma, língua, language | `languages` |
| sobre você, resumo, summary | `summary` |
| habilidades, skills, competências | `skills` |

**Campos sem mapeamento:**
- `required` no HTML → pausa, pede ao usuário, persiste resposta no `profile.json`
- sem `required` → registra como "ficou vazio" no relatório

---

## Persistência de Novos Dados

Quando o usuário fornece dados não existentes no `profile.json` durante o preenchimento, a skill salva automaticamente no arquivo para uso em candidaturas futuras.

---

## Relatório Final

```
✓ PREENCHIDO (N campos)
  - lista dos campos preenchidos automaticamente

⚠ PREENCHIDO PELO USUÁRIO (N campos)
  - cover letter, campos obrigatórios sem mapeamento

○ DEIXADO EM BRANCO — opcional (N campos)
  - lista dos campos opcionais sem dados

⛔ FORMULÁRIO PAUSADO — aguardando ação manual
  Botão de submit detectado mas NÃO clicado.
  Revise e submeta quando estiver pronto.
```

---

## Regras Hard

1. **Nunca clicar em submit/enviar/finalizar/candidatar**
2. **Nunca inventar dados** — só usa o que está no `profile.json`
3. **Sempre persistir** dados novos coletados do usuário no `profile.json`
4. **Sempre pausar** antes de preencher cover letter e pedir o texto ao usuário

---

## Estrutura de Arquivos

```
.agents/skills/subscrible-job/
├── SKILL.md
└── assets/
    ├── profile.json
    ├── Profile.pdf
    └── face.jpg
```

---

## Assets disponíveis no profile.json

Campos presentes: `name`, `cpf`, `birth_date`, `gender`, `pronoun`, `ethnicity`, `pcd`, `phone`, `email`, `location`, `address` (street, number, city, state, state_abbr, country), `linkedin`, `github`, `current_role`, `summary`, `skills`, `languages`, `certifications`, `experience`, `education`, `job_preferences` (primary/secondary contract+modality+salary, availability_days, willing_to_travel, willing_to_relocate, job_source).
