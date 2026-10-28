---
tags: [goal-debate]
max_turns: 60
timeout_seconds: 1800
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash, Agent, SendMessage, AskUserQuestion]
---

I want every photo in the gallery to get an AI caption, generated locally with an open vision model so nothing goes to a cloud API. The library has about 20k photos. Before we plan any of it, have two agents argue it out: one for the idea, one against, and settle on the best shape given my laptop, how fast we can ship it, and the token cost. If you need answers from me, ask. When you ask about a deadline, assume I answer "two weeks", and about cloud APIs, "only if local is impossible".
