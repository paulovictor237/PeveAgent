---
name: yt-playlist-organizer
description: Organize, manage, and maintain your YouTube playlists. Use this skill whenever the user wants to list playlists, create new playlists, rename or delete playlists, add videos to playlists, remove videos from playlists, reorder videos within a playlist, or manage their YouTube library in any way. This skill handles the full YouTube OAuth authorization flow and should be used for any YouTube playlist management task — even if the user doesn't explicitly say "YouTube" but clearly means playlist organization (e.g., "sort my watched videos", "clean up duplicate playlists", "reorder the videos in my gym playlist"). Make sure to EXPLICITLY ask for user authorization confirmation before making ANY changes to their YouTube account.
version: 1.0.0
---

# YouTube Playlist Organizer

This skill manages YouTube playlists via the YouTube Data API v3 using OAuth 2.0.

## Authorization Flow

**BEFORE any write operation (create, edit, remove), ALWAYS confirm with the user.**

### Step 1: Check credentials

Check if OAuth credentials exist in `~/.config/yt-playlist-organizer/`:

```
CLIENT_ID=$(cat ~/.config/yt-playlist-organizer/client_id 2>/dev/null)
CLIENT_SECRET=$(cat ~/.config/yt-playlist-organizer/client_secret 2>/dev/null)
ACCESS_TOKEN=$(cat ~/.config/yt-playlist-organizer/access_token 2>/dev/null)
REFRESH_TOKEN=$(cat ~/.config/yt-playlist-organizer/refresh_token 2>/dev/null)
```

### Step 2: If they don't exist — guide OAuth

The script `scripts/auth.py` automates the entire flow: opens the browser, automatically captures the code via a local server, and saves the tokens. The user only needs to click "Allow".

**Option A — with JSON file** (easiest, user already has the Google Cloud JSON):
```bash
python ~/.claude/skills/yt-playlist-organizer/scripts/auth.py setup \
  --from-json /path/to/client_secrets.json
```

**Option B — with individual credentials:**
```bash
python ~/.claude/skills/yt-playlist-organizer/scripts/auth.py setup \
  --client-id CLIENT_ID \
  --client-secret CLIENT_SECRET
```

If the user does not have credentials yet, instruct them to:
1. Go to https://console.cloud.google.com/
2. Create a project (or select an existing one)
3. APIs & Services → Library → Enable "YouTube Data API v3"
4. APIs & Services → Credentials → Create Credentials → OAuth client ID
5. Type: **"Desktop app"**
6. Download the JSON — can be passed directly with `--from-json`

### Step 3: Existing tokens — validate and refresh if necessary

Test current token:

```bash
curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  https://www.googleapis.com/youtube/v3/playlists?part=snippet&mine=true&maxResults=1
```

If it returns 401, refresh with the script:

```bash
python ~/.claude/skills/yt-playlist-organizer/scripts/auth.py refresh
```

The saved `access_token` will be updated automatically.

## Operations

All operations use the base URL: `https://www.googleapis.com/youtube/v3`

### List all playlists

```bash
curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://www.googleapis.com/youtube/v3/playlists?part=snippet,contentDetails&mine=true&maxResults=50"
```

Parse with `jq` to extract ID, title, video count.

### Create playlist

```bash
curl -s -X POST \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "snippet": {
      "title": "PLAYLIST NAME",
      "description": "Optional description"
    },
    "status": {"privacyStatus": "private"}
  }' \
  "https://www.googleapis.com/youtube/v3/playlists?part=snippet,status"
```

### Rename playlist

```bash
curl -s -X PUT \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "PLAYLIST_ID",
    "snippet": {"title": "NEW TITLE", "description": "Updated on '"$(date)"'"},
    "status": {"privacyStatus": "PRIVACY"}
  }' \
  "https://www.googleapis.com/youtube/v3/playlists?part=snippet,status"
```

### Delete playlist

```bash
curl -s -X DELETE \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://www.googleapis.com/youtube/v3/playlists?id=PLAYLIST_ID"
```

### List videos from a playlist

```bash
curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet,contentDetails&playlistId=PLAYLIST_ID&maxResults=50"
```

### Add video to playlist

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

To get `VIDEO_ID` from a YouTube URL:

- `youtube.com/watch?v=VIDEO_ID` → extract `v`
- `youtu.be/VIDEO_ID` → extract after domain
- `youtube.com/shorts/VIDEO_ID` → extract after `shorts/`

### Remove video from playlist

```bash
curl -s -X DELETE \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://www.googleapis.com/youtube/v3/playlistItems?id=PLAYLIST_ITEM_ID"
```

### Reorder videos (playlistItems.update does not support position directly)

YouTube does not allow reordering via API easily. Workarounds:

1. **Recreate playlist in desired order** (more reliable):
   - List all videos
   - Delete playlist
   - Recreate with new order

2. **Use playlistItems.insert with position** (may not work on all accounts):
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

### Find duplicate videos in a playlist

List playlist and compare `contentDetails.videoId` — duplicates have the same `videoId`.

## Confirmation Before Actions

**GOLDEN RULE: Before ANY write operation, STOP and confirm:**

1. List exactly what will change
2. Show the command to be executed
3. Ask for explicit confirmation: "Confirm? (yes/no)"

Confirmation example:

```
⚠️ I WILL MAKE THE FOLLOWING CHANGES:

1. CREATE playlist: "My new playlist"
2. ADD video: "https://youtube.com/watch?v=ABC123" to "Existing" playlist

Confirm? (yes/no)
```

## Output Format

When listing playlists, use a formatted table:

```
| # | Playlist                    | Videos | Privacy     |
|---|-----------------------------|--------|-------------|
| 1 | Playlist Name               |    42  | public      |
| 2 | Another Playlist            |   128  | private     |
```

When listing videos:

```
| # | Video Title                             | Added on          |
|---|------------------------------------------|--------------------|
| 1 | Video Example                           | 2024-01-15         |
| 2 | Another Video                           | 2024-02-20         |
```

## Common Errors

| Error                  | Solution                                                  |
| ---------------------- | --------------------------------------------------------- |
| 401 Unauthorized       | Refresh token expired or revoked — need to re-authenticate |
| 403 Quota Exceeded     | API daily quota exceeded — wait until tomorrow            |
| 404 Playlist Not Found | Incorrect playlist ID or playlist deleted                 |
| 400 Bad Request        | Invalid parameters — check JSON syntax                    |
