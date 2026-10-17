# Verification — 2026-10-17

For the current canonical workspace, read the [2026-10-18 readiness report](readiness.md).
The installation paths and Git limitations below describe earlier historical runs.

The first section records the historical v1.0 baseline. The **PyLite 1.1
extension verification** section below supersedes its feature exclusions and
syntax-only `check` description.

Verified the supplied checkout on Linux with Python 3.14.4 in a fresh virtual
environment at `/tmp/pylite-verify-venv`. No agent instructions were visible.
The visible `.git` directory was empty, so clone provenance and a Git diff could
not be verified. No changes were pushed or published.

## Installation and execution

The host lacked ensurepip/pip. Created the environment with `python3 -m venv`
(the interpreter was created but ensurepip failed), then bootstrapped pip from
PyPA's get-pip.py into that environment. `python -m pip install .` successfully
built and installed pylite-language 1.0.0 with isolated setuptools build dependencies.
Network access was needed for the installer and build tooling; the language has
no external runtime dependencies.

All requested commands passed with the actual example filenames:

```sh
python -m pylite lex examples/demo.lite
python -m pylite lex examples/demo.lite --json
python -m pylite check examples/demo.lite
python -m pylite transpile examples/demo.lite
python -m pylite run examples/demo.lite
python -m pylite run examples/full_program.lite
python -m pylite run -c 'print(2 + 3)'
```

Also tested every command via the installed `pylite` entry point from `/tmp`,
using absolute example paths and removing PYTHONPATH/PYTHONHOME. Confirmed imports
came from the virtual environment's site-packages. Inline output was `5`.
Both examples' full output was asserted, JSON tokens were decoded, and transpiled
acceptance code was compiled and executed with Runtime.environment().

Baseline: 35 tests passed. Final: 41 tests passed, including the acceptance
program with LF/CRLF/CR, with/without indentation, and comments. Fifteen invalid
program cases checked undeclared reads/assignments, constant changes, duplicate
declarations, division by zero, unknown functions, invalid characters, unclosed
strings, missing colons, mismatched endings, invalid repeat counts and nonboolean
conditions. All returned 1, identified line/column, and omitted Python tracebacks.

Acceptance output (also asserted through both installed CLI forms):

```text
Hello 1
Hello 2
Hello 3
Done
6
```

## Fixes

- Lexer and parser diagnostics now split source only at PyLite's CR/LF line
  endings. Previously Unicode line separators allowed inside string values
  caused the diagnostic to display an unrelated source line.
- PowerShell launcher now uses Python from PATH or explicit -PythonPath, removing
  its preference for a Codex-specific interpreter location. README documents
  environment activation and installation. PowerShell execution was not tested
  on this Linux host.
- Added tests/test_acceptance.py for execution, transpilation, diagnostics,
  scope, pipeline order, escapes, and newline/indentation handling.

## Specification boundaries

The supplied README and docs/language.md are the available specification; no
separate original proposal is present to independently resolve their claims.
Confirmed core behavior includes mutable let, immutable const, declaration
checks, integer/string/boolean values, precedence/comparisons, explicit nested
blocks and left-to-right pipelines.

Existing documented decisions, preserved rather than silently changed:

| Topic | Implementation / difference |
| --- | --- |
| Floats | No float literals; division can produce floats at runtime. |
| Scientific notation | Rejected. |
| Single quotes | Rejected; strings require double quotes. |
| Multiline comments | No dedicated syntax; use # on each line. |
| Scope | Program-wide, including blocks; declarations execute when reached. Re-declaring in repeated iterations fails. |
| Zero repeats | Accepted, despite the documented original proposal saying positive integers. |
| Conditions | Require booleans; integers/strings have no implicit truthiness. |
| Builtins | print and double_value plus abs, len, str, int. Additional helpers and Python-style conversion/argument validation are implementation decisions. print returns Python None. |

No user-defined functions, imports, collections, else, or logical operators.
`check` validates syntax only; variable and type checks occur during execution.
Only Python 3.14.4 was exercised locally, not the entire advertised 3.10+ range.
The runtime is not a resource-limited sandbox. Very deep expressions/resource
exhaustion and Python's very-large-integer display limit remain host limits;
those limit errors do not necessarily have PyLite source locations.

## Reproduce locally

From the repository directory, with Python 3.10+ and venv/pip available:

```sh
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell instead: .\.venv\Scripts\Activate.ps1
python -m pip install .
python -m unittest discover -s tests -v
python -m pylite run examples/full_program.lite
pylite run examples/demo.lite
pylite run -c 'print(2 + 3)'
```


## PyLite 1.1 extension verification

Implemented the missing literals, multiline comments and semantic checking after
reviewing the code, tests, README and reference. The launcher already selected
Python from PATH or an explicit interpreter. Its invocation now also preserves
native argument quoting, with ArgumentList on PowerShell 7 and Windows CRT
quoting on Windows PowerShell 5.1.

### Features and decisions

