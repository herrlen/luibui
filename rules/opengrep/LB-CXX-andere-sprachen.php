<?php
// LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
function tool($name) {
    // ruleid: LB-C01-shell-mit-eingabe-php
    shell_exec("git log " . $name);
    // ok: LB-C01-shell-mit-eingabe-php
    shell_exec("git status");
    // ruleid: LB-C02-dynamischer-code-php
    eval($name);
    // ok: LB-C02-dynamischer-code-php
    assert($name == "x");
    // ruleid: LB-C08-verschleiert-php
    eval(gzinflate(base64_decode("S0zOyFcIzy/KSQEA")));
    // ok: LB-C08-verschleiert-php
    file_put_contents("bild.png", base64_decode($name));
}
