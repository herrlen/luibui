// LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
const code = Buffer.from("ZWNobyBoYWxsbw==", "base64").toString();
// ruleid: LB-C08-verschleiert-js
eval(code);
// ruleid: LB-C08-verschleiert-js
new Function(atob("cmV0dXJuIDE="))();
const bild = Buffer.from(eingabe, "base64");
// ok: LB-C08-verschleiert-js
require("fs").writeFileSync("bild.png", bild);
