---
type: llm
focus: trace
weight: 1
---

Before proposing options, the run states the contract of topCustomers: orders in, and only the top `limit` rows out, with spent, order count and favourite item. It also describes the current structure: a list of names, one filter and JSON clone per customer, and a sort over all rows. At least one option is a structural rewrite from that contract, such as one grouping pass with a Map, not only local tweaks.
