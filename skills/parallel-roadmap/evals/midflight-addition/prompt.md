---
tags: [parallel-roadmap]
max_turns: 40
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

We're in the middle of the accounts roadmap in docs/roadmaps/accounts, the login node is being worked on by an agent right now. Two things came up: I want "Sign in with GitHub" (OAuth), and we should add rate limiting to login because we saw brute force attempts in staging. Can you fit these in? Don't spawn any workers, just update the plan.

Input files: docs/roadmaps/accounts
