import { createHash, randomBytes, timingSafeEqual } from "node:crypto";

const digest = (s: string) => createHash("sha256").update(s).digest();

/** Checks a presented key against the single configured one (MCP_ACCESS_KEY), in constant time. */
export function accessKeyVerifier(configured: string | undefined): (key: string) => boolean {
  if (!configured) return () => false;
  const expected = digest(configured);
  return (key) => timingSafeEqual(expected, digest(key));
}

export const generateKey = () => "gmcp_" + randomBytes(32).toString("base64url");
