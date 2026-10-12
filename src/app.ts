import { createMcpHandler } from "@modelcontextprotocol/server";
import express from "express";
import { Readable } from "node:stream";
import { bearerAuth } from "./auth/middleware.js";
import type { KeyStore } from "./auth/keystore.js";
import { createMcpServer } from "./server.js";

/** Stateless: the handler builds a fresh McpServer per request, so restarts never invalidate client sessions. */
export function createApp(keys: KeyStore) {
  const mcp = createMcpHandler(() => createMcpServer(), {
    onerror: (err) => console.error("MCP error:", err),
  });

  const app = express();
  app.use(express.json({ limit: "1mb" }));

  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  // Express req/res <-> web-standard Request/Response bridge for the fetch-shaped MCP handler.
  app.all("/mcp", bearerAuth(keys), async (req, res) => {
    const headers = new Headers();
    for (const [k, v] of Object.entries(req.headers)) {
      if (v !== undefined) headers.set(k, Array.isArray(v) ? v.join(", ") : v);
    }
    const hasBody = req.method !== "GET" && req.method !== "HEAD";
    const request = new Request(`${req.protocol}://${req.get("host")}${req.originalUrl}`, {
      method: req.method,
      headers,
      body: hasBody && req.body !== undefined ? JSON.stringify(req.body) : undefined,
    });

    try {
      const response = await mcp.fetch(request, { parsedBody: req.body });
      res.status(response.status);
      response.headers.forEach((value, key) => res.setHeader(key, value));
      if (response.body) {
        Readable.fromWeb(response.body as never).pipe(res);
      } else {
        res.end();
      }
    } catch (err) {
      console.error("MCP request failed:", err);
      if (!res.headersSent) {
        res.status(500).json({ jsonrpc: "2.0", error: { code: -32603, message: "Internal error" }, id: null });
      }
    }
  });

  return app;
}
