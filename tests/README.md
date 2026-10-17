# Test guide

Run the full suite from the project root:

```sh
python -m unittest discover -s tests -v
```

| File | Coverage |
| --- | --- |
| `test_lexer.py` | Tokens, values, positions, lexical errors, and JSON CLI |
| `test_workspace_runtime.py` | Preserved destination execution and tutorial regressions |
| `test_parser.py`, `test_semantic.py`, `test_diagnostics.py` | Preserved workspace syntax-node APIs and precise diagnostic coverage |
| `test_runtime.py` | Parsing, bindings, operations, blocks, builtins, and core CLI |
| `test_acceptance.py` | Original acceptance output, line endings, indentation, and diagnostics |
| `test_extensions.py` | Additional literals/comments, semantic analysis, and resource handling |
| `test_launcher.py` | Windows PowerShell launcher, interpreter selection, quoting, and exit status |
| `installed_smoke.py` | Explicit installed-package check outside the checkout |

For a focused run, for example:

```sh
python -m unittest discover -s tests -p test_extensions.py -v
```

Windows launcher tests are skipped unless Windows and PowerShell are available.
The installation smoke check is separate from unittest discovery:

```sh
python -m pip install .
python tests/installed_smoke.py
python -m pip check
```

See the [development guide](../docs/development.md) for CI and implementation
notes, and the [verification record](../docs/verification.md) for recorded results.