- Float/scientific literals: `3.14`, `1e3`, `2.5e-2`, `12E+2`; digits on both
  sides of a decimal point, exponent digits mandatory, nonfinite literals rejected.
- Single-quoted strings use the same escapes as double quotes, with both quote
  escapes accepted. Unknown escapes/raw newlines/unclosed strings are errors.
- No existing multiline-comment delimiters were defined. Added nested
  `#| ... |#` comments as an explicitly documented syntax extension. Newlines
  inside comments preserve statement boundaries and raw token offsets.
- Dedicated non-executing semantic analyzer tracks absent/mutable/constant
  binding states. Definite undeclared use, duplicate declaration, constant
  assignment, builtin-name misuse and unknown functions are errors. Conditional
  declarations and unknown/zero-iteration loops never create false definite
  bindings. Possible binding errors are warnings (exit 0); definite errors return 1.
- Shared source diagnostics preserve the earlier Unicode line-splitting fix.
  Runtime errors now include source excerpts. Catchable nesting/memory failures
  become ResourceError diagnostics; token JSON rendering failures identify the
  failing token. Runtime declaration checks remain active.
- Existing scope, boolean conditions, zero-repeat behavior, builtin functions,
  and valid program execution remain unchanged. Version bumped to 1.1.0.

### Executed checks

Linux, Python **3.14.4**, fresh `/tmp/pylite-extensions-venv` (created with
`python3 -m venv --without-pip` because the host lacks ensurepip; pip was installed
into it using the previous environment's pip --python support).
`python -m pip install .` built and installed pylite-language **1.1.0** with
isolated build dependencies. The final package was reinstalled after the final
CLI diagnostic change. No developer-machine paths or PYTHONPATH are required.

```sh
python -m pip install .
python -m unittest discover -s tests -v
python tests/installed_smoke.py
python -m pip check
python -m pylite run examples/extensions.lite
python -m pylite check examples/semantic_warning.lite
python -m pylite run examples/semantic_warning.lite
```

Final suite: **71 collected, 68 passed, 3 Windows-only tests skipped**. The 41
baseline test methods remain passing; obsolete rejection cases for single quotes,
floats and scientific notation were replaced with malformed literal cases.
The new tests cover all extensions, LF/CRLF/CR positions, nested comments,
transpiled execution, uncertain declarations/constants, known/unknown nested
loops, source diagnostics, recursion, simulated memory failure and integer
rendering limits. Existing acceptance output remains exactly the original five
lines. No tests were dropped to hide failures.

`tests/installed_smoke.py` runs the installed module with isolated Python and the
installed `pylite` entry point outside the repository, removing PYTHONPATH and
PYTHONHOME. It asserts full output for both original examples and the new feature
example, checks JSON tokens, semantic checking and transpilation, and asserts
semantic error exit status. `pip check`: no broken requirements.

`examples/extensions.lite` output:

```text
Literals: 3.14 1000.0 0.025
It's PyLite say "hello" backslash: \
0.05
Nested blocks still work: 2
```

`examples/semantic_warning.lite` checks successfully with a source-located
SemanticWarning for its potentially absent binding; executing it succeeds.
This demonstrates that static uncertainty is reported without silently changing
runtime semantics.

### Files changed

- Language implementation: `pylite/lexer.py`, `pylite/parser.py`,
  `pylite/runtime.py`, `pylite/__main__.py`, `pylite/__init__.py`.
- New stages/support: `pylite/semantic.py`, `pylite/diagnostics.py`.
- Automation/packaging: `pylite.ps1`, `.github/workflows/tests.yml`, `pyproject.toml`.
- Tests: updated `tests/test_lexer.py`; added `tests/test_extensions.py`,
  `tests/test_launcher.py`, `tests/installed_smoke.py`.
- Examples: `examples/extensions.lite`, `examples/semantic_warning.lite`.
- Documentation: `README.md`, `docs/language.md`, this verification record.

### Remaining limits and platform status

CI is configured for Python **3.10–3.14 on Ubuntu and Windows**. The three Windows
launcher tests exercise both available PowerShell hosts, explicit/active Python,
working-directory independence, quoting, multiline inline source and exit status.
They were **not executed locally**: this host has neither Windows nor PowerShell.
The workflow was added locally; no remote workflow run was triggered. Python
3.10–3.13 were not locally available. Their results remain pending CI.

Semantic analysis is conservative: no general value propagation, arithmetic
folding, branch correlation, type checking, termination proof or resource budget.
Warnings can occur for valid programs. Runtime errors can occur after a clean
check (for example division by zero). Host memory/recursion limits are handled
where catchable, but fatal OS termination cannot be intercepted. Some resource
errors use line 1, column 1 when a more precise position is unavailable. Floats
have ordinary host rounding/underflow and can become nonfinite through arithmetic.
No unrelated syntax such as classes/imports/lists/functions was added.

Git status still fails because visible Git metadata is empty/unrecognized.
A local commit could not be created. Nothing was pushed or published.
