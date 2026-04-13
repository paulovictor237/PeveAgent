---
name: listen
description: Lê a última interação em voz alta usando edge-tts (vozes neurais), ou lê um arquivo específico se passado como parâmetro. Use quando o usuário pedir para ouvir, reproduzir, escutar ou ler em voz alta a última resposta, um arquivo, ou qualquer menção a "listen", "ouça", "fale", "leia em voz alta", "text-to-speech", "TTS", ou variação relacionada a áudio.
---

# Listen

Lê a última resposta da conversa em voz alta usando edge-tts (text-to-speech neural) e reproduz o áudio automaticamente, ou lê um arquivo específico se passado como parâmetro.

## Como usar

### Sem parâmetros (lê última resposta)

1. **Identifique sua resposta anterior** nesta conversa (não inclua mensagens do usuário).

2. **Prepare o texto**:
   - Remova emojis e caracteres especiais problemáticos
   - Mantenha apenas o texto principal da resposta

3. **Escolha a voz apropriada** baseada no idioma:
   - **Português**: Use `pt-BR-FranciscaNeural`
   - **Inglês**: Use `en-US-JennyNeural`

4. **Gere e reproduza o áudio**:

   Para textos curtos (até ~200 caracteres):
   ```bash
   edge-tts --voice "pt-BR-FranciscaNeural" --text "TEXTO_AQUI" --write-media /tmp/listen_output.mp3 && afplay /tmp/listen_output.mp3
   ```

   Para textos longos (recomendado - use heredoc para textos multilinha):
   ```bash
   cat > /tmp/listen_input.txt << 'EOF'
   TEXTO_AQUI
   EOF

   edge-tts --voice "pt-BR-FranciscaNeural" --file /tmp/listen_input.txt --write-media /tmp/listen_output.mp3 && afplay /tmp/listen_output.mp3
   ```

   Ou comando único para textos longos:
   ```bash
   cat > /tmp/listen_input.txt << 'EOF'
   TEXTO_AQUI
   EOF

   edge-tts --voice "pt-BR-FranciscaNeural" --file /tmp/listen_input.txt --write-media /tmp/listen_output.mp3 && afplay /tmp/listen_output.mp3
   ```

### Com parâmetro de arquivo (lê um arquivo específico)

Use a skill passando o caminho do arquivo como parâmetro:

```bash
/listen /caminho/para/arquivo.txt
```

Exemplos:
```bash
/listen README.md
/listen /Users/paulovictor237/.claude/skills/listen/SKILL.md
/listen ~/documentos/texto.txt
```

A skill irá:
1. Ler o conteúdo do arquivo
2. Remover emojis e caracteres especiais problemáticos
3. Gerar e reproduzir o áudio usando edge-tts
4. Reproduzir automaticamente com afplay

## Notas importantes

- **Use heredoc com cat** para criar arquivos temporários - evita problemas com aspas e caracteres especiais
- **Use a abordagem de arquivo** (`--file`) para textos longos ou com formatação complexa
- **Arquivos temporários** são salvos em `/tmp/listen_*` e serão limpos automaticamente pelo sistema
- **Formato de áudio**: MP3 (compatível com afplay no macOS)
- **Não use Write** para arquivos temporários - o sistema exige leitura prévia, causando erros desnecessários

## Ferramentas permitidas

- `Bash(edge-tts*)` - Geração de áudio neural
- `Bash(afplay*)` - Reprodução de áudio no macOS
- `Bash(cat > /tmp/listen_*)` - Criação de arquivos temporários com heredoc

## Dependências

Esta skill requer `edge-tts` (Python) e `afplay` (nativo do macOS).

Se o comando `edge-tts` não estiver disponível, rode o script de instalação:

```bash
bash ~/.claude/skills/listen/scripts/install.sh
```

O script verifica e instala automaticamente o que estiver faltando. Consulte [scripts/install.sh](scripts/install.sh) para detalhes.
