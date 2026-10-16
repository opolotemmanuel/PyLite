"""Tests for PyLite variable binding checks."""

import unittest

from pylite.parser import Parser
from pylite.semantic import SemanticAnalyzer
from pylite.symbols import SemanticError


class SemanticTests(unittest.TestCase):
    def check(self, source):
        program = Parser(source).parse()
        return SemanticAnalyzer().analyze(program)

    def test_mutable_assignment(self):
        self.check("let count = 1\ncount = count + 1\n")

    def test_constant_read(self):
        self.check("const limit = 3\nprint(limit)\n")

    def test_undeclared_read(self):
        with self.assertRaisesRegex(SemanticError, "has not been declared"):
            self.check("print(missing)\n")

    def test_undeclared_assignment(self):
        with self.assertRaisesRegex(SemanticError, "has not been declared"):
            self.check("missing = 2\n")

    def test_constant_assignment(self):
        with self.assertRaisesRegex(SemanticError, "Cannot reassign"):
            self.check("const limit = 3\nlimit = 4\n")

    def test_duplicate_declaration(self):
        with self.assertRaisesRegex(SemanticError, "already declared"):
            self.check("let count = 1\nlet count = 2\n")

    def test_self_reference(self):
        with self.assertRaisesRegex(SemanticError, "has not been declared"):
            self.check("let count = count + 1\n")

    def test_pipeline(self):
        self.check("let value = 10\nvalue |> double_value |> print\n")

    def test_unknown_function(self):
        with self.assertRaisesRegex(SemanticError, "Unknown function"):
            self.check("mystery(10)\n")

    def test_function_argument_count(self):
        with self.assertRaisesRegex(SemanticError, "expects 1 argument"):
            self.check("double_value(1, 2)\n")

    def test_builtin_name_collision(self):
        with self.assertRaisesRegex(SemanticError, "built-in function"):
            self.check("let double_value = 5\n")

    def test_nested_blocks(self):
        self.check(
            "let count = 0\n"
            "repeat 2 times:\n"
            "if true:\n"
            "count = count + 1\n"
            "end if\n"
            "end loop\n"
            "print(count)\n"
        )

    def test_conditional_declaration_may_be_uninitialized(self):
        with self.assertRaisesRegex(SemanticError, "may not have a value"):
            self.check(
                "if false:\n"
                "let result = 10\n"
                "end if\n"
                "print(result)\n"
            )

    def test_loop_declaration_may_be_uninitialized(self):
        with self.assertRaisesRegex(SemanticError, "may not have a value"):
            self.check(
                "repeat 0 times:\n"
                "let result = 10\n"
                "end loop\n"
                "print(result)\n"
            )

    def test_declaration_used_inside_its_block(self):
        self.check(
            "if true:\n"
            "let result = 10\n"
            "print(result)\n"
            "end if\n"
        )

    def test_assignment_after_optional_declaration(self):
        self.check(
            "if false:\n"
            "let result = 10\n"
            "end if\n"
            "result = 20\n"
            "print(result)\n"
        )

    def test_analyzer_resets_between_programs(self):
        analyzer = SemanticAnalyzer()
        analyzer.analyze(Parser("let count = 1\n").parse())

        with self.assertRaisesRegex(SemanticError, "has not been declared"):
            analyzer.analyze(Parser("print(count)\n").parse())


if __name__ == "__main__":
    unittest.main()