import path from "node:path";

export const config = {
  port: Number(process.env.PORT ?? 3334),
  host: process.env.HOST ?? "127.0.0.1",
  dataDir: path.resolve(process.env.DATA_DIR ?? "data"),
};
