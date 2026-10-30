#!/usr/bin/env sh
# Fast check: every module under src/ parses.
set -e
for f in $(find src -name '*.js'); do node --check "$f"; done
echo ok
