# PyLite working directory

The canonical project root is `C:\Users\kingo\Documents\PyLite`
(WSL: `/mnt/c/Users/kingo/Documents/PyLite`). Make future project changes here.
The original Codex outputs/pylite folder is a preserved reference; do not modify
it as part of work on this project.

Read `docs/development.md` and `docs/migration.md` for the retained public APIs.
Preserve this destination's Git history and unrelated user changes.
Run `python -m unittest discover -s tests -v` from this root after code changes.
After installation, `python tests/installed_smoke.py` checks the installed CLI.
