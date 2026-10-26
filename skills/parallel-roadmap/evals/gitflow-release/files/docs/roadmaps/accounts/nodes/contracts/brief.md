---
id: contracts
title: Freeze session and user contracts
status: done
priority: must
size: S
gate: true
owns: [src/server/auth/session.ts, src/server/auth/users.ts, src/server/auth/*.fake.ts]
provides: [session-api, user-api]
---

# Freeze session and user contracts

Types, fakes and contract tests for sessions and users.
