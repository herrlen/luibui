// LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
class Tool {
    void run(String name) throws Exception {
        // ruleid: LB-C01-shell-mit-eingabe-java
        Runtime.getRuntime().exec("git log " + name);
        // ok: LB-C01-shell-mit-eingabe-java
        Runtime.getRuntime().exec("git status");
    }
}
