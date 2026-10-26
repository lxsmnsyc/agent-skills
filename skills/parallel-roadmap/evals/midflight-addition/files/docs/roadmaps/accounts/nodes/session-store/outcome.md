# Outcome: session-store

## Built

- `src/server/auth/session.pg.ts`, migration `0032_sessions.sql` (table `sessions`, index on `user_id`).

## Gotchas

- `revoke` is idempotent. Expired rows are cleaned by a daily job, not on read.

## Size

- Estimated M, actual M.
