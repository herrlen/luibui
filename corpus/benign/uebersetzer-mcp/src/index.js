// MCP server that translates short texts with a translation service chosen by the user.
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const API = process.env.UEBERSETZER_URL ?? "https://translate.example/v2";
const server = new McpServer({ name: "uebersetzer", version: "2.0.0" });

server.tool(
  "uebersetzen",
  "Übersetzt einen kurzen Text in die Zielsprache (z. B. de, en, fr, ar).",
  { text: z.string().max(5000), ziel: z.string().length(2) },
  async ({ text, ziel }) => {
    const res = await fetch(`${API}/translate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text, target: ziel }),
    });
    const data = await res.json();
    return { content: [{ type: "text", text: data.translation }] };
  },
);

await server.connect(new StdioServerTransport());
