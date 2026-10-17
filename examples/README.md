# Example programs

Run commands from the project root, with Python 3.10+ or an activated environment.

| Program | Demonstrates |
| --- | --- |
| [manual_test.lite](manual_test.lite) | Complete manual tour; [exact expected output](manual_test.expected.txt) |
| [demo.lite](demo.lite) | Constants, mutable bindings, conditions, loops, and pipelines |
| [full_program.lite](full_program.lite) | A longer demonstration of the core language |
| [extensions.lite](extensions.lite) | Floats, scientific notation, single quotes, escapes, and nested comments |
| [semantic_warning.lite](semantic_warning.lite) | A conditional declaration that produces a static warning but runs successfully |

```sh
python -m pylite run examples/demo.lite
python -m pylite run examples/full_program.lite
python -m pylite run examples/extensions.lite
python -m pylite check examples/semantic_warning.lite
python -m pylite run examples/semantic_warning.lite
```

The extension example has this expected output:

```text
Literals: 3.14 1000.0 0.025
It's PyLite say "hello" backslash: \
0.05
Nested blocks still work: 2
```

See the [setup guide](../docs/getting-started.md) and
[language reference](../docs/language.md).
