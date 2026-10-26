---
name: session-api
version: 1
status: frozen
defined_by: contracts
---

# Contract: session-api

## Interface

```ts
// src/server/auth/session.ts
export interface SessionStore {
  create(userId: string, meta: { ip: string; userAgent: string }): Promise<Session>
  get(token: string): Promise<Session | null>
  revoke(token: string): Promise<void>
}
export interface Session { token: string; userId: string; expiresAt: Date }
```

## Behavior

- Tokens are 32 random bytes, base64url. Sessions expire after 30 days.

## Stub

`src/server/auth/session.fake.ts`, in-memory.
