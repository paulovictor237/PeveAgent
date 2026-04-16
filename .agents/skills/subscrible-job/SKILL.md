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
