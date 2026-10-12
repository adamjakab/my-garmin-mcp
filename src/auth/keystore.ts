import { createHash, randomBytes, randomUUID, timingSafeEqual } from "node:crypto";
import fs from "node:fs";
import path from "node:path";

export interface StoredKey {
  id: string;
  name: string;
  /** sha256 hex of the full key; the key itself is never stored. */
  hash: string;
  createdAt: string;
}

const KEY_PREFIX = "gmcp_";

const hashKey = (key: string) => createHash("sha256").update(key).digest("hex");

/** API keys persisted as a JSON file (no database). Re-read on every call so CLI changes apply without a restart. */
export class KeyStore {
  constructor(private readonly file: string) {}

  list(): StoredKey[] {
    try {
      return JSON.parse(fs.readFileSync(this.file, "utf8")) as StoredKey[];
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code === "ENOENT") return [];
      throw err;
    }
  }

  /** Returns the plaintext key — this is the only time it is available. */
  create(name: string): { key: string; stored: StoredKey } {
    if (this.list().some((k) => k.name === name)) {
      throw new Error(`A key named "${name}" already exists`);
    }
    const key = KEY_PREFIX + randomBytes(32).toString("base64url");
    const stored: StoredKey = {
      id: randomUUID().slice(0, 8),
      name,
      hash: hashKey(key),
      createdAt: new Date().toISOString(),
    };
    this.save([...this.list(), stored]);
    return { key, stored };
  }

  /** Revoke by id or name. Returns the revoked key, or undefined if none matched. */
  revoke(idOrName: string): StoredKey | undefined {
    const keys = this.list();
    const hit = keys.find((k) => k.id === idOrName || k.name === idOrName);
    if (hit) this.save(keys.filter((k) => k !== hit));
    return hit;
  }

  verify(key: string): StoredKey | undefined {
    const candidate = Buffer.from(hashKey(key), "hex");
    let match: StoredKey | undefined;
    for (const k of this.list()) {
      const stored = Buffer.from(k.hash, "hex");
      if (stored.length === candidate.length && timingSafeEqual(stored, candidate)) match = k;
    }
    return match;
  }

  private save(keys: StoredKey[]) {
    fs.mkdirSync(path.dirname(this.file), { recursive: true });
    const tmp = `${this.file}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(keys, null, 2) + "\n", { mode: 0o600 });
    fs.renameSync(tmp, this.file);
  }
}
