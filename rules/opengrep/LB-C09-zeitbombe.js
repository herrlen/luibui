// LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
const { execSync } = require("child_process");
if (Date.now() > new Date("2027-01-01").getTime()) {
  // ruleid: LB-C09-zeitbombe-js
  execSync("echo hallo");
}
if (Date.now() > new Date("2027-01-01").getTime()) {
  // ok: LB-C09-zeitbombe-js
  console.log("Diese Version ist veraltet.");
}
