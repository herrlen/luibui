# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
# ruleid: LB-C08-verschleiert-sh
echo "ZWNobyBoYWxsbw==" | base64 -d | sh
# ruleid: LB-C08-verschleiert-sh
eval "$(echo ZWNobyBoYWxsbw== | base64 --decode)"
# ok: LB-C08-verschleiert-sh
echo "aGFsbG8=" | base64 -d > hallo.txt
