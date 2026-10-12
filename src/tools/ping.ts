import type { McpServer } from "@modelcontextprotocol/server";

export function registerPing(server: McpServer) {
  server.registerTool(
    "ping",
    {
      title: "Ping",
      description: "Health check. Replies with pong and the server time.",
      annotations: { readOnlyHint: true },
    },
    async () => ({
      content: [{ type: "text", text: `pong ${new Date().toISOString()}` }],
    }),
  );
}
