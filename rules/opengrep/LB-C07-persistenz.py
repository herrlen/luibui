# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
import os
import shutil
import subprocess

# ruleid: LB-C07-persistenz-py
with open(os.path.expanduser("~/.bashrc"), "a") as f:
    f.write("echo hallo\n")
# ruleid: LB-C07-persistenz-py
ziel = os.path.expanduser("~/Library/LaunchAgents/com.beispiel.plist")
# ruleid: LB-C07-persistenz-py
subprocess.run("(crontab -l; echo '* * * * * echo hallo') | crontab -", shell=True)
# ruleid: LB-C07-persistenz-py
subprocess.run(["crontab", "-"], input="* * * * * echo hallo\n", text=True)
# ok: LB-C07-persistenz-py
subprocess.run(["crontab", "-l"], capture_output=True, text=True)
# ok: LB-C07-persistenz-py
vorhanden = shutil.which("crontab")
# ok: LB-C07-persistenz-py
open("einstellungen.json", "w").write("{}")
# ok: LB-C07-persistenz-py
hinweis = "Füge den Pfad selbst zu deiner Shell hinzu."
