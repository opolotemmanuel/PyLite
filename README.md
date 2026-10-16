# PyLite 1.0

PyLite includes a lexer, parser, semantic analyzer, Python AST transpiler,
and runtime, compatible with Python 3.10+ with no external dependencies.
Python 3.11+ debug ranges (enabled by default) provide precise runtime spans.

From this folder:

```sh
python3 -m pylite lex examples/demo.lite
python3 -m pylite lex examples/demo.lite --json
python3 -m pylite parse examples/demo.lite
python3 -m pylite check examples/demo.lite
python3 -m pylite run examples/demo.lite
python3 -m unittest discover -s tests -v
```

Python API:

```python
from pylite import Lexer
from pylite.parser import Parser
from pylite.runtime import run

tokens = Lexer('let count = 1\n').tokenize()
program = Parser('let count = 1\n', filename='demo.lite').parse()
values = run('let count = 1\nprint(count)\n', filename='demo.lite')
```

## Continuous integration

[GitHub Actions](.github/workflows/ci.yml) runs the unittest suite and demo on
Python 3.10, 3.11, and 3.12 for pushes to `main`, pull requests targeting `main`,
and manual dispatch. Python 3.11 and 3.12 also run the suite with debug ranges
disabled. Matrix jobs run independently, with no external Python packages needed.

## Language rules

- Keywords: `let const if unless repeat times end loop print true false`.
  Identifiers use ASCII letters or underscore followed by ASCII letters,
  digits, or underscores. Keywords are case-sensitive.
- Integers contain decimal digits; unary `+` and `-` are supported. Booleans
  and double-quoted strings are values. Strings decode `\n`, `\t`, `\r`,
  `\"`, and `\\`. Raw newlines and unknown escapes are errors.
- Arithmetic precedence is unary, then `* /`, then `+ -`, then comparisons,
  then pipelines (`value |> double_value |> print`). Arithmetic is left
  associative. Division uses Python's true division. Comparisons are
  `== != < > <= >=`; chained comparisons are rejected.
- `let` declares mutable variables, `const` declares constants, and assignment
  requires an existing mutable binding. Declarations are program-wide;
  declarations inside optional blocks may be uninitialized afterward.
  Redeclaration is rejected both statically and during repeated execution.
  Builtin function names and the `__pylite_` prefix are reserved.
- Builtins are `print(...)` and `double_value(number)`. Pipelines pass one
  argument. `repeat count times:` requires a nonnegative integer (not a
  boolean), evaluates its count once, and closes with `end loop`.
  `if condition:` and `unless condition:` close with `end if` and `end unless`.
- Indentation is ignored. Explicit `end` blocks delimit bodies, so no
  `INDENT` or `DEDENT` tokens are emitted. `#` starts a line comment.
  Newlines separate statements; parentheses allow multiline expressions.
  LF, CRLF, and CR are supported. The CLI accepts UTF-8 with an optional BOM.
- Floats as literals, scientific notation, single-quoted strings, multiline
  comments, user-defined functions, and implicit declarations are unsupported.

## Source locations and diagnostics

Tokens have one-based line and visual column numbers and zero-based Unicode
character offsets. Parsed nodes retain optional `span` and `focus` metadata;
spans include exclusive end offsets and end positions. Program nodes retain
source text and filename. Existing positional node constructors and structural
equality remain compatible; manually constructed nodes may omit locations.
The `parse` JSON output includes the new metadata.

Semantic errors identify the relevant variable or function. Runtime errors for
zero division, incompatible operands, invalid repeat counts, repeated declarations,
and invalid `double_value` arguments identify the originating `.lite` operation,
including failures raised by runtime helpers. For example:

```text
PyLite RuntimeError [demo.lite, Line 3, Col 7]:
Cannot divide by zero. Check the value after '/'.
3 | print(10 / 0)
          ^^^^^^
```

Columns and carets use four-column tab stops, matching the lexer. Python AST
columns use UTF-8 byte offsets internally, so non-ASCII string content before
an operation does not shift its diagnostic. CLI language errors go to stderr
with exit status 1 and no internal traceback; stdout printed before a runtime
failure is preserved. Unexpected compiler or helper defects are allowed to
propagate for debugging.

Limits: a multiline span highlights only its first line. A helper-generated
operation may highlight its entire declaration or repeat header. Columns count
Unicode code points after tab expansion, not terminal display widths for wide
characters or combining marks.

On Python 3.10, or when Python 3.11+ debug ranges are unavailable (for example,
with `-X no_debug_ranges`), runtime diagnostics fall back to the original
`.lite` traceback line, including its source text. These line-only diagnostics
omit the column and caret rather than inventing an exact location:

```text
PyLite RuntimeError [demo.lite, Line 3]:
Cannot divide by zero. Check the value after '/'.
3 | print(10 / 0)
```

The fallback also applies to runtime helper errors and preserves the same CLI
stderr, exit status, and stdout behavior.

Hand-built trees without source metadata retain synthetic AST positions and are intended for structural/compiler use, not source diagnostics.
Lexical and parse errors retain their existing line/column format.
