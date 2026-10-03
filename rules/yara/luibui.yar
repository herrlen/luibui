// Eigene YARA-Regeln von luibui für Programmdateien (S4-10, Prüfkatalog C10, A04).
// Geprüft werden nur Binärdateien; Textdateien decken Opengrep und die Inhaltsregeln ab, und in
// Dokumentation zitierte Befehle sollen hier nicht anschlagen. Jede Regel trägt in `meta` die
// Regel-ID, die Schwere (K/H/M) und einen deutschen Titel. Testfälle: rules/yara/tests/.

rule LB_C10_krypto_miner
{
    meta:
        regel = "LB-C10-krypto-miner"
        schwere = "K"
        titel = "Programmdatei enthält einen Krypto-Miner"
    strings:
        $pool1 = "stratum+tcp://" nocase
        $pool2 = "stratum+ssl://" nocase
        $pool3 = "stratum2+tcp://" nocase
        $x1 = "xmrig" nocase
        $x2 = "--donate-level"
        $x3 = "cryptonight" nocase
        $x4 = "randomx" nocase
    condition:
        any of ($pool*) or 2 of ($x*)
}

rule LB_C10_reverse_shell
{
    meta:
        regel = "LB-C10-reverse-shell"
        schwere = "K"
        titel = "Programmdatei öffnet eine Reverse Shell"
    strings:
        $tcp = "/dev/tcp/"
        $i1 = "bash -i"
        $i2 = "sh -i"
        $nc1 = "nc -e /bin/sh"
        $nc2 = "nc -e /bin/bash"
        $nc3 = "ncat -e /bin/"
        $socat = /socat [^\x00]{0,40}exec:[^\x00]{0,40}pty/
    condition:
        ($tcp and any of ($i*)) or any of ($nc*) or $socat
}

rule LB_C10_ransomware
{
    meta:
        regel = "LB-C10-ransomware"
        schwere = "K"
        titel = "Programmdatei enthält eine Lösegeldforderung"
    strings:
        $v1 = "files have been encrypted" nocase
        $v2 = "files are encrypted" nocase
        $v3 = "Dateien wurden verschlüsselt" nocase
        $z1 = "bitcoin" nocase
        $z2 = "monero" nocase
        $z3 = "decrypt your files" nocase
        $z4 = "ransom" nocase
    condition:
        any of ($v*) and any of ($z*)
}

rule LB_C10_keylogger
{
    meta:
        regel = "LB-C10-keylogger"
        schwere = "H"
        titel = "Programmdatei liest Tastatureingaben mit"
    strings:
        $w1 = "SetWindowsHookExA"
        $w2 = "SetWindowsHookExW"
        $k1 = "GetAsyncKeyState"
        $k2 = "GetKeyboardState"
        $k3 = "/dev/input/event"
        $l1 = "keylog" nocase
    condition:
        (any of ($w*) and any of ($k*)) or ($l1 and any of ($k*))
}

rule LB_C10_anti_analyse
{
    meta:
        regel = "LB-C10-anti-analyse"
        schwere = "H"
        titel = "Programmdatei versucht, Analyse und Sandboxen zu erkennen"
    strings:
        $d1 = "IsDebuggerPresent"
        $d2 = "CheckRemoteDebuggerPresent"
        $d3 = "NtQueryInformationProcess"
        $v1 = "VBoxService" nocase
        $v2 = "vmtoolsd" nocase
        $v3 = "wine_get_version"
        $v4 = "SbieDll.dll" nocase
    condition:
        2 of ($d*) and any of ($v*)
}

rule LB_A04_gepackt
{
    meta:
        regel = "LB-A04-gepackt"
        schwere = "M"
        titel = "Programmdatei ist gepackt"
    strings:
        $upx1 = "UPX!"
        $upx2 = "UPX0"
        $upx3 = "UPX1"
    condition:
        $upx1 and ($upx2 or $upx3)
}
