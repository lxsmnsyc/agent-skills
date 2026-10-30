---
type: llm
focus: trace
weight: 1
---

feat/onboarding ends with exactly one new commit on top of "feat: add the welcome step", holding the profile-setup changes (src/onboarding/profile/index.js and its outcome). It is a squash of the two worker commits, not a merge commit and not the two original commits, and its subject is the pull request title from plan.py (for example "feat: profile setup step") or follows the repo convention. The branch was fast-forwarded, never force-updated.
