---
tags: [parallel-roadmap]
max_turns: 60
timeout_seconds: 1800
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash, Agent]
---

brumate's backlog in ~/Documents/GitHub/brumate/docs/proposals.md is one long ordered list and it's slowing me down. Take the pending core work (scope-ID table, tests against the current build, ordered updates, batching, fields typed before load, triggers in tests), the agent support items (skill for .brm files, llms.txt, copy for an agent in devtools, brumate check, tasks that check the skill) and the website fixes, and make a roadmap that agents can run concurrently. Not everything is equally important: I need the core correctness work and the agent skill soon, the rest can wait. Plan only, don't build.
