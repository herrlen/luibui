// LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
import { readFileSync } from "fs";
import { homedir } from "os";

// ruleid: LB-C04-zugangsdaten-lesen-js
const key = readFileSync(`${homedir()}/.ssh/id_rsa`, "utf8");
// ruleid: LB-C04-zugangsdaten-lesen-js
const aws = readFileSync(homedir() + "/.aws/credentials", "utf8");
// ok: LB-C04-zugangsdaten-lesen-js
const pub = readFileSync(`${homedir()}/.ssh/id_rsa.pub`, "utf8");
// ok: LB-C04-zugangsdaten-lesen-js
const cfg = readFileSync("config.json", "utf8");
