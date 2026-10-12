import type { McpServer } from "@modelcontextprotocol/server";
import { registerPing } from "./ping.js";

/** Add new tool registrations here. */
export function registerTools(server: McpServer) {
  registerPing(server);
}
