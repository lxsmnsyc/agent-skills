---
id: login
title: Login slice
status: done
priority: must
size: M
owns:
  - src/server/auth/login/**
  - src/web/routes/login/**
shared: [src/server/routes.ts]
depends_on:
  - on: session-store
    kind: behavior
    via: session-api
  - on: contracts
    kind: contract
    via: user-api
---

# Login slice

POST /api/login (email, password) checks the password with `verifyPassword`, creates a session and sets the `sid` cookie. Login page at /login with error states.

## Acceptance

- [ ] Wrong password shows "Email or password is wrong" without saying which.
- [ ] Successful login redirects to /app with a session cookie (HttpOnly, Secure, SameSite=Lax).
- [ ] Fast check passes.
