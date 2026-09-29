// LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
use std::process::Command;

fn tool(name: &str) {
    // ruleid: LB-C01-shell-mit-eingabe-rs
    Command::new("sh").arg("-c").arg(name).output().unwrap();
    // ok: LB-C01-shell-mit-eingabe-rs
    Command::new("sh").arg("-c").arg("git status").output().unwrap();
}
