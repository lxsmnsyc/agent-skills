import { test } from "node:test";
import assert from "node:assert/strict";
import { requestReset, completeReset, type ResetDeps } from "./handler.ts";

function setup(start = 0) {
  let clock = start;
  const mails: string[] = [];
  const passwords = new Map<string, string>();
  const deps: ResetDeps = {
    findUserId: async (email) => (email === "a@x.dev" ? "u1" : null),
    setPassword: async (id, pw) => { passwords.set(id, pw); },
    sendMail: async (_to, body) => { mails.push(body); },
    now: () => clock,
  };
  const token = () => mails.at(-1)!.split("token=")[1];
  return { deps, mails, passwords, token, tick: (ms: number) => { clock += ms; } };
}

test("reset sets the new password once", async () => {
  const s = setup();
  await requestReset(s.deps, "a@x.dev");
  assert.equal(await completeReset(s.deps, s.token(), "new-pass"), true);
  assert.equal(s.passwords.get("u1"), "new-pass");
  assert.equal(await completeReset(s.deps, s.token(), "again"), false);
});

test("token expires after one hour", async () => {
  const s = setup();
  await requestReset(s.deps, "a@x.dev");
  s.tick(60 * 60 * 1000 + 1);
  assert.equal(await completeReset(s.deps, s.token(), "late"), false);
});

test("unknown email sends nothing", async () => {
  const s = setup();
  await requestReset(s.deps, "nobody@x.dev");
  assert.equal(s.mails.length, 0);
});
