// Password reset: emails a single-use token valid for 1 hour, then sets the new password.
import { randomBytes } from "node:crypto";

export interface ResetDeps {
  findUserId(email: string): Promise<string | null>;
  setPassword(userId: string, password: string): Promise<void>;
  sendMail(to: string, body: string): Promise<void>;
  now(): number;
}

const HOUR = 60 * 60 * 1000;
const tokens = new Map<string, { userId: string; expiresAt: number }>();

export async function requestReset(deps: ResetDeps, email: string): Promise<void> {
  const userId = await deps.findUserId(email);
  // Same response for unknown emails, so the endpoint does not reveal which accounts exist.
  if (!userId) return;
  const token = randomBytes(32).toString("base64url");
  tokens.set(token, { userId, expiresAt: deps.now() + HOUR });
  await deps.sendMail(email, `Reset your password: /reset?token=${token}`);
}

export async function completeReset(deps: ResetDeps, token: string, password: string): Promise<boolean> {
  const entry = tokens.get(token);
  tokens.delete(token);
  if (!entry || entry.expiresAt < deps.now()) return false;
  await deps.setPassword(entry.userId, password);
  return true;
}
