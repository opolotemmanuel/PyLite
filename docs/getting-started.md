# Getting started

Use Python 3.10 or newer. Open a terminal in the project directory containing
`pyproject.toml` and `README.md`.

## Install on Windows

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
```

If PowerShell script execution is restricted, use the interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m pylite run examples/demo.lite
```

## Install on Linux or macOS

```sh
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

If creating the environment reports that `ensurepip` is unavailable, install your
operating system's Python venv/pip support, then recreate the environment.
Installation may need network access to obtain the setuptools build dependency;
PyLite itself has no external runtime dependencies.

## Run a program

With the environment active, run these commands from the project directory:

```sh
python -m pylite run examples/demo.lite
python -m pylite run examples/full_program.lite
python -m pylite run examples/extensions.lite
python -m pylite run -c 'print(2 + 3)'
pylite run -c 'print(2 + 3)'
```

Both inline commands print `5`. The installed commands work from other
folders too; supply the correct path to your `.lite` file.

On Windows, the optional launcher also supports:

```powershell
.\pylite.ps1 run examples/demo.lite
.\pylite.ps1 -PythonPath .\.venv\Scripts\python.exe run examples/extensions.lite
```

The launcher uses an explicitly supplied interpreter or `python` from PATH.
Activate the environment before using it to select that environment's Python.

## Inspect and check source

```sh
python -m pylite lex examples/extensions.lite
python -m pylite lex examples/extensions.lite --json
python -m pylite check examples/extensions.lite
python -m pylite transpile examples/extensions.lite
```

`check` analyzes syntax and declarations without running the program. Definite
semantic errors fail with status 1; uncertainty warnings return status 0.
Runtime checks remain necessary. `transpile` displays Python helper calls rather
than a standalone Python application.

See the [language reference](language.md), [example guide](../examples/README.md),
and [development guide](development.md) for more.
