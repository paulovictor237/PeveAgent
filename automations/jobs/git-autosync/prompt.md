---
enabled: true
mode: script
script: run.sh
schedule: daily
time: "09:00"
missed_run_grace_minutes: 720
timeout_minutes: 10
notify: on_failure
---

Todo dia, faz commit e push dos seguintes projetos:

- /Users/paulo.duarte/workspace/outros/Obsidian Vault
- este repositório (PeveAgent)
