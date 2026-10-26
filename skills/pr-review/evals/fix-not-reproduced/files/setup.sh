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

git checkout -qb fix/discount-rounding
cat > src/cart.js <<'J'
// Cart totals in cents.
export function subtotal(items) {
  let total = 0;
  for (let i = 1; i < items.length; i++) total += items[i].price * items[i].qty;
  return total;
}

// Round half up so a discount never gives away an extra cent.
export function applyDiscount(total, percent) {
  const discounted = total * (1 - percent / 100);
  return Math.floor(discounted + 0.5);
}
J
cat >> src/cart.test.js <<'J'

test("discount of 15% on 1000 is 850", () => {
  assert.equal(applyDiscount(1000, 15), 850);
});
J
git add -A && git commit -qm "fix: discount rounding gave away a cent" -m "Users reported totals one cent too low after a discount."
git checkout -q main
