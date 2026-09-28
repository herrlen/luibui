// LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
const fs = require("fs");
const os = require("os");
// ruleid: LB-C07-persistenz-js
fs.appendFileSync(`${os.homedir()}/.zshrc`, "echo hallo\n");
// ruleid: LB-C07-persistenz-js
fs.writeFileSync(os.homedir() + "/.config/autostart/x.desktop", "[Desktop Entry]");
// ok: LB-C07-persistenz-js
fs.writeFileSync("ausgabe.txt", "hallo");
