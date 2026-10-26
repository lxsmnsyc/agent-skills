---
id: password-reset
title: Password reset by email
status: todo
priority: could
size: M
owns:
  - src/server/auth/reset/**
  - src/web/routes/reset/**
  - db/migrations/0034_reset_tokens.sql
reserves: [migration 0034]
depends_on:
  - on: contracts
    kind: contract
    via: user-api
---

# Password reset by email
