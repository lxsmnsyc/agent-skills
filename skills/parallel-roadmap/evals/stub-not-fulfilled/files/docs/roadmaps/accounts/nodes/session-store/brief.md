---
id: session-store
title: Postgres session store
status: done
priority: must
size: M
owns: [src/server/auth/session.pg.ts, db/migrations/0032_sessions.sql]
reserves: [migration 0032]
provides: [session-api]
depends_on:
  - on: contracts
    kind: contract
    via: session-api
---

# Postgres session store

Implements SessionStore on Postgres.
