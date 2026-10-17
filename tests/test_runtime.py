"""Tests for PyLite transpilation and execution."""

import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path

from pylite.runtime import run, PyLiteRuntimeError
from pylite.symbols import SemanticError


class RuntimeTests(unittest.TestCase):
    def execute(self, source):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            variables = run(source)
        return output.getvalue(), variables

    def test_empty_program(self):
        output, variables = self.execute("")
        self.assertEqual(output, "")
        self.assertEqual(variables, {})

    def test_arithmetic_and_assignment(self):
        output, variables = self.execute(
            "let count = 2 + 3 * 4\n"
            "count = count - 1\n"
            "print(count)\n"
        )
        self.assertEqual(output, "13\n")
        self.assertEqual(variables["count"], 13)

    def test_division(self):
        _, variables = self.execute("let value = 5 / 2\n")
        self.assertEqual(variables["value"], 2.5)

    def test_conditionals(self):
        output, _ = self.execute(
            'if true:\nprint("if")\nend if\n'
            'unless false:\nprint("unless")\nend unless\n'
            'if false:\nprint("hidden")\nend if\n'
        )
        self.assertEqual(output, "if\nunless\n")

    def test_pipeline(self):
        output, _ = self.execute("10 |> double_value |> print\n")
        self.assertEqual(output, "20\n")

    def test_repeat(self):
        output, variables = self.execute(
            "let count = 0\n"
            "repeat 3 times:\n"
            "count = count + 1\n"
            "end loop\n"
            "print(count)\n"
        )
        self.assertEqual(output, "3\n")
        self.assertEqual(variables, {"count": 3})

    def test_nested_loops(self):
        _, variables = self.execute(
            "let count = 0\n"
            "repeat 2 times:\n"
            "repeat 3 times:\n"
            "count = count + 1\n"
            "end loop\n"
            "end loop\n"
        )
        self.assertEqual(variables["count"], 6)

    def test_repeat_count_evaluated_once(self):
        _, variables = self.execute(
            "let count = 3\n"
            "let steps = 0\n"
            "repeat count times:\n"
            "count = 0\n"
            "steps = steps + 1\n"
            "end loop\n"
        )
        self.assertEqual(variables["steps"], 3)

    def test_zero_repeat(self):
        output, _ = self.execute(
            'repeat 0 times:\nprint("hidden")\nend loop\n'
        )
        self.assertEqual(output, "")

    def test_repeated_declaration_rejected(self):
        for keyword in ("let", "const"):
            with self.subTest(keyword=keyword):
                with self.assertRaisesRegex(
                    PyLiteRuntimeError,
                    "Variable 'value' was declared more than once",
                ):
                    self.execute(
                        "repeat 2 times:\n"
                        f"{keyword} value = 7\n"
                        "end loop\n"
                    )

    def test_declaration_in_single_iteration_loop(self):
        for keyword in ("let", "const"):
            with self.subTest(keyword=keyword):
                output, variables = self.execute(
                    "repeat 1 times:\n"
                    f"{keyword} value = 7\n"
                    "print(value)\n"
                    "end loop\n"
                )
                self.assertEqual(output, "7\n")
                self.assertEqual(variables, {"value": 7})

    def test_separate_runs_have_independent_declarations(self):
        self.assertEqual(run("let value = 7\n"), {"value": 7})
        self.assertEqual(run("let value = 9\n"), {"value": 9})

    def test_invalid_repeat_counts(self):
        for expression in ("-1", "true", '"three"', "3 / 2"):
            with self.subTest(expression=expression):
                with self.assertRaisesRegex(
                    PyLiteRuntimeError, "nonnegative integer"
                ):
                    self.execute(
                        f"repeat {expression} times:\nend loop\n"
                    )

    def test_division_by_zero(self):
        with self.assertRaisesRegex(
            PyLiteRuntimeError, "Cannot divide by zero"
        ):
            self.execute("print(1 / 0)\n")

    def test_incompatible_operands(self):
        with self.assertRaisesRegex(
            PyLiteRuntimeError, "incompatible values"
        ):
            self.execute('print("hello" - 1)\n')

    def test_constant_reassignment_rejected(self):
        with self.assertRaisesRegex(SemanticError, "Cannot reassign"):
            self.execute("const limit = 3\nlimit = 4\n")

    def test_reserved_compiler_name(self):
        with self.assertRaisesRegex(SemanticError, "reserved"):
            self.execute("let __pylite_repeat = 2\n")

    def test_tutorial_cli(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                sys.executable, "-m", "pylite", "run",
                "examples/tutorial.lite",
            ],
            cwd=root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            result.stdout,
            "Hello, PyLite!\n1\n2\n3\nLoop completed\nTarget reached\n6\n",
        )

    def test_run_cli(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                sys.executable, "-m", "pylite", "run",
                "examples/demo.lite",
            ],
            cwd=root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "Passed\n20\n" + "Executing step\n" * 5,
        )


if __name__ == "__main__":
    unittest.main()
