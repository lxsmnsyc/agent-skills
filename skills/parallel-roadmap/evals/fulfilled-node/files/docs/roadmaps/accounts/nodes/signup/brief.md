---
id: signup
title: Signup slice
status: todo
priority: must
size: M
owns:
  - src/server/auth/signup/**
  - src/web/routes/signup/**
  - db/migrations/0033_users.sql
shared: [src/server/routes.ts]
reserves: [migration 0033]
depends_on:
  - on: contracts
    kind: contract
    via: user-api
  - on: session-store
    kind: behavior
    via: session-api
---

# Signup slice

POST /api/signup and the /signup page. Creates the user and logs them in.
