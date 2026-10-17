import json
import subprocess
import sys
import unittest
from pathlib import Path
from pylite.lexer import Lexer, LexError, StreamReader

class LexerTests(unittest.TestCase):
    def kinds(self, source):
        return [t.kind for t in Lexer(source).tokenize()]

    def test_empty(self):
        self.assertEqual(self.kinds(""), ["EOF"])

    def test_keywords(self):
        self.assertEqual(self.kinds("let const if unless repeat times end loop print true false")[:-1],
                         "LET CONST IF UNLESS REPEAT TIMES END LOOP PRINT TRUE FALSE".split())

    def test_identifier_boundaries(self):
        self.assertEqual(self.kinds("letter _count print_value True"), ["IDENTIFIER"] * 4 + ["EOF"])

    def test_greedy_operators(self):
        self.assertEqual(self.kinds("|> == != <= >= = + - * / < > ( ) : ,")[:-1],
                         "PIPE EQ NE LE GE ASSIGN PLUS MINUS STAR SLASH LT GT LPAREN RPAREN COLON COMMA".split())

    def test_negative_is_unary(self):
        self.assertEqual(self.kinds("-10 x-1"), ["MINUS", "INTEGER", "IDENTIFIER", "MINUS", "INTEGER", "EOF"])

    def test_values(self):
        tokens = Lexer('42 true false "a\\n\\t\\\"\\\\b"').tokenize()
        self.assertEqual([t.value for t in tokens[:-1]], [42, True, False, 'a\n\t"\\b'])

    def test_comments_and_indentation(self):
        self.assertEqual(self.kinds("  # comment\n\tlet x = 1 # comment\n"),
                         ["NEWLINE", "LET", "IDENTIFIER", "ASSIGN", "INTEGER", "NEWLINE", "EOF"])

    def test_positions_crlf_tabs(self):
        tokens = Lexer("let x=1\r\n\tprint(x)").tokenize()
        self.assertEqual((tokens[5].kind, tokens[5].line, tokens[5].column, tokens[5].start),
                         ("PRINT", 2, 5, 10))
        for t in tokens:
            self.assertEqual("let x=1\r\n\tprint(x)"[t.start:t.end], t.lexeme)

    def test_invalid_inputs(self):
        for source in ['@', '$', '&', '|', '!', '1.2.3', '1e+', '42name', '"unterminated', '"a\nb"', '"\\q"']:
            with self.subTest(source=source), self.assertRaises(LexError):
                Lexer(source).tokenize()

    def test_diagnostic(self):
        with self.assertRaises(LexError) as context:
            Lexer("let x=1\n\t@").tokenize()
        self.assertIn("Line 2, Col 5", str(context.exception))
        self.assertIn("2 |     @", str(context.exception))

    def test_large_string(self):
        self.assertEqual(len(Lexer('"' + 'a' * 100000 + '"').tokenize()[0].value), 100000)

    def test_nested_expression(self):
        self.assertEqual(self.kinds("((1+2)*3) |> print")[-3:], ["PIPE", "PRINT", "EOF"])

    def test_repeatable(self):
        lexer = Lexer("let x=1")
        self.assertEqual(lexer.tokenize(), lexer.tokenize())

    def test_stream_eof(self):
        stream = StreamReader("")
        self.assertTrue(stream.is_at_end())
        self.assertEqual(stream.advance(), "")

    def test_demo_and_json_cli(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, "-m", "pylite", "lex", "examples/demo.lite", "--json"],
                                cwd=root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        tokens = json.loads(result.stdout)
        self.assertEqual(tokens[-1]["kind"], "EOF")
        self.assertIn("LOOP", [t["kind"] for t in tokens])

if __name__ == "__main__":
    unittest.main()
