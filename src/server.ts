import { McpServer } from "@modelcontextprotocol/server";
import { registerTools } from "./tools/index.js";

export function createMcpServer(): McpServer {
  const server = new McpServer(
    { name: "my-garmin-mcp", version: "0.1.0" },
    { instructions: "Personal server for the owner's Garmin data." },
  );
  registerTools(server);
  return server;
}
