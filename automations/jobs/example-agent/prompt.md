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

Summarize the last 24h of commits in this repository in up to 5 bullets.
