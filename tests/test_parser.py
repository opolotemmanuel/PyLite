"""Tests for PyLite syntax parsing."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

from pylite.keywords import ReservedWordError
from pylite.nodes import (
    Assignment, Binary, Call, Conditional, Declaration,
    Literal, Name, Repeat, Unary,
)
from pylite.parser import Parser, ParseError


class ParserTests(unittest.TestCase):
    def parse(self, source):
        return Parser(source).parse()

    def test_empty_program(self):
        self.assertEqual(self.parse("").statements, [])

    def test_declarations_and_assignment(self):
        program = self.parse(
            "const limit = 3\n"
            "let count = 1\n"
            "count = count + 1\n"
        )
        self.assertEqual(
            program.statements[0],
            Declaration("limit", Literal(3), False),
        )
        self.assertEqual(
            program.statements[1],
            Declaration("count", Literal(1), True),
        )
        self.assertEqual(
            program.statements[2],
            Assignment(
                "count",
                Binary(Name("count"), "+", Literal(1)),
            ),
        )

    def test_arithmetic_precedence(self):
        value = self.parse("let x = 2 + 3 * 4\n").statements[0].value
        self.assertEqual(
            value,
            Binary(
                Literal(2), "+",
                Binary(Literal(3), "*", Literal(4)),
            ),
        )

    def test_parentheses_and_negation(self):
        value = self.parse("let x = -(2 + 3)\n").statements[0].value
        self.assertEqual(
            value,
            Unary("-", Binary(Literal(2), "+", Literal(3))),
        )

    def test_subtraction_is_left_associative(self):
        value = self.parse("let x = 10 - 3 - 2\n").statements[0].value
        self.assertEqual(
            value,
            Binary(
                Binary(Literal(10), "-", Literal(3)),
                "-", Literal(2),
            ),
        )

    def test_pipeline_order(self):
        expression = self.parse(
            "10 |> double_value |> print\n"
        ).statements[0].expression
        self.assertEqual(
            expression,
            Call("print", [Call("double_value", [Literal(10)])]),
        )

    def test_multiline_call(self):
        expression = self.parse(
            'print(\n"Hello",\n2 + 3\n)\n'
        ).statements[0].expression
        self.assertEqual(
            expression,
            Call(
                "print",
                [Literal("Hello"), Binary(Literal(2), "+", Literal(3))],
            ),
        )

    def test_nested_blocks(self):
        program = self.parse(
            "repeat 2 times:\n"
            "if true:\n"
            'print("Hello")\n'
            "end if\n"
            "end loop\n"
        )
        loop = program.statements[0]
        self.assertIsInstance(loop, Repeat)
        self.assertEqual(loop.count, Literal(2))
        self.assertIsInstance(loop.body[0], Conditional)
        self.assertFalse(loop.body[0].inverted)

    def test_unless(self):
        block = self.parse(
            'unless false:\nprint("Hello")\nend unless\n'
        ).statements[0]
        self.assertTrue(block.inverted)
        self.assertEqual(block.condition, Literal(False))

    def test_missing_block_end(self):
        with self.assertRaisesRegex(ParseError, "Missing 'end if'"):
            self.parse('if true:\nprint("Hello")\n')

    def test_mismatched_block_end(self):
        with self.assertRaisesRegex(ParseError, "Expected 'end loop'"):
            self.parse("repeat 2 times:\nend if\n")

    def test_invalid_syntax(self):
        invalid_sources = [
            "let x 1\n",
            "let x =\n",
            "let x = 1 let y = 2\n",
            "if true\nend if\n",
            "repeat 2:\nend loop\n",
            'print("Hello"\n',
            "10 |>\n",
            "end if\n",
            "let x = 1 < 2 < 3\n",
        ]
        for source in invalid_sources:
            with self.subTest(source=source):
                with self.assertRaises(ParseError):
                    self.parse(source)

    def test_reserved_word_as_name(self):
        # Caught by the keyword pre-check before parsing starts.
        with self.assertRaisesRegex(ReservedWordError, "'if' is a reserved keyword"):
            self.parse("let if = 1\n")

    def test_error_position(self):
        with self.assertRaises(ParseError) as caught:
            self.parse("let x = 1\nlet y =\n")
        message = str(caught.exception)
        self.assertIn("Line 2, Col 8", message)
        self.assertIn("2 | let y =", message)
        self.assertIn("^", message)

    def test_parse_cli(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                sys.executable, "-m", "pylite", "parse",
                "examples/demo.lite",
            ],
            cwd=root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        tree = json.loads(result.stdout)
        self.assertEqual(tree["type"], "Program")
        self.assertEqual(tree["statements"][0]["type"], "Declaration")


if __name__ == "__main__":
    unittest.main()