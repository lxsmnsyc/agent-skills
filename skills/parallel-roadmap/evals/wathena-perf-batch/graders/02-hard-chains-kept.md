---
type: llm
focus: trace
weight: 1
---

Retention/partition-drop work from ADR 0057 step 1 is ordered before 0057 step 5 (chat_log partitioning), and the 0055 frame-writer steps keep their order.
