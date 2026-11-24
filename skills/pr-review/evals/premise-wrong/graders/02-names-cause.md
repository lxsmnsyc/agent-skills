---
type: llm
focus: trace
weight: 1
---

The review says the slowness comes from calling getUser once per order in a loop in src/orders.js (one query per order), and that the cache does not help the first load of a page whose orders have many different buyers.
