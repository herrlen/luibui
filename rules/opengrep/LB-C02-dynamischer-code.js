// LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
const vm = require("vm");
function run(eingabe) {
  // ruleid: LB-C02-dynamischer-code-js
  eval(eingabe);
  // ruleid: LB-C02-dynamischer-code-js
  vm.runInNewContext(eingabe, {});
  // ok: LB-C02-dynamischer-code-js
  eval("1 + 1");
  // ok: LB-C02-dynamischer-code-js
  return JSON.parse(eingabe);
}
