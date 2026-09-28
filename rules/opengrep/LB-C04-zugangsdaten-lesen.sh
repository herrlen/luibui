# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
# ruleid: LB-C04-zugangsdaten-lesen-sh
cat ~/.ssh/id_rsa | base64
# ruleid: LB-C04-zugangsdaten-lesen-sh
cp "$HOME/.aws/credentials" /tmp/x
# ruleid: LB-C04-zugangsdaten-lesen-sh
security find-generic-password -s "Chrome Safe Storage" -w
# ok: LB-C04-zugangsdaten-lesen-sh
cat ~/.ssh/id_rsa.pub
# ok: LB-C04-zugangsdaten-lesen-sh
# Hinweis: niemals ~/.ssh/id_rsa weitergeben
echo "fertig"
