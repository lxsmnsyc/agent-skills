set -eu
git init -q -b main
git config user.name "Repo Owner"; git config user.email owner@example.com
mkdir -p src scripts
cat > package.json <<'J'
{"name":"shop","version":"1.0.0","type":"module","private":true,"scripts":{"lint":"node scripts/lint.js","build":"node scripts/build.js","test":"node --test"}}
J
cat > package-lock.json <<'J'
{"name":"shop","version":"1.0.0","lockfileVersion":3,"requires":true,"packages":{"":{"name":"shop","version":"1.0.0"}}}
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
cat > src/db.js <<'J'
// Fake database client. Every query costs one round trip (20 ms).
export const stats = { queries: 0 };
const users = new Map([["u1", { id: "u1", name: "Ada" }], ["u2", { id: "u2", name: "Lin" }]]);

export async function query(ids) {
  stats.queries++;
  await new Promise((r) => setTimeout(r, 20));
  return ids.map((id) => users.get(id)).filter(Boolean);
}
J
cat > src/users.js <<'J'
import { query } from "./db.js";

// Fetch one user by id.
export async function getUser(id) {
  const [user] = await query([id]);
  return user;
}

// Fetch many users in one query.
export async function getUsers(ids) {
  return query([...new Set(ids)]);
}
J
cat > src/orders.js <<'J'
import { getUser } from "./users.js";

// Attach the buyer's name to each order for the orders page.
export async function listOrders(orders) {
  const rows = [];
  for (const order of orders) {
    const user = await getUser(order.userId);
    rows.push({ ...order, buyer: user?.name ?? "unknown" });
  }
  return rows;
}
J
cat > src/orders.test.js <<'J'
import { test } from "node:test";
import assert from "node:assert/strict";
import { listOrders } from "./orders.js";

test("orders get the buyer name", async () => {
  const rows = await listOrders([{ id: 1, userId: "u1" }, { id: 2, userId: "u3" }]);
  assert.deepEqual(rows.map((r) => r.buyer), ["Ada", "unknown"]);
});
J
git add -A && git commit -qm "Add orders page data"
git checkout -qb perf/user-cache
cat > src/users.js <<'J'
import { query } from "./db.js";

const cache = new Map();
const TTL_MS = 60_000;

// Fetch one user by id, cached for one minute.
export async function getUser(id) {
  const hit = cache.get(id);
  if (hit && Date.now() - hit.at < TTL_MS) return hit.user;
  const [user] = await query([id]);
  cache.set(id, { user, at: Date.now() });
  return user;
}

// Clear the user cache. For tests.
export function clearUserCache() {
  cache.clear();
}

// Fetch many users in one query.
export async function getUsers(ids) {
  return query([...new Set(ids)]);
}
J
cat > src/users.test.js <<'J'
import { test } from "node:test";
import assert from "node:assert/strict";
import { getUser, clearUserCache } from "./users.js";
import { stats } from "./db.js";

test("getUser queries once per id within the TTL", async () => {
  clearUserCache();
  const before = stats.queries;
  await getUser("u1");
  await getUser("u1");
  assert.equal(stats.queries - before, 1);
});
J
git add -A && git commit -qm "perf: cache getUser to speed up the orders page (#12)"
git checkout -q main
