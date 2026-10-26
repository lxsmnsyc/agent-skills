# Accounts

## Outcome

Users can sign up, log in and stay logged in on the web app, backed by server-side sessions. Ships in the 0.4 release.

## Acceptance

- `pnpm test:e2e accounts` passes.

## Priorities

- must: needed for the 0.4 release (sign up, log in, sessions).
- should: improves the 0.4 release but it can ship without it.
- could: worth doing when agents are free.
- later: after 0.4.

## Constraints

- Sessions are server-side, stored in Postgres. No JWT.
- No new paid services.

## Non-goals

- Admin user management UI.

## Verification

- Fast check: `pnpm test --filter accounts` (safe in parallel worktrees)
- Full check: `pnpm check && pnpm test:e2e accounts` (8 min, needs the Postgres container on port 5432; run after merging)

## Numbered resources

- Migrations: `db/migrations/NNNN_*.sql`, reserved per node with `reserves: [migration NNNN]`. Last used: 0031.

## Gates

- After contracts (done, approved 2026-10-20).
