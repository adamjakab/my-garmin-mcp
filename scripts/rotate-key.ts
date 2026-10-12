import fs from "node:fs";
import readline from "node:readline/promises";
import { generateKey } from "../src/auth/keys.js";

const ENV_FILE = ".env";
const VAR = "MCP_ACCESS_KEY";
const force = process.argv.includes("--yes");

if (!fs.existsSync(ENV_FILE)) {
  console.error(`No ${ENV_FILE} here. Copy .env.example to .env first.`);
  process.exit(1);
}

if (!force) {
  if (!process.stdin.isTTY) {
    console.error("Not interactive: pass --yes to rotate without asking.");
    process.exit(1);
  }
  console.warn(`WARNING: this replaces ${VAR} in ${ENV_FILE}. The current key stops working once the server restarts,`);
  console.warn("and every client using it (Claude Code, the phone, ...) must be updated with the new key.");
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const answer = (await rl.question("Rotate the key? [y/N] ")).trim().toLowerCase();
  rl.close();
  if (answer !== "y" && answer !== "yes") {
    console.log("Cancelled; nothing changed.");
    process.exit(0);
  }
}

const key = generateKey();
const text = fs.readFileSync(ENV_FILE, "utf8");
const line = new RegExp(`^${VAR}=.*$`, "m");
const updated = line.test(text) ? text.replace(line, () => `${VAR}=${key}`) : `${text.replace(/\n*$/, "\n")}${VAR}=${key}\n`;

const tmp = `${ENV_FILE}.tmp`;
fs.writeFileSync(tmp, updated, { mode: fs.statSync(ENV_FILE).mode });
fs.renameSync(tmp, ENV_FILE);

console.log(`Updated ${VAR} in ${ENV_FILE}. New key:\n\n${key}\n`);
console.log("Restart the service to apply it:  pm2 restart my-garmin-mcp");
