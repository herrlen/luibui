# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
import os
from pathlib import Path

# ruleid: LB-C04-zugangsdaten-lesen-py
schluessel = open(os.path.expanduser("~/.ssh/id_rsa")).read()
# ruleid: LB-C04-zugangsdaten-lesen-py
aws = Path.home().joinpath(".aws/credentials").read_text()
# ruleid: LB-C04-zugangsdaten-lesen-py
ed = Path.home() / ".ssh" / "id_ed25519"
# ruleid: LB-C04-zugangsdaten-lesen-py
chrome = os.path.join(profil, "Login Data")
# ok: LB-C04-zugangsdaten-lesen-py
oeffentlich = Path.home() / ".ssh" / "id_ed25519.pub"
# ok: LB-C04-zugangsdaten-lesen-py
konfig = open(".env").read()
# ok: LB-C04-zugangsdaten-lesen-py
hinweis = "Lege deinen API-Schlüssel in der Umgebung ab."
