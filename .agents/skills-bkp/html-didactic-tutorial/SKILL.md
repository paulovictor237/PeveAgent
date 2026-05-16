---
name: html-didactic-tutorial
description: "Cria documentos HTML interativos e didáticos estilo tutorial — arquivo único, dark mode moderno, barra de progresso de leitura no topo, sidebar esquerda com sumário navegável e scroll contínuo entre seções. Use quando o usuário pedir: criar um tutorial HTML, guia interativo, doc de produto, doc de operação, documento didático, ou qualquer explicação de tema em formato de tutorial navegável. Triggers: 'crie um tutorial HTML sobre X', 'gere um guia interativo de Y', 'faça um documento didático explicando Z', 'quero um HTML de documentação da iniciativa W'."
---

# HTML Didactic Tutorial

## Overview

Gera um arquivo `.html` único e completo com layout de tutorial dark mode: sidebar com sumário automático, barra de progresso de leitura, scroll contínuo entre seções e componentes visuais ricos (cards, steps, callouts, tabelas, embeds).

**Não é necessário código externo — tudo em um único arquivo HTML autocontido.**

## Workflow

1. Leia o conteúdo/tema fornecido pelo usuário (Markdown, outline, texto livre)
2. Mapeie as seções e subseções
3. Copie o template de `assets/template.html` como base
4. Substitua todos os `{{PLACEHOLDER}}` com o conteúdo real
5. Adicione ou remova seções conforme necessário
6. Entregue o arquivo `.html` final

## Template

O arquivo `assets/template.html` é o ponto de partida. Ele já inclui:

- Barra de progresso animada com gradiente roxo/azul no topo
- Topbar fixa com título e percentual lido
- Sidebar com TOC gerado automaticamente via `data-title` nas seções
- TOC highlight ativo via IntersectionObserver
- Scroll suave entre seções
- Layout responsivo com toggle de sidebar no mobile

**Seções do template e seus propósitos:**

| Seção | Componentes incluídos |
|---|---|
| Hero / Introdução | Tag decorativa, título com gradiente, descrição, meta-dados |
| Seção padrão (01-N) | Número da seção, h2, parágrafos, cards, callouts |
| Seção de passos | Stepper numerado com linha conectora |
| Seção de tabela | Tabela com header, badges de status, callout |
| Seção com embed | Bloco de código com copy button + iframe embed |
| Seção de encerramento | Citação, cards de próximos passos, callout de conclusão |

## Componentes disponíveis

Todos os componentes abaixo já estão no CSS/HTML do template. Insira-os nas seções conforme o conteúdo exigir:

### Callouts

```html
<!-- Dica (verde) -->
<div class="callout callout-tip">
  <span class="callout-icon">💡</span>
  <div class="callout-body"><strong>Dica</strong><p>Texto aqui.</p></div>
</div>

<!-- Aviso (amarelo) -->
<div class="callout callout-warning">
  <span class="callout-icon">⚠️</span>
  <div class="callout-body"><strong>Atenção</strong><p>Texto aqui.</p></div>
</div>

<!-- Info (azul) -->
<div class="callout callout-info">
  <span class="callout-icon">ℹ️</span>
  <div class="callout-body"><strong>Nota</strong><p>Texto aqui.</p></div>
</div>

<!-- Perigo (vermelho) -->
<div class="callout callout-danger">
  <span class="callout-icon">🚨</span>
  <div class="callout-body"><strong>Importante</strong><p>Texto aqui.</p></div>
</div>
```

### Cards em grid

```html
<div class="cards-grid">
  <div class="card">
    <span class="card-icon">🎯</span>
    <h4>Título do Card</h4>
    <p>Descrição breve do item.</p>
  </div>
</div>
```

### Stepper (passo a passo)

```html
<ol class="steps">
  <li class="step">
    <div class="step-dot">1</div>
    <div class="step-content">
      <h4>Nome do passo</h4>
      <p>Descrição do que fazer neste passo.</p>
    </div>
  </li>
</ol>
```

### Embed externo

```html
<div class="embed-wrap">
  <div class="embed-header"><span class="embed-label">🔗 Título do embed</span></div>
  <iframe src="URL_AQUI" height="360" allowfullscreen loading="lazy"></iframe>
</div>
```

### Badges inline

```html
<span class="badge badge-green">Ativo</span>
<span class="badge badge-blue">Em revisão</span>
<span class="badge badge-purple">Planejado</span>
<span class="badge badge-red">Inativo</span>
```

### Bloco de código com copy

```html
<div class="code-block">
  <div class="code-header">
    <span class="code-lang">bash</span>
    <button class="copy-btn" onclick="copyCode(this)">Copiar</button>
  </div>
  <pre><code>conteúdo aqui</code></pre>
</div>
```

## Adicionando novas seções

Cada seção deve ter um `id` único e o atributo `data-title` para aparecer no TOC automático:

```html
<section class="section" id="minha-secao" data-title="Título no Sumário">
  <div class="section-header">
    <div class="section-number">06</div>
    <h2>Título da Seção</h2>
  </div>
  <!-- conteúdo -->
</section>
```

## Regras de qualidade

- **Linguagem**: simples, direta e didática. Evite jargão técnico. Explique como se o leitor fosse novo no assunto.
- **Seções**: mínimo 3, máximo 8 seções para manter boa navegação.
- **Tamanho de seção**: cada seção deve ter conteúdo suficiente para justificar a existência (mínimo 2 parágrafos ou 1 componente visual).
- **Completude**: entregue sempre o arquivo HTML completo, nunca parcial ou com `...` no código.
- **Arquivo único**: não referencie CSS ou JS externos. Tudo inline no `<style>` e `<script>`.
- **Nome do arquivo**: use o slug do título do documento (ex: `guia-onboarding-time.html`).

## Assets

- `assets/template.html` — template completo para copiar e customizar
