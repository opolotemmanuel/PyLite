# Readiness verification — 2026-10-18

**Verdict: ready with limitations for manual testing.** This is evidence for the
checks below, not a proof that every possible program is correct.

## Scope and environment

Only the confirmed VS Code project was reviewed and changed:

- Windows: `C:\Users\kingo\Documents\PyLite`
- WSL: `/mnt/c/Users/kingo/Documents/PyLite`
- Host: Linux / WSL2, kernel `6.18.54.1-microsoft-standard-WSL2`
- Interpreter: Python **3.14.4**

Read the README, language reference, project instructions, development guide,
migration notes, and historical verification record. Reviewed the active lexer,
shared syntax parser, guarded AST compiler, semantic analyzer, runtime, CLI,
launcher and retained compatibility APIs. No other project copy was used.
Existing unrelated changes were retained. Nothing was pushed or published.

## Installation actually verified

Created a fresh ignored `.venv-verify` in this project. This host lacks ensurepip,
so the environment was created with `python3 -m venv --without-pip .venv-verify`
and pip was bootstrapped from PyPA's get-pip.py. Then executed:

```sh
.venv-verify/bin/python -m pip install .
.venv-verify/bin/python tests/installed_smoke.py
.venv-verify/bin/python -m pip check
```

Installation built and installed **pylite-lang 1.1.0**. Isolated Python imports
resolved to:

```text
/mnt/c/Users/kingo/Documents/PyLite/.venv-verify/lib/python3.14/site-packages/pylite/__init__.py
```

Distribution origin metadata was `file:///mnt/c/Users/kingo/Documents/PyLite`.
The smoke check removes PYTHONPATH/PYTHONHOME and executes the installed module
with `-I` and the installed entry point outside the checkout. Both passed.
Package execution uses the installed package and Python standard library;
inspection found no Codex-specific interpreter paths or external project imports.
Pip reported **no broken requirements**. Build tooling required network access;
PyLite has no external runtime dependencies. The ignored environment is a Linux
virtual environment, not a Windows Python environment.

## Automated and direct execution results

Baseline: **140 collected, 137 passed, 0 failed, 3 skipped**.
After changes: **145 collected, 142 passed, 0 failed, 3 skipped** with:

```sh
.venv-verify/bin/python -m unittest discover -s tests -v
```

All pre-existing test methods remain. Five meaningful regression/manual tests
were added; no assertions were weakened. Skips are the three Windows-only
launcher tests. Existing tests exercise syntax nodes, native/guarded AST,
precise diagnostics and fallback behavior, bindings, builtins, precedence,
blocks, pipelines, literals/escapes, nested comments, line endings and resources.

All seven requested commands were executed against actual repository filenames:

```sh
python -m pylite lex examples/demo.lite
python -m pylite lex examples/demo.lite --json
python -m pylite check examples/demo.lite
python -m pylite transpile examples/demo.lite
python -m pylite run examples/demo.lite
python -m pylite run examples/full_program.lite
python -m pylite run -c 'print(2 + 3)'
```

Successful exits were accompanied by output checks: JSON was decoded, token and
helper output was inspected, and the complete demo/full-program output was
asserted. Installed `pylite` commands were also tested. Inline output was exactly
`5` followed by a newline.

The standalone acceptance program was executed through both isolated installed
module and installed executable, asserting exactly:

```text
Hello 1
Hello 2
Hello 3
Done
6
```

The manual program's full output was asserted through API execution, generated
Python, module CLI and installed executable. Other direct checks covered the
extensions example, tutorial and semantic-warning example. See the
[manual guide](manual-testing.md) and
[exact expected output](../examples/manual_test.expected.txt).

## Error and semantic-check evidence

A direct matrix of 14 invalid programs was run through the module and again
through both installed entry points. Every case returned 1, matched its expected
source line/column and omitted Python tracebacks:

- Undeclared read and assignment; constant reassignment; duplicate declaration.
- Malformed scientific literal, invalid character, unclosed single-quoted string
  and unclosed multiline comment.
- Missing colon, mismatched block ending, negative and floating repeat counts.
- Unknown function and division by zero.

The automated suite also covers boolean/string/fractional repeat counts, invalid
escapes and other malformed literals, missing endings, nested comment positions,
LF/CRLF/CR, and catchable recursion/memory/rendering failures.

Through both installed entry points, `check` was given a file containing a print
marker, division by zero and a large repeat. It returned the documented static
success summary without executing any statements. Conditional-binding uncertainty
produced SemanticWarning with status 0. Definite errors returned 1.
`check` intentionally does not validate runtime types, all argument arities,
division safety or termination; a clean check does not promise runtime success.

## Confirmed defects fixed

1. Known nested repeat blocks were re-analyzed twice even when their binding
   state did not change, making harmless static checks exponential. Twelve nested
   loops caused **8,191 block visits** before the fix, and **13** afterward.
   A stable binding state now skips the redundant second pass. A separate
   regression verifies that repeated declarations are still diagnosed when
   bindings change; execution semantics are unchanged.
2. The retained strict analyzer's unknown-function hint listed only two functions
   although it recognizes six. The hint now derives its list from the actual
   builtin table, with a regression test.

Documentation now distinguishes syntax nodes from guarded AST generation,
filename/span and fallback diagnostics, the reserved compiler prefix, historical
verification, and the current compatibility APIs.

## Files changed by this verification

- `pylite/semantic.py`, `pylite/binding_checks.py`
- `tests/test_readiness.py` (new)
- `examples/manual_test.lite`, `examples/manual_test.expected.txt` (new)
- `.gitignore` (ignore `.venv-verify/`)
- `README.md`, `examples/README.md`, `docs/README.md`
- `docs/language.md`, `docs/verification.md`
- `docs/manual-testing.md`, `docs/readiness.md` (new)
- `docs/repository-layout.md` (identify the unused historical scanner)

## Remaining limitations and unperformed checks

- Windows/PowerShell launcher execution was not performed on this Linux host;
  three launcher tests are skipped. The launcher was inspected and has no
  Codex-specific interpreter dependency. Windows results remain unverified.
- Python 3.10–3.13 and remote CI were not executed in this run. The advertised
  version matrix is configured, not proven by this local run.
- The native `Transpiler` / strict `SemanticAnalyzer` are retained compatibility
  APIs. Native Python truthiness/operators and strict legacy analysis differ
  from the guarded CLI semantics. Use `run` or package-level `transpile` to test
  the documented language.
- Root `lexer_core.py` is an unused historical scanner skeleton with its own
  `#[ ... ]#` comment assumptions. It is not imported or shipped as the installed
  language lexer. The active lexer is `pylite/lexer.py`, with nested `#| ... |#`.
  The historical file was left intact.
- Floats follow host rounding/underflow. Nonfinite literals are rejected, but
  arithmetic can produce nonfinite values. No execution time/memory budget is
  enforced; fatal OS termination cannot be caught.
- Classes, imports, collections, user-defined functions, else and logical
  operators remain outside the documented implementation.

Use the [manual testing guide](manual-testing.md) for copyable WSL and Windows
terminal commands. Expected manual output is stored beside the example and
asserted by the regression suite.
