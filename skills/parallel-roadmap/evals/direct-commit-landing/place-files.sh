#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
R=docs/roadmaps/onboarding

git init -q -b main
git config user.name "Eval"
git config user.email "eval@example.com"
git add -A
git commit -qm "chore: start onboarding roadmap"

# The story branch, with the welcome child already landed on it.
git switch -qc feat/onboarding
mkdir -p src/onboarding/welcome
printf 'export function welcome(name) {\n  return `Welcome, ${name}`\n}\n' > src/onboarding/welcome/index.js
printf '# Outcome: welcome\n\n## Built\n\n- `welcome(name)` in `src/onboarding/welcome/index.js`.\n' > $R/nodes/welcome/outcome.md
git add -A
git commit -qm "feat: add the welcome step"

# The profile-setup worker's branch: two commits on top of the story branch.
git switch -qc feat/profile-setup
mkdir -p src/onboarding/profile
printf 'export function profile(input) {\n  return { name: input.name }\n}\n' > src/onboarding/profile/index.js
git add -A
git commit -qm "profile-setup: Profile setup step"
printf 'export function profile(input) {\n  return { name: input.name.trim(), avatar: input.avatar ?? null }\n}\n' > src/onboarding/profile/index.js
printf '# Outcome: profile-setup\n\n## Built\n\n- `profile(input)` in `src/onboarding/profile/index.js`, trims the name and keeps an optional avatar.\n\n## Size\n\n- Estimated M, actual M.\n' > $R/nodes/profile-setup/outcome.md
git add -A
git commit -qm "profile-setup: fix review findings"

# The docs-readme worker's branch, from main.
git switch -q main
git switch -qc docs/readme
printf '# Demo app\n\n## Onboarding\n\nNew users go through the welcome and profile steps.\n' > README.md
printf '# Outcome: docs-readme\n\n## Built\n\n- Onboarding section in `README.md`.\n' > $R/nodes/docs-readme/outcome.md
git add -A
git commit -qm "docs-readme: Document onboarding in the readme"

git switch -q main
