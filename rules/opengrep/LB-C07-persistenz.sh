# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
# ruleid: LB-C07-persistenz-sh
(crontab -l; echo "* * * * * echo hallo") | crontab -
# ruleid: LB-C07-persistenz-sh
cp dienst.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/dienst.plist
# ruleid: LB-C07-persistenz-sh
systemctl --user enable hallo.service
# ok: LB-C07-persistenz-sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
# ok: LB-C07-persistenz-sh
crontab -l
# ok: LB-C07-persistenz-sh
crontab -r
