import path from "node:path";
import { createApp } from "./app.js";
import { KeyStore } from "./auth/keystore.js";
import { config } from "./config.js";

const keys = new KeyStore(path.join(config.dataDir, "keys.json"));
if (keys.list().length === 0) {
  console.warn("No API keys configured — every /mcp request will be rejected. Run: npm run keys -- create <name>");
}

const server = createApp(keys).listen(config.port, config.host, () => {
  console.log(`my-garmin-mcp listening on http://${config.host}:${config.port}/mcp`);
});

for (const sig of ["SIGINT", "SIGTERM"] as const) {
  process.on(sig, () => server.close(() => process.exit(0)));
}
