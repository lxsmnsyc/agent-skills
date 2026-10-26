---
name: user-api
version: 1
status: frozen
defined_by: contracts
---

# Contract: user-api

```ts
// src/server/auth/users.ts
export function createUser(email: string, password: string): Promise<User>
export function verifyPassword(email: string, password: string): Promise<User | null>
export interface User { id: string; email: string; createdAt: Date }
```

Passwords are hashed with argon2id.
