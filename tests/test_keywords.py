import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pylite.keywords import (
    KEYWORDS, KeywordClassifier, ReservedWordError, ScopedSymbolTable, precheck,
)
from pylite.lexer import Lexer, LexError
from pylite.parser import Parser


def check(source):
    return precheck(Lexer(source).tokenize(), source)


class KeywordClassifierTests(unittest.TestCase):
    def setUp(self):
        self.classifier = KeywordClassifier()

    def test_lookup_table_has_every_keyword(self):
        self.assertEqual(set(KEYWORDS), set(
            "let const if unless repeat times end loop print true false".split()))

    def test_classify(self):
        self.assertEqual(self.classifier.classify("repeat"), "REPEAT")
        self.assertEqual(self.classifier.classify("count"), "IDENTIFIER")

    def test_case_sensitive(self):
        for word in ["Let", "IF", "True", "PRINT"]:
            with self.subTest(word=word):
                self.assertFalse(self.classifier.is_reserved(word))
                self.assertEqual(self.classifier.classify(word), "IDENTIFIER")

    def test_matches_lexer(self):
        for word, kind in KEYWORDS.items():
            with self.subTest(word=word):
                self.assertEqual(Lexer(word).tokenize()[0].kind, kind)
                self.assertEqual(self.classifier.classify(word), kind)

    def test_valid_identifiers(self):
        for word in ["x", "_count", "max_attempts", "letter", "end2", "printer"]:
            with self.subTest(word=word):
                self.assertTrue(self.classifier.is_valid_identifier(word))
        for word in ["", "if", "true", "2x", "my-name", "café", "a b"]:
            with self.subTest(word=word):
                self.assertFalse(self.classifier.is_valid_identifier(word))


class ScopedSymbolTableTests(unittest.TestCase):
    def test_inner_scope_sees_outer(self):
        table = ScopedSymbolTable()
        table.declare("x", True, 1, 5)
        table.enter_scope()
        table.declare("y", False, 2, 11)
        self.assertEqual(table.lookup("x").depth, 0)
        self.assertEqual(table.lookup("y").depth, 1)
        table.exit_scope()
        self.assertTrue(table.is_declared("x"))
        self.assertFalse(table.is_declared("y"))

    def test_exit_never_pops_top_level(self):
        table = ScopedSymbolTable()
        table.exit_scope()
        self.assertEqual(table.depth, 0)


class PrecheckTests(unittest.TestCase):
    def test_reserved_after_let_or_const(self):
        for word in KEYWORDS:
            for binder in ("let", "const"):
                source = f"{binder} {word} = 1"
                with self.subTest(source=source), self.assertRaises(ReservedWordError):
                    check(source)

    def test_reserved_on_left_of_assignment(self):
        for source in ["end = 3", "print = 1", "repeat = 2", "true = 1",
                       "let x = 1\ntimes = 2"]:
            with self.subTest(source=source), self.assertRaises(ReservedWordError):
                check(source)

    def test_diagnostic_points_at_keyword(self):
        with self.assertRaises(ReservedWordError) as context:
            check("let x = 1\nif x > 0:\n\tconst unless = 2\nend if\n")
        message = str(context.exception)
        self.assertIn("Line 3, Col 11", message)
        self.assertIn("'unless' is a reserved keyword", message)
        self.assertIn("3 |     const unless = 2", message)

    def test_boolean_message(self):
        with self.assertRaises(ReservedWordError) as context:
            check("let false = 0")
        self.assertIn("'false' is a boolean value", str(context.exception))

    def test_is_a_lex_error(self):
        self.assertTrue(issubclass(ReservedWordError, LexError))

    def test_valid_program_records_scoped_declarations(self):
        table = check(
            "let count = 1\n"
            "repeat 3 times:\n"
            "    const step = count\n"
            "    if step > 1:\n"
            "        let inner = step\n"
            "    end if\n"
            "end loop\n"
            "let after = 2\n"
        )
        self.assertEqual([(s.name, s.mutable, s.line, s.depth) for s in table.declarations],
                         [("count", True, 1, 0), ("step", False, 3, 1),
                          ("inner", True, 5, 2), ("after", True, 8, 0)])
        self.assertEqual(table.depth, 0)

    def test_keywords_elsewhere_are_fine(self):
        for source in ["print(1)", "let x = true", "if x == false:\n    print(x)\nend if",
                       "5 |> print", "let letter = 1\nletter = 2", "let True = 1"]:
            with self.subTest(source=source):
                check(source)

    def test_parser_uses_precheck(self):
        with self.assertRaises(ReservedWordError):
            Parser("let print = 1\n").parse()

    def test_cli_reports_reserved_word(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.lite"
            path.write_text("let repeat = 5\n", encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "pylite", "check", str(path)],
                                    cwd=root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("PyLite LexError [Line 1, Col 5]", result.stderr)
        self.assertIn("'repeat' is a reserved keyword", result.stderr)


if __name__ == "__main__":
    unittest.main()
