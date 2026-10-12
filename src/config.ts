import fs from "node:fs";
import path from "node:path";

// Node's built-in .env loader; real environment variables win over the file.
if (fs.existsSync(".env")) process.loadEnvFile(".env");

export const config = {
  port: Number(process.env.PORT ?? 3334),
  host: process.env.HOST ?? "127.0.0.1",
  accessKey: process.env.MCP_ACCESS_KEY,
  dataDir: path.resolve(process.env.DATA_DIR ?? "data"),
  garmin: {
    email: process.env.GARMIN_EMAIL,
    password: process.env.GARMIN_PASSWORD,
    tokenStore: path.resolve(process.env.GARMIN_TOKEN_STORE ?? "data/garmin-tokens"),
  },
};
