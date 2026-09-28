// LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
import { exec, execSync } from "child_process";

export function tool(name: string) {
  // ruleid: LB-C01-shell-mit-eingabe-js
  execSync(`git log ${name}`);
  // ruleid: LB-C01-shell-mit-eingabe-js
  exec("ls " + name, () => {});
  // ok: LB-C01-shell-mit-eingabe-js
  execSync("git status");
  // ok: LB-C01-shell-mit-eingabe-js
  const m = /a(b)/.exec(name);
  return m;
}
