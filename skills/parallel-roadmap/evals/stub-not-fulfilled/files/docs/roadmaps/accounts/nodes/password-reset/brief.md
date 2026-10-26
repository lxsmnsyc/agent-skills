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
verify: test -f src/server/auth/reset/handler.ts && test -f src/server/auth/reset/handler.test.ts
depends_on:
  - on: contracts
    kind: contract
    via: user-api
---

# Password reset by email

## Acceptance

- [ ] `requestReset(deps, email)` emails a single-use token valid for 1 hour, in `src/server/auth/reset/handler.ts`.
- [ ] `completeReset(deps, token, password)` sets the new password.
- [ ] Tests in `src/server/auth/reset/handler.test.ts`.
