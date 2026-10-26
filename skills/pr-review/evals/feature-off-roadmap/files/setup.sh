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

## Priorities

- must: needed for 1.0 checkout.
J
cat > docs/roadmaps/checkout/nodes/tax/brief.md <<'J'
---
id: tax
title: Sales tax on the subtotal
status: todo
priority: must
size: S
owns: [src/tax.js, src/tax.test.js]
---

# Sales tax on the subtotal

## Acceptance

- [ ] `tax(subtotal, rate)` returns the tax in whole cents, rounded half up.
J
git add -A && git commit -qm "Add checkout roadmap"
git checkout -qb feat/wishlist
cat > src/wishlist.js <<'J'
// Wishlist: items saved for later, kept in memory per user.
const lists = new Map();

export function save(userId, item) {
  const list = lists.get(userId) ?? [];
  if (!list.some((i) => i.id === item.id)) list.push(item);
  lists.set(userId, list);
  return list;
}

export function remove(userId, itemId) {
  const list = (lists.get(userId) ?? []).filter((i) => i.id !== itemId);
  lists.set(userId, list);
  return list;
}

export function list(userId) {
  return lists.get(userId) ?? [];
}
J
cat > src/wishlist.test.js <<'J'
import { test } from "node:test";
import assert from "node:assert/strict";
import { save, remove, list } from "./wishlist.js";

test("save ignores duplicates and remove drops an item", () => {
  save("u1", { id: "a" });
  save("u1", { id: "a" });
  save("u1", { id: "b" });
  assert.deepEqual(list("u1").map((i) => i.id), ["a", "b"]);
  remove("u1", "a");
  assert.deepEqual(list("u1").map((i) => i.id), ["b"]);
});
J
git add -A && git commit -qm "feat: add a wishlist"
git checkout -q main
