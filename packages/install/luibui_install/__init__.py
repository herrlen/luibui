"""``luibui-install``: install packages from the luibui register (S4-5).

Deliberately separate from the engine: it contains no checks and no rules, only what is needed to
fetch a published version, verify luibui's signature and the archive, show the result of the
check and set the package up. It never executes anything from the package.
"""
