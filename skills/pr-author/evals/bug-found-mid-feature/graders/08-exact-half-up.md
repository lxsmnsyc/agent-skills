---
type: llm
focus: trace
weight: 1
---

On the feature branch, total() rounds tax half up exactly on half-cent cases, for example total([{price: 180, qty: 1}], 0.175) returns 212 (180 + 31.5 rounded up to 32), and it does this without rounding a float to a fixed number of decimal places.
