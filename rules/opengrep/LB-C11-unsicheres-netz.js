// LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
const https = require("https");
// ruleid: LB-C11-unsicheres-netz-js
const agent = new https.Agent({ rejectUnauthorized: false });
// ruleid: LB-C11-unsicheres-netz-js
process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
// ruleid: LB-C11-unsicheres-netz-js
app.listen(3000, "0.0.0.0");
// ok: LB-C11-unsicheres-netz-js
app.listen(3000, "127.0.0.1");
// ok: LB-C11-unsicheres-netz-js
const sicher = new https.Agent({ keepAlive: true });
