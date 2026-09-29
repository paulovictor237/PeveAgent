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

Every day, commits and pushes the following projects:

- /Users/paulo.duarte/workspace/outros/Obsidian Vault
- this repository (PeveAgent)
