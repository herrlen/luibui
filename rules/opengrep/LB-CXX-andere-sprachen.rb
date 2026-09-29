# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
require "base64"

def tool(name)
  # ruleid: LB-C01-shell-mit-eingabe-rb
  system("git log #{name}")
  # ok: LB-C01-shell-mit-eingabe-rb
  system("git status")
  # ruleid: LB-C02-dynamischer-code-rb
  eval(name)
  # ok: LB-C02-dynamischer-code-rb
  eval("1 + 1")
  # ruleid: LB-C08-verschleiert-rb
  eval(Base64.decode64("cHV0cyAx"))
  # ok: LB-C08-verschleiert-rb
  File.write("bild.png", Base64.decode64(name))
end
