import http from "node:http";
import net from "node:net";
import type { Duplex } from "node:stream";
import { lookup } from "node:dns/promises";

// After the API container restarts, the cluster DNS keeps returning its old address for about
// 30 seconds. A connection to that address never gets an answer, and Linux gives up only after
// about two minutes: every request in that window hung and then failed with 500 (measured
// 29.09.2026). This agent gives each attempt two seconds, looks the name up again and keeps
// trying for up to 30 seconds. Nothing has been sent before the connection stands, so retrying
// is safe for every request, uploads included. No keep-alive: a pooled socket to a stopped
// container would hang the same way.

export const VERSUCH_MS = 2_000;
export const INSGESAMT_MS = 30_000;
const PAUSE_MS = 500;

type Aufloesen = (host: string) => Promise<string>;

const aufloesen: Aufloesen = async (host) => (await lookup(host)).address;

function verbinden(adresse: string, port: number, ms: number): Promise<net.Socket> {
  return new Promise((resolve, reject) => {
    const socket = net.connect({ host: adresse, port });
    const timer = setTimeout(() => {
      socket.destroy();
      reject(Object.assign(new Error(`connect timeout ${adresse}:${port}`), { code: "ETIMEDOUT" }));
    }, ms);
    socket.once("connect", () => {
      clearTimeout(timer);
      resolve(socket);
    });
    socket.once("error", (err) => {
      clearTimeout(timer);
      socket.destroy();
      reject(err);
    });
  });
}

export async function verbindenMitWiederholung(
  host: string,
  port: number,
  { versuchMs = VERSUCH_MS, insgesamtMs = INSGESAMT_MS, aufloesen: finde = aufloesen } = {},
): Promise<net.Socket> {
  const ende = Date.now() + insgesamtMs;
  for (;;) {
    try {
      return await verbinden(await finde(host), port, versuchMs);
    } catch (err) {
      if (Date.now() + PAUSE_MS >= ende) throw err;
      await new Promise((r) => setTimeout(r, PAUSE_MS));
    }
  }
}

export class ApiAgent extends http.Agent {
  constructor() {
    super({ keepAlive: false });
  }

  // Node's Agent accepts an asynchronous createConnection: return nothing, call back later.
  createConnection(
    options: http.ClientRequestArgs,
    callback?: (err: Error | null, stream: Duplex) => void,
  ): Duplex | null | undefined {
    const host = options.host ?? options.hostname ?? "localhost";
    const port = Number(options.port ?? 80);
    verbindenMitWiederholung(host, port).then(
      (socket) => callback?.(null, socket),
      (err: Error) => callback?.(err, undefined as unknown as Duplex),
    );
    return undefined;
  }
}

/** For the rewrite proxy of Next.js: http-proxy passes ``agent: false``, and Node then creates a
 * fresh agent of the global agent's class for the request (checked in the tests). */
export function installieren(): void {
  http.globalAgent = new ApiAgent();
}
