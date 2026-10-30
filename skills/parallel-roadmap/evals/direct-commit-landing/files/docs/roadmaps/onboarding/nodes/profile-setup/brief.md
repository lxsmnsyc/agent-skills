---
id: profile-setup
title: Profile setup step
status: active
type: feature
story: onboarding
size: M
owns:
  - src/onboarding/profile/**
depends_on:
  - on: welcome
    kind: hard
    why: the profile step follows the welcome step and reuses its module layout
---

# Profile setup step

## Goal

`profile(input)` validates the name and an optional avatar.

## Acceptance

- [ ] `sh check.sh` passes.
