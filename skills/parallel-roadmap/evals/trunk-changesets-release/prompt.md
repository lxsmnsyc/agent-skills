---
tags: [parallel-roadmap]
max_turns: 40
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

The accounts roadmap is in docs/roadmaps/accounts. We merge everything to main and publish with changesets: the bot keeps a Version Packages PR open, and merging it publishes. Signup and login are the 0.4 release. Password reset is for 0.5, and its PR #41 is ready (review clean, checks pass). I'm worried 0.5 work slips into 0.4. Set the roadmap up so that cannot happen, and tell me whether to merge #41 now. Don't spawn workers and don't merge anything.

Input files: docs/roadmaps/accounts, .changeset
