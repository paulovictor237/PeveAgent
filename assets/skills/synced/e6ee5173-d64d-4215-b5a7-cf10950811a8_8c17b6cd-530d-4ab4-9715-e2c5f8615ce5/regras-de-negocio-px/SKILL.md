---
name: regras-de-negocio-px
description: Use quando alguém perguntar como a plataforma PX funciona — regras de negócio, fluxos, status, cálculos, validações, ou comportamento de telas do painel/app do motorista. Responde consultando o código-fonte real dos repositórios PX via Devin MCP (DeepWiki), sempre com citações de arquivo.
---

# Regras de Negócio da Plataforma PX

Responde dúvidas de negócio sobre a plataforma PX consultando o **código-fonte real** dos
repositórios, através do servidor **Devin MCP (DeepWiki)**. Serve para perguntas como
"quais os status de um frete?", "como funciona o adiantamento?", "o que entra na pesquisa
de GR de um motorista?", "o que o transportador vê no painel quando o frete é cancelado?".

## Como responder

1. **Desambigue antes de perguntar.** Se o termo for polissêmico (ver *Termos ambíguos*),
   NÃO assuma um sentido: ou pergunte ao usuário qual ele quer, ou rode as duas interpretações
   e separe as respostas. Assumir o sentido errado é o erro nº 1 desta skill.
2. **Identifique o(s) repositório(s)** pela pergunta, usando o *Mapa de repositórios* abaixo.
3. Chame a ferramenta **`ask_question`** do conector Devin/DeepWiki:
   - `repoName`: o repo (string) **ou vários repos (array)** para fluxos que cruzam sistemas.
   - `question`: reescreva a dúvida de forma **específica e em português**, nomeando o conceito
     (o enum, o serviço, a tela), pedindo **os valores** e **o caminho completo do arquivo**
     (ex.: "cite o caminho completo de cada arquivo", não só o nome da classe).
4. **Na resposta ao usuário:**
   - Escreva em português, claro para alguém **não-técnico**.
   - **Mostre as citações de arquivo e os links de wiki** que a ferramenta retornar — é assim
     que o time confere a fonte.
   - Se vier incompleta, genérica, **ou citando só nomes de classe sem caminho**, **refine**
     (mais específica, nomeie o enum/serviço/tela, peça o caminho completo) e pergunte de novo,
     ou adicione/troque o repo.

> **Default:** dúvida sobre regra de negócio core (frete, contrato, pagamento, adiantamento)
> e o repo não está claro → comece por **`px-center/px-torre-core`** (backend, fonte da verdade).

## Mapa de repositórios (domínio → repo)

| Dúvida sobre... | Repositório |
|---|---|
| Regras core: fretes, contratos, pagamentos, adiantamento, status, validações (backend) | `px-center/px-torre-core` |
| Painel do transportador (web): telas, faturas, contratos, gestão | `px-center/px-painel` |
| App do motorista | `px-center/px-mobile-motorista` |
| Cadastro de motorista / empresa | `px-center/px-registration-front`, `px-center/masterdriver-registration` |
| Pesquisa de **GR** (gerenciamento de risco) dos prestadores | `px-center/px-radar-check`, `px-center/px-radar-check-web`, `px-center/px-radar-enrichment`, `px-center/px-radar-agents`, `px-center/px-radar-infra` |
| Treinamento dos prestadores (academia) | `px-center/px-academy-core` |
| Feature flags | `px-center/px-feature-flag-api`, `px-center/px-feature-flag-web` |
| Integrações (Salesforce, NetSuite, BrasilRisk, SmartPay) | `px-center/px-integrations-salesforce-conector`, `px-center/px-integrations-netsuite-connector`, `px-center/px-integrations-brasilrisk`, `px-center/px-integrations-smartpay` |

