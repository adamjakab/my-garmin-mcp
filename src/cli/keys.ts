import path from "node:path";
import { KeyStore } from "../auth/keystore.js";
import { config } from "../config.js";

const store = new KeyStore(path.join(config.dataDir, "keys.json"));
const [cmd, arg] = process.argv.slice(2);

switch (cmd) {
  case "create": {
    if (!arg) fail("Usage: npm run keys -- create <name>");
    const { key, stored } = store.create(arg);
    console.log(`Created key "${stored.name}" (id ${stored.id}). Copy it now — it cannot be shown again:\n\n${key}\n`);
    break;
  }
  case "list": {
    const keys = store.list();
    if (!keys.length) console.log("No keys.");
    for (const k of keys) console.log(`${k.id}  ${k.name}  ${k.createdAt}`);
    break;
  }
  case "revoke": {
    if (!arg) fail("Usage: npm run keys -- revoke <id|name>");
    const hit = store.revoke(arg);
    if (!hit) fail(`No key matching "${arg}"`);
    console.log(`Revoked "${hit.name}" (${hit.id})`);
    break;
  }
  default:
    fail("Usage: npm run keys -- <create <name> | list | revoke <id|name>>");
}

function fail(msg: string): never {
  console.error(msg);
  process.exit(1);
}
