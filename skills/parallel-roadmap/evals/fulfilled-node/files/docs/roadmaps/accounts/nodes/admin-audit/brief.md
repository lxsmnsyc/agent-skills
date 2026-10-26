---
id: admin-audit
title: Audit log of logins for admins
status: todo
priority: later
size: L
owns: [src/server/audit/**]
depends_on:
  - on: login
    kind: hard
    why: hooks into the finished login handler
---

# Audit log of logins
