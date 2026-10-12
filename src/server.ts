import { McpServer } from "@modelcontextprotocol/server";
import { registerTools } from "./tools/index.js";

export function createMcpServer(): McpServer {
  const server = new McpServer(
    { name: "my-garmin-mcp", version: "0.1.0" },
    {
      instructions: "Personal server for the owner's Garmin data.",
      // Nothing here ever changes the tool list. Without this, registerTool() defaults it to
      // true and a 2026-era subscriptions/listen would hold a stream open on a stateless endpoint.
      capabilities: { tools: { listChanged: false } },
    },
  );
  registerTools(server);
  return server;
}
