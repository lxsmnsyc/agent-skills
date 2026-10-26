set -eu
git init -q -b main
git config user.name "Repo Owner"; git config user.email owner@example.com
mkdir -p src scripts
cat > package.json <<'J'
{"name":"cart","version":"1.0.0","type":"module","private":true,"scripts":{"lint":"node scripts/lint.js","build":"node scripts/build.js","test":"node --test"}}
J
cat > package-lock.json <<'J'
{"name":"cart","version":"1.0.0","lockfileVersion":3,"requires":true,"packages":{"":{"name":"cart","version":"1.0.0"}}}
J
cat > scripts/lint.js <<'J'
import { readdirSync, readFileSync } from "node:fs";
let bad = 0;
for (const f of readdirSync("src")) {
  const text = readFileSync("src/" + f, "utf8");
  if (/\bvar\b/.test(text)) { console.error(`src/${f}: use let or const, not var`); bad++; }
}
process.exit(bad ? 1 : 0);
J
cat > scripts/build.js <<'J'
import { mkdirSync, readdirSync, copyFileSync } from "node:fs";
mkdirSync("dist", { recursive: true });
for (const f of readdirSync("src")) if (!f.endsWith(".test.js")) copyFileSync("src/" + f, "dist/" + f);
J
printf "dist/\nnode_modules/\nsetup.sh\n" > .gitignore
cat > src/cart.js <<'J'
// Cart totals in cents.
export function subtotal(items) {
  let total = 0;
  for (let i = 1; i < items.length; i++) total += items[i].price * items[i].qty;
  return total;
}

export function applyDiscount(total, percent) {
  return Math.round(total * (1 - percent / 100));
}
J
cat > src/cart.test.js <<'J'
import { test } from "node:test";
import assert from "node:assert/strict";
import { applyDiscount } from "./cart.js";

test("discount rounds to whole cents", () => {
  assert.equal(applyDiscount(999, 10), 899);
});
J
git add -A && git commit -qm "Add cart totals"

mkdir -p .github/workflows
cat > .github/workflows/ci.yml <<'J'
name: ci
on:
  pull_request:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test
J
printf "# cart\n\nCart totals in cents. Run the tests with \`npm tset\`.\n" > README.md
git add -A && git commit -qm "Add CI and README"
git init -q --bare ../origin.git
git remote add origin ../origin.git
git push -q -u origin main
