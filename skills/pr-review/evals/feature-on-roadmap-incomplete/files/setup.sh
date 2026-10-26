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

mkdir -p docs/roadmaps/checkout/nodes/tax
cat > docs/roadmaps/checkout/GOAL.md <<'J'
# Checkout

## Outcome

Customers can pay for a cart with correct totals, tax and discounts. Ships in 1.0.
J
cat > docs/roadmaps/checkout/nodes/tax/brief.md <<'J'
---
id: tax
title: Sales tax on the subtotal
status: active
priority: must
size: S
owns: [src/tax.js, src/tax.test.js]
verify: node --test src/tax.test.js
---

# Sales tax on the subtotal

## Acceptance

- [ ] `tax(subtotal, rate)` returns the tax in whole cents, rounded half up.
- [ ] A rate of 0 returns 0, and a negative rate throws a RangeError.
- [ ] Tests in `src/tax.test.js`.
J
git add -A && git commit -qm "Add checkout roadmap"
git checkout -qb feat/tax
cat > src/tax.js <<'J'
// Sales tax in whole cents, rounded half up.
export function tax(subtotal, rate) {
  return Math.floor(subtotal * rate + 0.5);
}
J
cat > src/tax.test.js <<'J'
import { test } from "node:test";
import assert from "node:assert/strict";
import { tax } from "./tax.js";

test("tax rounds half up", () => {
  assert.equal(tax(1050, 0.1), 105);
  assert.equal(tax(125, 0.1), 13);
});
J
sed -i.bak 's/^export function applyDiscount/\/\/ Discounts are applied before tax.\nexport function applyDiscount/' src/cart.js && rm src/cart.js.bak
git add -A && git commit -qm "feat: sales tax on the subtotal" -m "Roadmap node: docs/roadmaps/checkout/nodes/tax/brief.md"
git checkout -q main
