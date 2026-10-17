# PyLite 1.1 rules and grammar

Version 1.1 preserves the v1.0 core and adds literal/comment extensions plus a
non-executing semantic checker. No separate original proposal is present in this
checkout. The former reference excluded floats, single quotes and multiline
comments because their syntax was unspecified; the extensions below now define
them explicitly. Classes, imports, collections and user-defined functions are
not part of this language.

## Lexical rules

Keywords: `let const if unless repeat times end loop print true false`. `loop`
was added for `end loop`, although omitted in the original keyword list.
Keywords are case-sensitive. Identifiers match `[A-Za-z_][A-Za-z0-9_]*`.
Builtin names cannot be redeclared or used as variable bindings. The
`__pylite_` prefix is reserved for compiler internals.

Integers contain ASCII digits; leading zeros are decimal. Minus is a separate
unary/subtraction token. **1.1 extensions:** decimal floats such as `3.14`, and
scientific notation such as `1e3`, `2.5e-2`, `12E+2`. Numeric syntax:

```ebnf
digits = digit { digit } ;
integer = digits ;
float = digits "." digits [ exponent ] | digits exponent ;
exponent = ("e" | "E") [ "+" | "-" ] digits ;
```

A decimal point requires digits on both sides: write `0.5` and `1.0`, not `.5`
or `1.`. Underscores, numeric/name concatenation, missing exponent digits and
extra decimal points are errors at the start of the literal. Floats use Python's
binary floating-point representation (rounding and underflow apply). Literals
that overflow to infinity, such as `1e309`, are rejected. Exponent notation
always produces a `FLOAT`, even when its mathematical value is integral.
Integers remain arbitrary precision within host memory limits.

Strings use double quotes or **1.1 extension:** single quotes. Both styles
support `\n`, `\t`, `\r`, `\"`, `\'`, and `\\`; contents may contain Unicode.
The opening quote must match the closing quote. The other quote can appear
unescaped. Raw CR/LF, unknown escapes, and unclosed strings are errors at the
opening quote. Triple quotes and multiline strings are not supported.

Comments use `#` through line end. **1.1 extension:** multiline comments use
`#| ... |#` because no delimiters were defined by the supplied reference. They
nest, and an unclosed comment points at its outer opening delimiter. An unmatched
`|#` is an error. Delimiters inside a string or line comment are ordinary text;
inside a multiline comment, all text except delimiters and CR/LF is ignored.
Comments separate tokens; they never join identifiers or numbers. Newlines in
comments remain statement boundaries, except inside parentheses where all
newlines are ignored. A former line comment starting with `#|` now begins a
multiline comment; use `# #|` when you want that literal text in a line comment.

Indentation is ignored; tabs use four-column stops for diagnostics. LF, CRLF,
and CR are accepted. CLI source encoding is UTF-8 with optional BOM.
Parenthesized expressions can span lines.

Operators: `= + - * / == != < > <= >= |>`. Delimiters: `( ) : ,`.
Longer operators match first. Tokens carry `kind`, `lexeme`, `value`, `line`,
`column`, `start`, and `end`. Literal token kinds are `INTEGER`, `FLOAT`, `STRING`,
`TRUE`, `FALSE`. Positions are one-based; offsets are zero-based character indices
with exclusive ends. Streams finish with `EOF`.

## Grammar

```ebnf
program = { statement } EOF ;
statement = declaration | assignment | conditional | repetition | expression_line ;
declaration = ("let" | "const") identifier "=" expression line_end ;
assignment = identifier "=" expression line_end ;
conditional = "if" expression ":" NEWLINE { statement } "end" "if" line_end
            | "unless" expression ":" NEWLINE { statement } "end" "unless" line_end ;
repetition = "repeat" expression "times" ":" NEWLINE { statement } "end" "loop" line_end ;
expression_line = expression line_end ;
expression = comparison { "|>" function_name } ;
comparison = addition [ ("==" | "!=" | "<" | ">" | "<=" | ">=") addition ] ;
addition = multiplication { ("+" | "-") multiplication } ;
multiplication = unary { ("*" | "/") unary } ;
unary = ("+" | "-") unary | primary ;
primary = integer | float | string | "true" | "false" | identifier
        | function_name "(" [ expression { "," expression } ] ")"
        | "(" expression ")" ;
function_name = identifier | "print" ;
line_end = NEWLINE | EOF ;
```

Blank lines/comments may separate statements. Final newline is optional. Block
headers require a colon and newline. Empty blocks are valid. Trailing argument
commas and chained comparisons are rejected. Precedence, highest first:
calls/parentheses, unary signs, multiplication/division, addition/subtraction,
comparison, pipeline. Arithmetic and pipelines associate left to right.
Arguments evaluate left to right. The original left-to-right evaluation goal is
interpreted as pipeline sequencing; arithmetic retains standard precedence.

## Runtime semantics (preserved)

Bindings share one program-wide scope. Blocks introduce no scopes. Declarations
execute only when reached. Each name can be declared once per run; repeated
declaration inside a loop is an error. Declare accumulators before the loop and
assign inside it. Reading/assigning an undeclared name is an error. `let` allows
reassignment; `const` forbids it. Binding types are dynamic. Checks happen during
execution, including nested blocks. Right-hand expressions execute before
assignment updates or binding validation.

