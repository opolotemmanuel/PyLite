# Workspace migration

Canonical project folder: `C:\Users\kingo\Documents\PyLite`.
WSL path: `/mnt/c/Users/kingo/Documents/PyLite`.
Use this destination for future development. Open the project root in VS Code,
rather than just its nested `pylite/` package folder.

Source: `C:\Users\kingo\Documents\Codex\2026-10-13\i-x20\outputs\pylite`.
The original source is left intact. Virtual environments, caches, build outputs,
Git metadata, and environment state are excluded from the copy.

## Inspection and conflict decisions

The destination started clean on main, at commit
`84fe4d68500591ffa1b4d8d0d2d68ab483d923c6`. Its original suite passed 84 tests.
The source and destination had 2 identical files, 11 differing overlaps, 17
source-only files and 10 destination-only files (excluding generated state).
All differences were reviewed before applying the merged files. The destination
Git directory and its configuration/history are not replaced or copied.

- Preserve the destination syntax nodes, span metadata, native transpiler API,
  strict analyzer API, reserved compiler prefix, parse command and tutorial.
- Add source extensions, conservative checking, runtime guards, helper AST API,
  launcher, documentation, examples and tests. Compile the shared syntax tree
  into guarded AST rather than maintaining two parsers.
- Preserve dict-style run results while also providing the source `.variables` API.
- Preserve precise runtime spans, UTF-8 byte/visual-column conversion and Python
  3.10/no-debug-range diagnostic fallbacks; unexpected helper defects still propagate.
- Keep the destination distribution identity `pylite-lang`, its manifest and
  original CI workflow. Merge the newer Python/Windows and installed-package
  checks into that workflow, retaining no-debug-range jobs.
- Keep all original destination tests. The overlapping runtime test module is
  retained as `test_workspace_runtime.py`; the shared lexer tests use the newer
  literal rules. One old CLI assertion is updated for the expanded check summary.
  No diagnostic precision assertions were weakened.
- Preserve the original destination README at
  [migration/workspace-readme-v1.md](migration/workspace-readme-v1.md).

See [development](development.md) for both retained API entry points and
[verification](verification.md) for the historical source checks.

## Differing overlapping files

- `README.md`
- `pylite/__init__.py`
- `pylite/__main__.py`
- `pylite/diagnostics.py`
- `pylite/lexer.py`
- `pylite/parser.py`
- `pylite/runtime.py`
- `pylite/semantic.py`
- `pyproject.toml`
- `tests/test_lexer.py`
- `tests/test_runtime.py`

## Validation

The merged staged suite passed: **140 collected, 137 passed, 3 Windows-only
launcher tests skipped** on Linux/Python 3.14.4. Destination execution and
installation results are recorded below after the copy.

## Run here

Windows PowerShell:

```powershell
Set-Location 'C:\Users\kingo\Documents\PyLite'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
python -m unittest discover -s tests -v
python -m pylite run examples/full_program.lite
python -m pylite run examples/extensions.lite
python -m pylite run examples/tutorial.lite
pylite run -c 'print(2 + 3)'
```

WSL:

```sh
cd /mnt/c/Users/kingo/Documents/PyLite
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
python -m unittest discover -s tests -v
python -m pylite run examples/extensions.lite
```

## Destination results — 2026-10-18 (Africa/Kampala)

- From this destination, Python 3.14.4 collected 140 tests: 137 passed and three
  Windows-only launcher checks skipped. The staged no-debug-range suite also passed.
- Built and installed pylite-lang 1.1.0 from this destination into fresh
  `/tmp/pylite-destination-venv`; pip check found no broken requirements.
- Installed module and entry-point smoke checks passed outside the checkout,
  asserting full example outputs and error exit statuses.
- Ran demo.lite, full_program.lite, extensions.lite and the preserved tutorial.lite
  from the destination. Inline execution printed 5. The original acceptance
  program printed Hello 1, Hello 2, Hello 3, Done, 6, exactly as expected.
- Checked 40 relative documentation links and verified source file hashes against
  the pre-copy inventory. The original source is unchanged.
- At application time, destination .git file hashes were identical before and
  after copying. No Git metadata was imported, no commits were created and no
  changes were pushed. Changes remain available for review in git diff/status.
- Original destination authored files are backed up at
  `/tmp/pylite-workspace-merge/destination-original`; this temporary backup is not
  permanent storage. The clean pre-merge destination is also recoverable from
  the existing Git commit recorded above.

Windows launcher execution remains untested on this Linux host. The configured
Windows CI jobs have not been triggered. Future edits belong in this destination.
