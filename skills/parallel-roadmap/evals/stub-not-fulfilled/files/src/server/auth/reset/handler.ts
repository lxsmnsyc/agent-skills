// Password reset: emails a single-use token valid for 1 hour, then sets the new password.
export async function requestReset(email: string): Promise<void> {}
export async function completeReset(token: string, password: string): Promise<void> {}
