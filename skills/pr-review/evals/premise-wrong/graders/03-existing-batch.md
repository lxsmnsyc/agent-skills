---
type: llm
focus: trace
weight: 1
---

The review points to the existing getUsers(ids) in src/users.js as the fix at the cause: listOrders fetches all buyers in one query.
