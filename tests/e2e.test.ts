import { Client, StreamableHTTPClientTransport } from "@modelcontextprotocol/client";
import type { AddressInfo } from "node:net";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { createApp } from "../src/app.js";
import { accessKeyVerifier, generateKey } from "../src/auth/keys.js";

const KEY = generateKey();
const verify = accessKeyVerifier(KEY);
let httpServer: ReturnType<ReturnType<typeof createApp>["listen"]>;
let url: URL;

beforeAll(async () => {
  httpServer = createApp(verify).listen(0, "127.0.0.1");
  await new Promise((r) => httpServer.once("listening", r));
  url = new URL(`http://127.0.0.1:${(httpServer.address() as AddressInfo).port}/mcp`);
});

afterAll(() => {
  httpServer.close();
});

describe("access key", () => {
  it("accepts only the configured key", () => {
    expect(verify(KEY)).toBe(true);
    expect(verify(generateKey())).toBe(false);
    expect(accessKeyVerifier(undefined)("anything")).toBe(false);
  });
});

describe("mcp over http", () => {
  it("rejects requests without a valid key", async () => {
    const res = await fetch(url, { method: "POST" });
    expect(res.status).toBe(401);
  });

  // The v2 client defaults to the 2025 handshake; pinning makes it speak 2026-07-28 or fail.
  const eras = [
    ["2025 era (client default)", undefined],
    ["2026 era (pinned)", { mode: { pin: "2026-07-28" } } as const],
  ] as const;

  it.each(eras)("answers ping with a valid key, %s", async (_name, versionNegotiation) => {
    const client = new Client({ name: "test", version: "0" }, { versionNegotiation });
    await client.connect(
      new StreamableHTTPClientTransport(url, { requestInit: { headers: { Authorization: `Bearer ${KEY}` } } }),
    );
    expect((await client.listTools()).tools.map((t) => t.name)).toEqual(["ping"]);
    const result = await client.callTool({ name: "ping" });
    expect(JSON.stringify(result.content)).toMatch(/pong/);
    await client.close();
  });
});
