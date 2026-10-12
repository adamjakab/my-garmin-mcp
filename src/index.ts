import { createApp } from "./app.js";
import { accessKeyVerifier } from "./auth/keys.js";
import { config } from "./config.js";

if (!config.accessKey) {
  console.warn("No MCP_ACCESS_KEY configured — every /mcp request will be rejected. Set MCP_ACCESS_KEY in .env (npm run rotate-key generates one)");
}

const server = createApp(accessKeyVerifier(config.accessKey)).listen(config.port, config.host, () => {
  console.log(`my-garmin-mcp listening on http://${config.host}:${config.port}/mcp`);
});

for (const sig of ["SIGINT", "SIGTERM"] as const) {
  process.on(sig, () => server.close(() => process.exit(0)));
}
