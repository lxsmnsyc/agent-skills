set -eu
git init -q -b main
git config user.name "Repo Owner"; git config user.email owner@example.com
mkdir -p src bench
printf "node_modules/\nsetup.sh\n" > .gitignore
cat > package.json <<'J'
{"name":"shop-report","version":"1.0.0","type":"module","private":true,"scripts":{"test":"node --test","bench":"node bench/report.bench.js"}}
J
cat > src/data.js <<'J'
// Deterministic sample data: a small linear congruential generator.
export function makeOrders(count, customers, seed = 1) {
  let x = seed;
  const rand = () => (x = (x * 1103515245 + 12345) % 2147483648) / 2147483648;
  const orders = [];
  for (let i = 0; i < count; i++) {
    orders.push({
      id: i,
      customer: "c" + Math.floor(rand() * customers),
      total: Math.round(rand() * 20000),
      items: [{ sku: "s" + Math.floor(rand() * 50), qty: 1 + Math.floor(rand() * 3) }],
    });
  }
  return orders;
}
J
cat > src/report.js <<'J'
// Customer report: the top spenders, with their order count and favourite item.
export function topCustomers(orders, limit = 10) {
  const names = [];
  for (const order of orders) {
    if (!names.includes(order.customer)) names.push(order.customer);
  }
  const rows = names.map((name) => {
    const mine = JSON.parse(JSON.stringify(orders.filter((o) => o.customer === name)));
    const spent = mine.reduce((sum, o) => sum + o.total, 0);
    const counts = {};
    mine.forEach((o) => o.items.forEach((it) => {
      counts[it.sku] = (counts[it.sku] || 0) + it.qty;
    }));
    const favourite = Object.keys(counts).sort((a, b) => counts[b] - counts[a] || (a < b ? -1 : 1))[0];
    return { customer: name, spent, orders: mine.length, favourite };
  });
  rows.sort((a, b) => b.spent - a.spent || (a.customer < b.customer ? -1 : 1));
  return rows.slice(0, limit);
}
J
cat > src/report.test.js <<'J'
import { test } from "node:test";
import assert from "node:assert/strict";
import { topCustomers } from "./report.js";
import { makeOrders } from "./data.js";

test("top customers by spend, with count and favourite item", () => {
  const orders = [
    { id: 1, customer: "a", total: 100, items: [{ sku: "x", qty: 1 }] },
    { id: 2, customer: "b", total: 300, items: [{ sku: "y", qty: 2 }] },
    { id: 3, customer: "a", total: 250, items: [{ sku: "y", qty: 1 }, { sku: "x", qty: 2 }] },
  ];
  assert.deepEqual(topCustomers(orders, 2), [
    { customer: "a", spent: 350, orders: 2, favourite: "x" },
    { customer: "b", spent: 300, orders: 1, favourite: "y" },
  ]);
});

test("stable result on generated data", () => {
  const top = topCustomers(makeOrders(5000, 400), 3);
  assert.equal(top.length, 3);
  assert.deepEqual(top.map((r) => r.customer), [...top].sort((p, q) => q.spent - p.spent || (p.customer < q.customer ? -1 : 1)).map((r) => r.customer));
});
J
cat > bench/report.bench.js <<'J'
import { topCustomers } from "../src/report.js";
import { makeOrders } from "../src/data.js";

const orders = makeOrders(40000, 3000);
const start = performance.now();
const top = topCustomers(orders, 10);
const ms = performance.now() - start;
console.log(`topCustomers: ${ms.toFixed(1)} ms (top ${top[0].customer} spent ${top[0].spent})`);
J
git add -A && git commit -qm "Add the customer report"
