# Development guide

Use a fresh virtual environment as described in [getting started](getting-started.md).
Run all commands below from the repository root.

## Implementation stages

| File | Responsibility |
| --- | --- |
| `pylite/lexer.py` | Scan tokens, strings, numbers, comments, and source positions |
| `pylite/parser.py` | Parse explicit blocks and expressions into located syntax nodes |
| `pylite/compiler.py` | Lower syntax nodes to guarded Python AST |
| `pylite/transpiler.py` | Preserve the workspace native-AST compiler API |
| `pylite/binding_checks.py` | Preserve the workspace strict semantic API |
| `pylite/semantic.py` | Analyze possible bindings without executing the program |
| `pylite/runtime.py` | Enforce runtime semantics and execute helper-based AST |
| `pylite/diagnostics.py` | Format source diagnostics and resource errors |
| `pylite/__main__.py` | Provide the module CLI and installed entry point |
| `pylite/__init__.py` | Export the Python API |

`check` uses the analyzer. `run` retains runtime checks; it does not automatically
reject programs because of static warnings or unreachable binding errors.

## Test changes

```sh
python -m unittest discover -s tests -v
```

The suite covers the original acceptance program, lexer/parser/runtime behavior,
extensions, semantic analysis, CLI statuses, and resource diagnostics. Windows
launcher tests require Windows and PowerShell and are skipped on other platforms.
See the [test guide](../tests/README.md) for individual files.

## Verify the installed package

After changing package code, rebuild the installed copy before checking it:

```sh
python -m pip install .
python tests/installed_smoke.py
python -m pip check
```

The smoke script runs the installed module and executable outside the checkout,
removes developer Python path overrides, and checks outputs and exit statuses.
It requires a normal installation in the active virtual environment. Unit tests
run from the repository usually import local source, so they alone do not prove
that the installed package contains the changes.

## Automation and generated files

`.github/workflows/ci.yml` defines installation and test jobs for Python
3.10–3.14 on Ubuntu and Windows. A configured job is not evidence that it has run;
actual local results and pending platform checks are in the
[verification record](verification.md).

`build/`, `dist/`, `*.egg-info/`, `.venv/`, and Python caches are generated local
artifacts, covered by `.gitignore`. Keep authored code in `pylite/`, runnable
programs in `examples/`, tests in `tests/`, and prose documentation in `docs/`.
See the [folder map](repository-layout.md).

## APIs retained during the workspace merge

`pylite.parser.Parser` returns source-located `Program` syntax nodes, as in the
original workspace. `pylite.SyntaxParser` is an explicit alias. The package-level
`pylite.Parser` returns guarded Python AST, preserving the completed project's
API. Both call the same syntax parser; there is one grammar.

`pylite.transpiler.Transpiler` retains the native Python AST API and strict
`SemanticAnalyzer` validation. CLI execution and package-level `transpile`
use `compiler.Compiler` and runtime guards. `check` uses the newer conservative
binding analyzer; `SemanticAnalyzer` remains the original strict compatibility
API. `run` returns a dict-compatible result, also available through `.variables`.
Precise filename/span diagnostics and no-debug-range fallbacks are preserved.

The distribution name remains `pylite-lang`, matching the destination project.
