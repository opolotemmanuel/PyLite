# Manual testing

Open `C:\Users\kingo\Documents\PyLite` in VS Code. Commands below are for the
terminal in that project root, not the nested Python package directory.

## Windows PowerShell

```powershell
Set-Location 'C:\Users\kingo\Documents\PyLite'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
python -m pylite check examples/manual_test.lite
python -m pylite run examples/manual_test.lite
pylite run -c 'print(2 + 3)'
.\pylite.ps1 run examples/manual_test.lite
```

If script execution is restricted, use `.\.venv\Scripts\python.exe` directly
for installation and `-m pylite` commands. Windows launcher execution was not
performed on the Linux verification host.

## WSL / Linux

```sh
cd /mnt/c/Users/kingo/Documents/PyLite
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
python -m pylite check examples/manual_test.lite
python -m pylite run examples/manual_test.lite
pylite run -c 'print(2 + 3)'
```

For the isolated Linux environment created during this verification, use
`.venv-verify/bin/python` and `.venv-verify/bin/pylite` instead. These Linux
executables are for WSL; create a Windows environment to use Windows Python.

## Expected output

`manual_test.lite` demonstrates declarations/reassignment, integers, floats,
scientific notation, booleans, both quote styles, escapes, nested comments,
precedence, all comparisons, nested/zero loops, optional indentation, both
conditionals, pipelines, all builtins, multiline parentheses and dynamic values.
The first five lines are the requested acceptance program.

Running the file must print exactly:

```text
Hello 1
Hello 2
Hello 3
Done
6
Numbers: 3.14 1000.0 0.025
Quotes: It's PyLite "double" \
Escapes: 3 2 false
Math: 14 20 5 2.5 4 -4
Compare: true true true true true true false
Concat: PyLite
Nested: 4
Builtins: 7 5 true 42
6
Multiline: 3
Dynamic: changed
```

The same expected text is stored in
[manual_test.expected.txt](../examples/manual_test.expected.txt). Regression
tests assert it through the API, generated Python, and CLI. Inline execution
prints `5`.

## Inspect source and run automated checks

```sh
python -m pylite lex examples/manual_test.lite
python -m pylite lex examples/manual_test.lite --json
python -m pylite parse examples/manual_test.lite
python -m pylite transpile examples/manual_test.lite
python -m unittest discover -s tests -v
python tests/installed_smoke.py
python -m pip check
```

`check` does not execute code or prove runtime safety. A valid check can still
fail on division by zero or invalid runtime types. Static uncertainty produces
warnings with status 0; definite binding errors return 1.
