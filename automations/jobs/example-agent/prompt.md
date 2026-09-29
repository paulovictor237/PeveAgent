---
enabled: false
mode: agent
schedule: weekdays
time: "09:00"
precheck: "git log --since=yesterday --oneline | grep -q ."
agent_cmd: "claude -p --permission-mode plan"
timeout_minutes: 15
notify: always
---

Resuma os commits das últimas 24h deste repositório em até 5 bullets.