**Glossário:** *GR* = gerenciamento de risco (pesquisa/aprovação do prestador). *Prestador* = motorista/parceiro.
*(Repos puramente técnicos como `px-test-automation` raramente ajudam em dúvida de negócio — ignore, salvo pergunta sobre testes.)*

### Termos ambíguos (desambigue antes de perguntar)

| Termo | Sentido A | Sentido B | Como tratar |
|---|---|---|---|
| **"pesquisa de motorista"** | **GR** (Brasil Risk/Radar): aprovar/vetar o prestador | **Matching/Falcon**: buscar e convidar motoristas para um frete | Pergunte qual, ou rode os dois e separe. |
| **"score" / "avaliação"** | Score de risco/elegibilidade do prestador | Avaliação do frete (estrelas, pós-viagem) | Confirme o contexto. |

> **GR mora em dois lugares.** `px-torre-core` tem o `RiskManagerSearch` (integração Brasil
> Risk/Radar, visão do ciclo de vida da pesquisa). O **motor de regras** que decide adequado/
> pendente/insuficiente está nos `px-radar-*`. Dúvida de GR completa → inclua **ambos**, não só
> o default `px-torre-core`.

## Escolhendo os repositórios

- Regra / cálculo / status / validação → quase sempre **`px-torre-core`** (backend).
- Tela, o que o usuário vê, passo no painel → **`px-painel`** (ou **`px-mobile-motorista`** para o motorista).
- **Fluxo ponta-a-ponta** ("do começo ao fim", "como o painel mostra o que o backend calcula") →
  passe **vários repos no array**, ex.: `["px-center/px-torre-core", "px-center/px-painel"]`.
- Na dúvida, inclua o backend (`px-torre-core`) + o repo da interface relevante.

## Como fazer boas perguntas

A qualidade da resposta depende da pergunta enviada à ferramenta. Reescreva a dúvida do usuário:
- **Específica, nomeando o conceito:** "Quais os valores do enum `FreightStatusEnum` e o que cada um
  significa?" em vez de "como funciona o frete?".
- **Peça evidência:** "...liste todos os valores." / "...cite os arquivos."
- **Em português** (a resposta sai em PT).
- **Uma intenção por pergunta** — quebre dúvidas grandes em partes.

## Exemplos

**Status (factual) — 1 repo**
> Usuário: "quais os status de um frete?"
> `ask_question({ repoName: "px-center/px-torre-core", question: "Quais são todos os valores do FreightStatusEnum, com o código e o label de cada um? Cite o arquivo." })`

**Fluxo — multi-repo**
> Usuário: "como o status do frete aparece pro transportador no painel?"
> `ask_question({ repoName: ["px-center/px-torre-core","px-center/px-painel"], question: "Como o status do frete definido no backend é consumido e exibido no painel do transportador? Cite os arquivos dos dois lados." })`

**GR — multi-repo**
> Usuário: "o que entra na pesquisa de GR do motorista?"
> `ask_question({ repoName: ["px-center/px-radar-check","px-center/px-radar-enrichment"], question: "Quais dados e fontes compõem a pesquisa de GR de um prestador e como o resultado é avaliado/aprovado? Cite os arquivos." })`

## Limites

- As respostas são **geradas a partir do código**: ótimas para entender o sistema, mas **confira as
  citações** antes de tratar como verdade definitiva — sobretudo em decisões críticas.
- Resposta vaga ou "não encontrei"? Refine nomeando o termo técnico (enum, serviço, tela) ou
  ajuste o conjunto de repos.
- Cobre o que está **no código** dos repositórios PX. Não substitui documentação de produto,
  contratos comerciais ou decisões que não estejam implementadas.
- **O label exibido ao usuário pode divergir entre repos.** O mesmo status do enum core pode
  aparecer com texto diferente no painel (ex.: `WITH_DRIVER` = "Motorista Selecionado" no
  `px-torre-core` vs "Aguardando início" no `px-painel`). Em dúvida de tela, confirme o label
  no repo da interface, não só no backend.
