# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
import base64
import zlib

versteckt = base64.b64decode("ZWNobyBoYWxsbw==")
# ruleid: LB-C08-verschleiert-py
exec(versteckt)
# ruleid: LB-C08-verschleiert-py
exec(zlib.decompress(base64.b64decode("eJxLTc7IV8hIzMnJBwAWTAQS")))
# ok: LB-C08-verschleiert-py
bild = base64.b64decode(eingabe)
# ok: LB-C08-verschleiert-py
open("bild.png", "wb").write(bild)
import subprocess
# ok: LB-C08-verschleiert-py
subprocess.run(["curl", "-d", base64.b64encode(b"daten").decode(), "https://api.example/x"])
