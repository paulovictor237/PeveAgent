---
name: yt-playlist-organizer
description: Organize, manage, and maintain your YouTube playlists. Use this skill whenever the user wants to list playlists, create new playlists, rename or delete playlists, add videos to playlists, remove videos from playlists, reorder videos within a playlist, or manage their YouTube library in any way. This skill handles the full YouTube OAuth authorization flow and should be used for any YouTube playlist management task — even if the user doesn't explicitly say "YouTube" but clearly means playlist organization (e.g., "sort my watched videos", "clean up duplicate playlists", "reorder the videos in my gym playlist"). Make sure to EXPLICITLY ask for user authorization confirmation before making ANY changes to their YouTube account.
version: 1.0.0
---

# YouTube Playlist Organizer

Esta skill gerencia playlists do YouTube via YouTube Data API v3 usando OAuth 2.0.

## Fluxo de Autorização

**ANTES de qualquer operação de escrita (criar, editar, remover), SEMPRE confirme com o usuário.**

### Passo 1: Verificar credenciais

Verifique se existem credenciais OAuth em `~/.config/yt-playlist-organizer/`:

```
CLIENT_ID=$(cat ~/.config/yt-playlist-organizer/client_id 2>/dev/null)
CLIENT_SECRET=$(cat ~/.config/yt-playlist-organizer/client_secret 2>/dev/null)
ACCESS_TOKEN=$(cat ~/.config/yt-playlist-organizer/access_token 2>/dev/null)
REFRESH_TOKEN=$(cat ~/.config/yt-playlist-organizer/refresh_token 2>/dev/null)
```

### Passo 2: Se não existirem — guiar OAuth

O script `scripts/auth.py` automatiza todo o fluxo: abre o navegador, captura o código automaticamente via servidor local e salva os tokens. O usuário só precisa clicar em "Permitir".

**Opção A — com arquivo JSON** (mais fácil, usuário já tem o JSON do Google Cloud):
```bash
python ~/.claude/skills/yt-playlist-organizer/scripts/auth.py setup \
  --from-json /caminho/para/client_secrets.json
```

**Opção B — com credenciais avulsas:**
```bash
python ~/.claude/skills/yt-playlist-organizer/scripts/auth.py setup \
  --client-id CLIENT_ID \
  --client-secret CLIENT_SECRET
```

Se o usuário ainda não tem as credenciais, instruí-lo a:
1. Ir em https://console.cloud.google.com/
2. Criar projeto (ou selecionar existente)
3. APIs e Serviços → Biblioteca → Ativar "YouTube Data API v3"
4. APIs e Serviços → Credenciais → Criar Credenciais → ID do cliente OAuth
5. Tipo: **"App para desktop"**
6. Baixar o JSON — pode passar direto com `--from-json`

### Passo 3: Tokens existentes — validar e refrescar se necessário

Testar token atual:

```bash
curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  https://www.googleapis.com/youtube/v3/playlists?part=snippet&mine=true&maxResults=1
```

Se retornar 401, refrescar com o script:

```bash
python ~/.claude/skills/yt-playlist-organizer/scripts/auth.py refresh
```

O `access_token` salvo será atualizado automaticamente.

## Operações

Todas as operações usam a base URL: `https://www.googleapis.com/youtube/v3`

### Listar todas as playlists

```bash
curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://www.googleapis.com/youtube/v3/playlists?part=snippet,contentDetails&mine=true&maxResults=50"
```

Parsear com `jq` para extrair ID, título, contagem de vídeos.

### Criar playlist

```bash
curl -s -X POST \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "snippet": {
      "title": "NOME DA PLAYLIST",
      "description": "Descrição opcional"
    },
    "status": {"privacyStatus": "private"}
  }' \
  "https://www.googleapis.com/youtube/v3/playlists?part=snippet,status"
```

### Renomear playlist