Conditions must be booleans. Repeat counts are non-negative integers; zero means
no iterations. This preserves the existing broadening of the reference's
'positive integer' wording. Booleans and floats (including `2.0`) are rejected.
Arithmetic accepts integers and floats, excluding booleans. `/` produces true
division. `+` also joins two strings. Ordering compares two numbers or two strings.
Equality allows numeric cross-type comparison, while `true == 1` is false.
Floating-point operations follow the host behavior; operations can produce
nonfinite values, even though nonfinite literals are rejected. Host numeric
exceptions become source-located runtime errors.

Pipelines call a named function with one argument: `x |> f |> g` means `g(f(x))`.

| Builtin | Behavior |
| --- | --- |
| `print(...)` | Prints space-separated values; booleans display as `true`/`false` |
| `double_value(x)` | Doubles a number; provided for the original example |
| `abs(x)` | Python absolute value |
| `len(x)` | String length |
| `str(x)` | Display text conversion |
| `int(x)` | Python integer conversion; fractional numbers truncate toward zero |

Conversion builtins use Python argument validation. `print` returns Python
`None`; there is no null literal. Unknown functions and invalid arguments report
source-located errors. The additional `abs`, `len`, `str`, `int` helpers remain
implementation decisions rather than claimed original v1.0 requirements.

## Semantic analysis (1.1)

`check` parses and analyzes declarations without executing any program code,
including print calls, loop counts or conditions. `check(source)` in the Python
API returns an `Analysis` with `tree`, `errors` and `warnings` lists.

The dedicated analyzer tracks possible binding states: absent, mutable, constant.
A read/assignment with no possible declaration is an error; a declaration of an
already definite binding is an error; assigning a definite constant is an error.
Builtin-name misuse and unknown functions are also errors. Keywords in binding
positions remain syntax errors. An error inside a potentially reached block
means the operation is invalid whenever that point is reached, even if the whole
block might not execute. Analysis can report multiple diagnostics.

Literal `true`/`false` (including `unless`) select the reached branch; other
conditions join the branch with the path that skips it. Literal non-negative
integer counts, with unary signs/parentheses, distinguish zero, one, and repeated
iterations. Literal-zero loops and literal-false branches contribute no bindings
and are not semantically traversed (their syntax is still parsed). A second pass
through a known repeated loop detects duplicate declarations without unrolling
large counts. Unknown loop counts join the zero path and back edge until binding
sets stabilize. Binding mutability cannot be changed by assignment; it is fixed by declaration.

If a binding may be absent, duplicated, or constant on some paths, `check`
reports a `SemanticWarning`, not a proof of failure. Warnings return status 0
with an explicit warning summary; definite errors return 1. A successful check
never promises execution will succeed. The analyzer intentionally does not fold
arithmetic/comparisons, propagate variable values, correlate separate conditions,
or prove runtime types, argument validity, division safety or loop termination.
Thus even `let ready=true; if ready: ...` is treated conservatively.

`run` and `transpile` retain runtime declaration checks and do not automatically
reject programs based on static analysis. This preserves existing execution
behavior and permits harmless unreachable code. Use `check` explicitly for the
additional analysis stage.

## Architecture, diagnostics and commands

Source → lexer → recursive descent syntax parser → located syntax nodes →
guarded Python AST (`compiler.Compiler`). For `check`, a dedicated
semantic analyzer inspects that AST without invoking helpers. For `run`, Python
compilation and execution use runtime helpers. Source is not interpolated into
Python code. Helpers receive source positions; generated code exposes no Python
builtins beyond the runtime helpers.

Lexical, syntax, semantic and runtime diagnostics use `PyLite <category>` with
line/column information and a source excerpt/caret when available. File-based
semantic and runtime diagnostics also identify the filename. On Python 3.10 or
with debug ranges disabled, runtime diagnostics can fall back to the source line
and omit the column/caret rather than inventing a precise span. Source splitting
preserves Unicode characters inside strings. Catchable recursion and memory
failures are reported as `ResourceError` without a CLI Python traceback. Known
helper/parser positions are used where available; other host failures fall back
to line 1, column 1. Python's very-large-integer rendering limit remains a host
limit; it is reported gracefully. Fatal OS termination, stack exhaustion below
Python, and an inability to allocate a diagnostic cannot be guaranteed catchable.
No time, iteration or memory budget is imposed; this is not a hostile-code sandbox.

`lex` lists tokens; `run` executes; `check` validates syntax and analyzes bindings;
`transpile` displays helper-based Python code. Generated Python can execute with
`Runtime.environment()` through the Python API.
Exit codes: 0 success (possibly semantic warnings), 1 source/file/runtime/resource
error, 2 CLI usage error, 130 interruption.


## Compatibility APIs

This reference describes CLI execution, package-level `run`/`transpile`, and
`check`. `pylite.parser.Parser` (also `pylite.SyntaxParser`) returns located
syntax nodes. Package-level `pylite.Parser` lowers that same tree to guarded AST.
There is one syntax parser.

The retained `pylite.transpiler.Transpiler` and `SemanticAnalyzer` APIs are legacy
compiler/structural interfaces, not the CLI execution path. The native compiler
uses direct Python operators/truthiness and strict legacy binding analysis; these
are not equivalent to guarded runtime semantics (for example, Python treats
`true == 1` as true and accepts truthy integer conditions). Its output expects
its own native helper environment. To execute the documented language, use
`run` or package-level `transpile` with `Runtime.environment()`. See
[development](development.md) for the API distinction.
