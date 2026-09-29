import http from "node:http";
import type { AddressInfo } from "node:net";

import { afterEach, describe, expect, it } from "vitest";

import { ApiAgent, verbindenMitWiederholung } from "./api-verbindung";

let server: http.Server | null = null;

function starten(): Promise<number> {
  return new Promise((resolve) => {
    server = http.createServer((_q, r) => r.end("ok")).listen(0, "127.0.0.1", () => {
      resolve((server!.address() as AddressInfo).port);
    });
  });
}

afterEach(() => {
  server?.close();
  server = null;
});

describe("Verbindung zur API nach einem Neustart", () => {
  it("looks the name up again after a dead address and connects", async () => {
    const port = await starten();
    const antworten = ["10.255.255.1", "127.0.0.1"]; // first the stale, unreachable address
    let versuche = 0;
    const socket = await verbindenMitWiederholung("api", port, {
      versuchMs: 300,
      insgesamtMs: 5_000,
      aufloesen: async () => antworten[Math.min(versuche++, 1)],
    });
    expect(versuche).toBe(2);
    expect(socket.remoteAddress).toBe("127.0.0.1");
    socket.destroy();
  });

  it("gives up after the overall limit", async () => {
    const start = Date.now();
    await expect(
      verbindenMitWiederholung("api", 9, { versuchMs: 200, insgesamtMs: 1_000, aufloesen: async () => "10.255.255.1" }),
    ).rejects.toThrow();
    expect(Date.now() - start).toBeLessThan(3_000);
  });

  it("serves a normal request through the agent, also for agent: false", async () => {
    const port = await starten();
    const vorher = http.globalAgent;
    http.globalAgent = new ApiAgent();
    try {
      const text = await new Promise<string>((resolve, reject) => {
        http
          .get({ host: "127.0.0.1", port, agent: false }, (res) => {
            let body = "";
            res.on("data", (c) => (body += c));
            res.on("end", () => resolve(body));
          })
          .on("error", reject);
      });
      expect(text).toBe("ok");
    } finally {
      http.globalAgent = vorher;
    }
  });
});
