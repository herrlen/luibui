# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
import os
import shutil
from datetime import datetime

if datetime.now() > datetime(2027, 1, 1):
    # ruleid: LB-C09-zeitbombe-py
    os.system("echo hallo")
if datetime.now() >= datetime(2027, 6, 1):
    # ruleid: LB-C09-zeitbombe-py
    shutil.rmtree(os.path.expanduser("~/nicht-vorhanden-luibui"))
if datetime.now() > ablauf:
    # ok: LB-C09-zeitbombe-py
    os.remove("cache.json")
if datetime.now() > datetime(2027, 1, 1):
    # ok: LB-C09-zeitbombe-py
    print("Diese Version ist veraltet.")
