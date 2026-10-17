"""Acceptance and regressions for extensions beyond the original v1.0 grammar."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from pylite import (Lexer, LexError, Parser, ResourceError, Runtime,
                    check, run, transpile)
from pylite.__main__ import main

ROOT = Path(__file__).resolve().parents[1]


class LiteralAndCommentTests(unittest.TestCase):
    def test_number_values_and_execution(self):
        tokens = Lexer('3.14 1e3 2.5e-2 12E+2 00 0.5 -2.0').tokenize()
        self.assertEqual([t.kind for t in tokens],
                         ['FLOAT'] * 4 + ['INTEGER', 'FLOAT', 'MINUS', 'FLOAT', 'EOF'])
        self.assertEqual([t.value for t in tokens[:6]], [3.14, 1000.0, 0.025, 1200.0, 0, 0.5])
        output = []
        run('print(1.5 + 2 * 2.5, (1e2 + 1) / 2, -2.5e-2, 1e3==1000)', output=output.append)
        self.assertEqual(output, ['6.5 50.5 -0.025 true'])

    def test_malformed_numbers(self):
        for literal in ('1.', '.5', '1e', '1e+', '2.5e-', '1.2.3', '1e2e3', '1_000', '4name', '1e309'):
            with self.subTest(literal=literal), self.assertRaises(LexError) as caught:
                Lexer('print(\n\t' + literal + ')').tokenize()
            self.assertEqual((caught.exception.line, caught.exception.column), (2, 5))
            self.assertIn('number' if literal != '1e309' else 'range', str(caught.exception))

    def test_both_quote_styles_and_escapes(self):
        for quote in ('"', "'"):
            source = quote + r'''a\n\t\r\"\'\\''' + quote
            self.assertEqual(Lexer(source).tokenize()[0].value, 'a\n\t\r"\'\\')
        output = []
        run('print(\'double " inside\', "single \' inside")', output=output.append)
        self.assertEqual(output, ['double " inside single \' inside'])

    def test_unclosed_and_invalid_escapes(self):
        for quote in ('"', "'"):
            for suffix in ('unfinished', 'bad\\', 'raw\nnewline', 'unknown\\q'):
                with self.subTest(quote=quote, suffix=suffix), self.assertRaises(LexError) as caught:
                    Lexer('\n  ' + quote + suffix).tokenize()
                self.assertEqual((caught.exception.line, caught.exception.column), (2, 3))

    def test_nested_comments_positions_and_offsets(self):
        for ending in ('\n', '\r\n', '\r'):
            source = '#| outer' + ending + '#| nested |#' + ending + '|#\tprint(1)'
            tokens = Lexer(source).tokenize()
            first = next(t for t in tokens if t.kind == 'PRINT')
            self.assertEqual((first.line, first.column), (3, 5))
            self.assertEqual([t.kind for t in tokens[:2]], ['NEWLINE', 'NEWLINE'])
            for token in tokens:
                self.assertEqual(source[token.start:token.end], token.lexeme)

    def test_comment_boundaries_and_strings(self):
        output = []
        run('let x=1#| newline\n|#print(x)\n'
            'print(1 #| inline |# + 2, "#| text |#")\n'
            'print(\n1 #| multi\n#| inner |#\n|# + 2\n)', output=output.append)
        self.assertEqual(output, ['1', '3 #| text |#', '3'])
        # A line comment consumes comment-like delimiters on its line.
        self.assertEqual([t.kind for t in Lexer('# #| ignored\n1').tokenize()],
                         ['NEWLINE', 'INTEGER', 'EOF'])

    def test_unclosed_and_unmatched_comments(self):
        for source, position in (('\n #| never closed', (2, 2)),
                                 ('#| outer #| inner |#', (1, 1)), ('\t|#', (1, 5))):
            with self.subTest(source=source), self.assertRaises(LexError) as caught:
                Lexer(source).tokenize()
            self.assertEqual((caught.exception.line, caught.exception.column), position)

    def test_float_repeat_remains_invalid(self):
        from pylite import RuntimeError
        with self.assertRaisesRegex(RuntimeError, 'repeat count'):
            run('repeat 2.0 times:\nend loop')

    def test_extension_example_and_transpilation(self):
        source = (ROOT / 'examples/extensions.lite').read_text(encoding='utf-8')
        self.assertFalse(check(source).errors)
        expected = ['Literals: 3.14 1000.0 0.025', 'It\'s PyLite say "hello" backslash: \\',
                    '0.05', 'Nested blocks still work: 2']
        output = []
        run(source, output=output.append)
        self.assertEqual(output, expected)
        output.clear()
        environment = Runtime(output=output.append).environment()
        exec(compile(transpile(source), '<extensions>', 'exec'), environment, environment)
        self.assertEqual(output, expected)


class SemanticTests(unittest.TestCase):
    def test_provable_binding_errors(self):
        for source, message in (
            ('print(x)', 'not declared'), ('x=1', 'not declared'),
            ('let x=x+1', 'not declared'), ('let x=1\nlet x=2', 'already declared'),
            ('const x=1\nx=2', 'constant'), ('let len=1', 'reserved'),
            ('abs=2', 'reserved'), ('print(abs)', 'reserved'), ('unknown(1)', 'Unknown function')):
            with self.subTest(source=source):
                result = check(source)
                self.assertTrue(any(message in e.message for e in result.errors), result)
                self.assertTrue(all(e.line >= 1 and e.column >= 1 for e in result.errors))

    def test_check_never_executes(self):
        with patch('pylite.runtime.Runtime', side_effect=AssertionError('Executed!')):
            self.assertFalse(check('print(1/0)\nrepeat 1000000000000000 times:\nprint(1)\nend loop').errors)

    def test_known_condition_paths(self):
        for header in ('if true:', 'unless false:'):
            result = check(header + '\nlet x=1\nend ' + header.split()[0] + '\nprint(x)')
            self.assertFalse(result.errors + result.warnings)
        for header in ('if false:', 'unless true:'):
            result = check(header + '\nlet x=missing\nend ' + header.split()[0] + '\nprint(x)')
            self.assertEqual(len(result.errors), 1)
            self.assertIn("'x'", result.errors[0].message)

    def test_conditional_declaration_is_not_definite(self):
        result = check('let flag=true\nif flag:\nlet x=1\nend if\nprint(x)\nx=2\nlet x=3')
        self.assertFalse(result.errors)
        self.assertEqual(len(result.warnings), 3)
        self.assertIn('may not be declared', result.warnings[0].message)
        self.assertIn('may already be declared', result.warnings[-1].message)

    def test_maybe_constant_reassignment(self):
        result = check('let flag=true\nif flag:\nconst x=1\nend if\nx=2')
        self.assertFalse(result.errors)
        self.assertTrue(any('may be a constant' in w.message for w in result.warnings))

    def test_nested_conditional_is_not_definite(self):
        result = check('let flag=true\nif true:\nif flag:\nlet x=1\nend if\nend if\nprint(x)')
        self.assertFalse(result.errors)
        self.assertEqual(len(result.warnings), 1)

    def test_zero_and_single_iteration_paths(self):
        result = check('repeat 0 times:\nlet x=missing\nend loop\nprint(x)')
        self.assertEqual(len(result.errors), 1)
        self.assertIn("'x'", result.errors[0].message)
        self.assertFalse(check('repeat 1 times:\nlet x=1\nend loop\nprint(x)').errors)

    def test_repeat_declarations(self):
        result = check('repeat 2 times:\nlet x=1\nend loop')
        self.assertTrue(any('already declared' in e.message for e in result.errors))
        result = check('let n=2\nrepeat n times:\nlet x=1\nend loop\nprint(x)')
        self.assertFalse(result.errors)
        self.assertTrue(any('may already' in w.message for w in result.warnings))
        self.assertTrue(any('may not be declared' in w.message for w in result.warnings))

    def test_nested_unknown_loops_converge(self):
        result = check('let n=2\nrepeat n times:\nrepeat n times:\nlet x=1\nend loop\nend loop\nprint(x)')
        self.assertFalse(result.errors)
        self.assertTrue(result.warnings)

    def test_loop_body_checks_and_runtime_are_retained(self):
        from pylite import RuntimeError
        result = check('let n=0\nrepeat n times:\nprint(missing)\nend loop')
        self.assertTrue(result.errors)  # Invalid whenever the body is reached.
        source = 'let flag=false\nif flag:\nlet x=1\nend if\nprint(x)'
        self.assertTrue(check(source).warnings)
        with self.assertRaisesRegex(RuntimeError, 'not declared'):
            run(source)

    def test_reserved_keywords_remain_syntax_errors(self):
        from pylite import ParseError
        with self.assertRaises(ParseError):
            check('let print=1')

    def test_semantic_source_positions(self):
        error = check('# comment\r\n\tprint(missing)').errors[0]
        self.assertEqual((error.line, error.column), (2, 11))
        self.assertIn('2 |     print(missing)', str(error))


class ExtendedCliTests(unittest.TestCase):
    def test_check_cli_statuses(self):
        for source, status, message in [('print(x)', 1, 'SemanticError'),
                                        ('let flag=true\nif flag:\nlet x=1\nend if\nprint(x)', 0, 'SemanticWarning'),
                                        ('print(1/0)', 0, 'No definite semantic errors')]:
            with self.subTest(source=source), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'program.lite'
                path.write_text(source, encoding='utf-8')
                result = subprocess.run([sys.executable, '-m', 'pylite', 'check', str(path)],
                                        cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertIn(message, result.stdout + result.stderr)
                self.assertNotIn('Traceback', result.stderr)

    def test_extended_json_cli(self):
        result = subprocess.run([sys.executable, '-m', 'pylite', 'lex', 'examples/extensions.lite', '--json'],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        values = [t['value'] for t in json.loads(result.stdout) if t['kind'] == 'FLOAT']
        self.assertEqual(values, [3.14, 1000.0, 0.025])

    def test_resource_diagnostics_in_api_and_cli(self):
        source = 'print(' + '(' * 1000 + '1' + ')' * 1000 + ')'
        with self.assertRaises(ResourceError) as caught:
            run(source)
        self.assertGreater(caught.exception.column, 1)
        result = subprocess.run([sys.executable, '-m', 'pylite', 'run', '-c', source],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('ResourceError [Line 1, Col', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_flat_ast_depth_and_rendering_limits(self):
        source = 'print(' + '+'.join(['1'] * 2000) + ')'
        with self.assertRaises(ResourceError):
            Parser(source).parse()
        with self.assertRaises(ResourceError):
            transpile(source)
        # Python 3.10 has no default integer-to-text limit; do not impose one.
        if hasattr(sys, 'get_int_max_str_digits') and sys.get_int_max_str_digits():
            source = '\nprint(' + '9' * (sys.get_int_max_str_digits() + 1) + ')'
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'large.lite'
                path.write_text(source, encoding='utf-8')
                result = subprocess.run([sys.executable, '-m', 'pylite', 'lex', str(path), '--json'],
                                        cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertIn('ResourceError [Line 2, Col 7]', result.stderr)
                self.assertNotIn('Traceback', result.stderr)

    def test_memory_failure_in_runtime_helper(self):
        def exhausted(_line):
            raise MemoryError()
        with self.assertRaises(ResourceError) as caught:
            run('\nprint(1)', output=exhausted)
        self.assertEqual((caught.exception.line, caught.exception.column), (2, 1))

    def test_memory_failure_in_cli(self):
        with patch.object(sys, 'argv', ['pylite', 'run', '-c', 'print(1)']), \
                patch('pylite.__main__.run', side_effect=MemoryError()), \
                patch('sys.stderr') as stderr:
            self.assertEqual(main(), 1)
            self.assertIn('ResourceError', str(stderr.write.call_args_list))


if __name__ == '__main__':
    unittest.main()
