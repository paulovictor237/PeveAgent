---
name: subscrible-job
description: Especialista em preencher formulários de candidatura a vagas de emprego. Use quando o usuário fornecer uma URL de vaga e quiser se candidatar automaticamente.
---

# subscrible-job

## Regras Hard

1. **NUNCA clique em submit / enviar / finalizar / candidatar / apply**
2. **NUNCA invente dados** — use exclusivamente o que está em `profile.json`
3. **SEMPRE persista** no `profile.json` qualquer dado novo fornecido pelo usuário
4. **SEMPRE pause** quando encontrar campo de cover letter e peça o texto ao usuário
5. **SEMPRE faça upload** do `Profile-pt.pdf` quando encontrar campo de arquivo

## Arquivos

```
assets/profile.json    ← dados do candidato
assets/Profile-pt.pdf  ← currículo em português
assets/Profile-en.pdf  ← currículo em inglês
scripts/run.py         ← script principal (Python 3)
scripts/lib/           ← módulos internos
```

## Como executar

```bash
SKILL_DIR=<skill_dir> python3 <skill_dir>/scripts/run.py "<URL_DA_VAGA>"
```

**Fluxo:**
1. Abre browser (você vê o que acontece)
2. Escaneia e preenche campos automaticamente
3. Reporta o que não conseguiu mapear
4. **Você preenche o restante no browser**
5. **Feche o browser** → script captura edits e atualiza `profile.json`

## Cover letter

Reportado no terminal como `⚠`. Preencha manualmente no browser.

## Campos não mapeados

O script marca com `○`. Preencha manualmente — ao fechar o browser, o valor é capturado e salvo em `extra_fields` do profile.json. Na próxima execução, o script já sabe o mapeamento.

## Exemplo

```bash
SKILL_DIR=/Users/peve/.claude/skills/subscrible-job \
  python3 /Users/peve/.claude/skills/subscrible-job/scripts/run.py \
  "https://empresa.com/vaga/123"
```

## Melhoria incremental

Quando um campo não é preenchido corretamente na primeira vez, você corrige manualmente e o valor fica salvo. Nas próximas execuções com sites similares, o script já conhece o campo.

## Sem retry

Se o preenchimento de um campo falhar, o script marca como `✗` e avança para o próximo. Sem loops ou tentativas repetidas.