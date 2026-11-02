---
type: llm
focus: trace
weight: 1
---

The run asks the user at most two questions, only for choices that neither the goal nor the repo answers (such as the deadline). It infers what the goal already says, such as no cloud API, as `inferred` facts instead of asking, and does not ask for facts it could look up, such as the photo count or free memory.