```bash
curl -s -X PUT \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "PLAYLIST_ID",
    "snippet": {"title": "NOVO TÍTULO", "description": "Atualizada em '"$(date)"'"},
    "status": {"privacyStatus": "PRIVACY"}
  }' \
  "https://www.googleapis.com/youtube/v3/playlists?part=snippet,status"
```

### Deletar playlist

```bash
curl -s -X DELETE \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://www.googleapis.com/youtube/v3/playlists?id=PLAYLIST_ID"
```

### Listar vídeos de uma playlist

```bash
curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet,contentDetails&playlistId=PLAYLIST_ID&maxResults=50"
```

### Adicionar vídeo a playlist

```bash
curl -s -X POST \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "snippet": {
      "playlistId": "PLAYLIST_ID",
      "resourceId": {"kind": "youtube#video", "videoId": "VIDEO_ID"}
    }
  }' \
  "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet"
```

Para obter `VIDEO_ID` de uma URL YouTube:

- `youtube.com/watch?v=VIDEO_ID` → extrair `v`
- `youtu.be/VIDEO_ID` → extrair após domínio
- `youtube.com/shorts/VIDEO_ID` → extrair após `shorts/`

### Remover vídeo de playlist

```bash
curl -s -X DELETE \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://www.googleapis.com/youtube/v3/playlistItems?id=PLAYLIST_ITEM_ID"
```

### Reordenar vídeos (playlistItems.update não suporta posição diretamente)

O YouTube não permite reordenar via API facilmente. Workarounds:

1. **Recriar playlist na ordem desejada** (mais confiável):
   - Listar todos os vídeos
   - Deletar playlist
   - Recriar com nova ordem

2. **Usar playlistItems.insert com position** (pode não funcionar em todas as contas):
   ```bash
   curl -s -X POST \
     -H "Authorization: Bearer ${ACCESS_TOKEN}" \
     -H "Content-Type: application/json" \
     -d '{
       "snippet": {
         "playlistId": "PLAYLIST_ID",
         "resourceId": {"kind": "youtube#video", "videoId": "VIDEO_ID"},
         "position": N
       }
     }' \
     "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet"
   ```

### Buscar vídeos duplicados em uma playlist

Listar playlist e comparar `contentDetails.videoId` — duplicados têm mesmo `videoId`.

## Confirmação Antes de Ações

**REGRA DE OURO: Antes de QUALQUER operação de escrita, PARE e confirme:**

1. Listar exatamente o que vai mudar
2. Mostrar o comando que será executado
3. Pedir confirmação explícita: "Confirma? (sim/não)"

Exemplo de confirmação:

```
⚠️ VOU FAZER AS SEGUINTES MUDANÇAS:

1. CRIAR playlist: "Minha nova playlist"
2. ADICIONAR vídeo: "https://youtube.com/watch?v=ABC123" à playlist "Existente"

Confirma? (sim/não)
```

## Formato de Saída

Ao listar playlists, usar tabela formatada:

```
| # | Playlist                    | Vídeos | Privacidade |
|---|-----------------------------|--------|-------------|
| 1 | Nome da Playlist            |    42  | pública     |
| 2 | Outra Playlist              |   128  | privada     |
```

Ao listar vídeos:

```
| # | Título do Vídeo                         | Adicionado em     |
|---|------------------------------------------|--------------------|
| 1 | Video Example                           | 2024-01-15         |
| 2 | Another Video                           | 2024-02-20         |
```

## Erros Comuns

| Erro                   | Solução                                                  |
| ---------------------- | -------------------------------------------------------- |
| 401 Unauthorized       | Refresh token expirado ou revoke — precisa re-autenticar |
| 403 Quota Exceeded     | API quota diária esgotada — esperar até amanhã           |
| 404 Playlist Not Found | ID da playlist incorreto ou playlist deletada            |
| 400 Bad Request        | Parâmetros inválidos — verificar sintaxe do JSON         |
