# PyLite 1.0 lexer

A working lexer for your language concept, requiring Python 3.10+ and no external packages. This is the lexical stage; it does not yet execute PyLite programs.

From this folder:

```sh
python -m pylite lex examples/demo.lite
python -m pylite lex examples/demo.lite --json
python -m unittest discover -s tests -v
```

Python API:

```python
from pylite import Lexer
tokens = Lexer('let count = 1\n').tokenize()
```

## Rules and decisions

- Keywords: `let const if unless repeat times end loop print true false`. `loop` is added because `end loop` requires it.
- Identifiers use ASCII letters or underscore, followed by ASCII letters, digits, or underscores; keywords are case-sensitive.
- Integers contain decimal digits. Negative numbers produce `MINUS` then `INTEGER`, allowing a parser to distinguish negation from subtraction.
- Boolean tokens have Python boolean values. Double-quoted strings decode `\n`, `\t`, `\r`, `\"`, and `\\`. Raw newlines and unknown escapes are errors.
- All documented operators are supported with longest-match recognition. Parentheses, colon, and comma support calls and the examples' block syntax.
- Indentation is ignored. Tabs use four-column tab stops for diagnostics. Newlines are retained as statement boundaries; a parser can ignore them inside parentheses.
- `#` begins a comment through line end. LF, CRLF, and CR are supported. The CLI accepts UTF-8 with an optional BOM.
- Each token carries its kind, original lexeme, decoded value, one-based line and visual column, and zero-based start/end offsets. End offsets are exclusive. Every stream ends in `EOF`.
- `end if`, `end unless`, and `end loop` are separate keyword tokens; a parser checks valid combinations and nesting.

## Reference ambiguities

The main v1.0 specification defines integers and double-quoted strings, while the team breakdown requests floats, scientific notation, and single quotes. This implementation follows the main specification. Multiline comments have no delimiter defined, so only `#` line comments are supported. These extensions need syntax decisions before implementation.

The manual says implicit assignment is invalid but also shows reassignment of a declared `let` variable. Interpret this as: assignment is valid after declaration. Declaration checks, scope, reserved names in binding positions, and `const` reassignment belong to the parser or semantic/runtime stages, not the lexer.

Arithmetic precedence, pipeline precedence, available callable functions, division semantics, and zero/negative repeat counts still need definition before a complete interpreter can be built. The example's `double_value` requires a builtin or a future function-definition feature.

## Next stages

1. Define expression precedence and statement grammar.
2. Parse tokens into syntax nodes and validate block endings.
3. Check declarations and mutable/immutable bindings.
4. Translate nodes into Python AST with a controlled set of builtins.
5. Execute and translate runtime errors into PyLite diagnostics.

The explicit `end` blocks mean the lexer deliberately emits no `INDENT` or `DEDENT` tokens.
