# PyLite 1.1

A runnable educational language with explicit blocks, declared variables, immutable constants, and pipelines. Includes lexer, parser, semantic analyzer, Python AST transpiler, runtime, CLI, examples, tests, and GitHub CI. Requires Python 3.10+; no external runtime dependencies.

## Documentation

Start with the [documentation index](docs/README.md) or
[installation guide](docs/getting-started.md). The
[folder map](docs/repository-layout.md) explains where everything belongs.
[Examples](examples/README.md), [test instructions](tests/README.md), and the
[development guide](docs/development.md) have their own indexes.

## Run on Windows

Open PowerShell in this folder:

```powershell
.\pylite.ps1 run examples/full_program.lite
```

The launcher uses `python` from your PATH (activate your virtual environment first). You can supply `-PythonPath 'C:\path\to\python.exe'` explicitly. If your computer restricts PowerShell scripts, use the Python commands below directly.

## Commands

Run code directly without a file:

```powershell
.\pylite.ps1 run -c 'print(2 + 3)'
```

For multiple lines in PowerShell:

```powershell
$code = @'
let count = 1
count = count + 1
print(count)
'@
.\pylite.ps1 run -c $code
```

```sh
python -m pylite run examples/full_program.lite
python -m pylite run -c 'print(2 + 3)'
python -m pylite lex examples/demo.lite
python -m pylite lex examples/demo.lite --json
python -m pylite check examples/demo.lite
python -m pylite transpile examples/demo.lite
python -m unittest discover -s tests -v
```

Install from this repository in a fresh virtual environment (Python 3.10+):

```sh
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead:
# .\.venv\Scripts\Activate.ps1
python -m pip install .
pylite run examples/demo.lite
```

The installed commands work outside the repository; example paths remain relative to your current directory.
`check` validates syntax and analyzes declarations without execution. Definite errors return 1; possible binding errors produce warnings and return 0. Runtime checks remain active.
`transpile` shows generated Python helper calls, which require a runtime environment.

## Example

Save as `hello.lite`, then run `python -m pylite run hello.lite`:

```text
const greeting = "Hello from PyLite"
let count = 0
repeat 3 times:
    count = count + 1
    print(greeting, count)
end loop
if count == 3:
    print("Done")
end if
count |> double_value |> print
```

## Python API

```python
from pylite import Lexer, Parser, check, run, transpile
tokens = Lexer('let count = 1\n').tokenize()
tree = Parser('print(1 + 2)').parse()
runtime = run('let count = 1\ncount = count + 1\nprint(count)')
assert runtime.variables['count'] == 2
analysis = check('print(missing)')
assert analysis.errors  # No code was executed.
```

Every `run` has fresh variables. Pass `output=some_function` to capture printed lines.
Language errors expose source line and column with a caret when source text is available. Catchable recursion/memory failures become `ResourceError` diagnostics; this is not a hard resource sandbox.

## Structure

| File | Responsibility |
| --- | --- |
| `pylite/lexer.py` | Character scanning, tokens, lexical errors |
| `pylite/parser.py` | Grammar, blocks, located syntax nodes |
| `pylite/compiler.py` | Guarded Python AST generation |
| `pylite/semantic.py` | Definite/possible binding analysis for `check` |
| `pylite/diagnostics.py` | Shared source diagnostics and resource errors |
| `pylite/runtime.py` | Bindings, constants, operations, builtins, execution |
| `pylite/__main__.py` | Commands and error exit codes |
| `tests/` | Lexer, parser, runtime, and CLI tests |
| `.github/workflows/ci.yml` | Install and test on Python 3.10–3.14, Linux and Windows |

See [language rules and grammar](docs/language.md) for exact semantics and decisions resolving the original reference's gaps. Version 1.1 extends the v1.0 syntax with float/scientific literals, single quotes, and nested multiline comments; user-defined functions, imports, collections, `else`, and logical operators are future features.

The runtime exposes only PyLite helpers to generated code. It is an educational environment, not a resource-limited sandbox for hostile programs. Ctrl+C interrupts execution.

## Extensions beyond v1.0

```text
#| Multiline comment
   #| Nested comment |#
|#
const pi = 3.14
let scale = 1e3
print('It\'s PyLite', pi, scale, 2.5e-2)
```

Both quote styles accept `\n`, `\t`, `\r`, `\"`, `\'`, and `\\`.
Decimal points require digits on both sides; exponents require digits.
`repeat` still requires an integer count (`2.0` is a float and is rejected).

```sh
python -m pylite run examples/extensions.lite
python -m pylite lex examples/extensions.lite --json
python -m pylite check examples/extensions.lite
python -m pylite check examples/semantic_warning.lite
pylite run -c "print(3.14, 1e3, 2.5e-2)"
python tests/installed_smoke.py
```

The warning example runs successfully, but `check` conservatively warns that its
conditional declaration might not execute. It recognizes literal booleans and
literal integer repeat counts, without executing or folding arbitrary expressions.
See [the current reference](docs/language.md) and [verification results](docs/verification.md).

## Canonical workspace

This project lives at `C:\Users\kingo\Documents\PyLite` (WSL:
`/mnt/c/Users/kingo/Documents/PyLite`). Open that root folder in VS Code.
See the [workspace migration report](docs/migration.md) for preserved APIs,
conflict decisions, and the original destination documentation.
The distribution name is `pylite-lang`; the command remains `pylite`.
The source-located syntax-tree command is also available:

```sh
python -m pylite parse examples/demo.lite
python -m pylite run examples/tutorial.lite
```


## Manual testing

Run `python -m pylite run examples/manual_test.lite` for a tour of the implemented
language. Its expected output is saved in `examples/manual_test.expected.txt` and
shown in the [manual testing guide](docs/manual-testing.md).
See the [current readiness report](docs/readiness.md) for verified results and
platform limitations; older verification sections are historical records.
