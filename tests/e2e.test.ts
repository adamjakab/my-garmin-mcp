import { Client, StreamableHTTPClientTransport } from "@modelcontextprotocol/client";
import fs from "node:fs";
import type { AddressInfo } from "node:net";
import os from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { createApp } from "../src/app.js";
import { KeyStore } from "../src/auth/keystore.js";

let dir: string;
let keys: KeyStore;
let httpServer: ReturnType<ReturnType<typeof createApp>["listen"]>;
let url: URL;

beforeAll(async () => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "gmcp-"));
  keys = new KeyStore(path.join(dir, "keys.json"));
  httpServer = createApp(keys).listen(0, "127.0.0.1");
  await new Promise((r) => httpServer.once("listening", r));
  url = new URL(`http://127.0.0.1:${(httpServer.address() as AddressInfo).port}/mcp`);
});

afterAll(() => {
  httpServer.close();
  fs.rmSync(dir, { recursive: true, force: true });
});

describe("keystore", () => {
  it("verifies created keys, rejects unknown ones, and supports revoke", () => {
    const { key, stored } = keys.create("unit");
    expect(keys.verify(key)?.id).toBe(stored.id);
    expect(keys.verify("gmcp_nope")).toBeUndefined();
    expect(fs.readFileSync(path.join(dir, "keys.json"), "utf8")).not.toContain(key);
    keys.revoke("unit");
    expect(keys.verify(key)).toBeUndefined();
  });
});

describe("mcp over http", () => {
  it("rejects requests without a valid key", async () => {
    const res = await fetch(url, { method: "POST" });
    expect(res.status).toBe(401);
  });

  it("answers ping with a valid key", async () => {
    const { key } = keys.create("e2e");
    const client = new Client({ name: "test", version: "0" });
    await client.connect(
      new StreamableHTTPClientTransport(url, { requestInit: { headers: { Authorization: `Bearer ${key}` } } }),
    );
    const result = await client.callTool({ name: "ping" });
    expect(JSON.stringify(result.content)).toMatch(/pong/);
    await client.close();
  });
});
