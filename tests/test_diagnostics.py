"""Source locations must survive parsing, compilation and helper calls."""
import ast
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pylite.nodes import Binary, Literal
from pylite.parser import Parser
from pylite.runtime import PyLiteRuntimeError, run, runtime_span
from pylite.semantic import SemanticAnalyzer
from pylite.symbols import SemanticError
from pylite.transpiler import Transpiler


HAS_DEBUG_RANGES = (
    sys.version_info >= (3, 11)
    and any(position[2] is not None
            for position in compile('1 / 0', '<probe>', 'exec').co_positions())
)


class DiagnosticsTests(unittest.TestCase):
    def assert_location(self, error, kind, line, column, snippet, marked, filename='demo.lite'):
        text = str(error)
        if kind == 'RuntimeError' and not HAS_DEBUG_RANGES:
            self.assertIn(f'PyLite {kind} [{filename}, Line {line}]:', text)
            self.assertTrue(text.endswith(f'{line} | {snippet}'))
            self.assertNotIn('Col ', text)
            self.assertNotIn('^', text)
            self.assertNotIn('runtime.py', text)
            return
        self.assertIn(f'PyLite {kind} [{filename}, Line {line}, Col {column}]:', text)
        self.assertEqual(text.splitlines()[-2:], [
            f'{line} | {snippet}',
            ' ' * (len(f'{line} | ') + column - 1) + '^' * len(marked),
        ])
        self.assertNotIn('runtime.py', text)

    def runtime_error(self, source):
        with self.assertRaises(PyLiteRuntimeError) as caught:
            run(source, 'demo.lite')
        return caught.exception

    def test_nested_division_preserves_stdout(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            error = self.runtime_error('print("ready")\nif true:\n\tprint(10 / 0)\nend if\n')
        self.assertEqual(output.getvalue(), 'ready\n')
        self.assert_location(error, 'RuntimeError', 3, 11, '    print(10 / 0)', '10 / 0')

    def test_crlf_tab_and_unicode_before_operation(self):
        error = self.runtime_error('# heading\r\n\tprint("é猫", 10 / 0)\r\n')
        self.assert_location(error, 'RuntimeError', 2, 17, '    print("é猫", 10 / 0)', '10 / 0')

    def test_incompatible_binary_and_unary(self):
        for expression in ['"x" - 1', '-"x"', '"x" < 1']:
            with self.subTest(expression=expression):
                error = self.runtime_error('\nprint(' + expression + ')\n')
                self.assert_location(error, 'RuntimeError', 2, 7, 'print(' + expression + ')', expression)

    def test_repeat_helper_nested(self):
        error = self.runtime_error('if true:\n\trepeat -1 times:\n\tend loop\nend if\n')
        self.assert_location(error, 'RuntimeError', 2, 5, '    repeat -1 times:', 'repeat -1 times:')
        self.assertIn('nonnegative integer', str(error))

    def test_declaration_helper(self):
        error = self.runtime_error('repeat 2 times:\n\tlet value = 1\nend loop\n')
        self.assert_location(error, 'RuntimeError', 2, 5, '    let value = 1', 'let value = 1')
        self.assertIn('declared more than once', str(error))

    def test_double_value_helper_and_pipeline(self):
        for expression in ['double_value("é")', '"é" |> double_value']:
            with self.subTest(expression=expression):
                error = self.runtime_error('\n\t' + expression + '\n')
                self.assert_location(error, 'RuntimeError', 2, 5, '    ' + expression, expression)
                self.assertIn('expects a number', str(error))

    def test_semantic_identifier_nested(self):
        source = 'if true:\r\n\tprint("é猫", missing)\r\nend if\r\n'
        with self.assertRaises(SemanticError) as caught:
            SemanticAnalyzer().analyze(Parser(source, 'demo.lite').parse())
        self.assert_location(caught.exception, 'SemanticError', 2, 17,
                             '    print("é猫", missing)', 'missing')

    def test_semantic_binding_and_function_errors(self):
        cases = [
            ('let x = 1\nlet x = 2\n', 5, 'let x = 2', 'x'),
            ('const x = 1\nx = 2\n', 1, 'x = 2', 'x'),
            ('\nunknown(1)\n', 1, 'unknown(1)', 'unknown'),
            ('\ndouble_value()\n', 1, 'double_value()', 'double_value'),
            ('\nx = 2\n', 1, 'x = 2', 'x'),
        ]
        for source, column, snippet, marked in cases:
            with self.subTest(source=source):
                with self.assertRaises(SemanticError) as caught:
                    run(source, 'demo.lite')
                self.assert_location(caught.exception, 'SemanticError', 2, column, snippet, marked)

    def test_spans_and_ast_byte_columns(self):
        source = '# heading\r\n\tprint("é猫", 10 / 0)\r\n'
        program = Parser(source).parse()
        binary = program.statements[0].expression.arguments[1]
        self.assertEqual(source[binary.span.start:binary.span.end], '10 / 0')
        self.assertEqual((binary.span.line, binary.span.column, binary.span.end_line,
                          binary.span.end_column), (2, 17, 2, 23))
        tree = Transpiler().transpile(program)
        operation = next(node for node in ast.walk(tree) if isinstance(node, ast.BinOp))
        self.assertEqual((operation.lineno, operation.col_offset, operation.end_lineno,
                          operation.end_col_offset), (2, 16, 2, 22))
        self.assertEqual(binary, Binary(Literal(10), '/', Literal(0)))
        compile(tree, 'demo.lite', 'exec')

    def test_multiline_expression(self):
        error = self.runtime_error('print(\n  10 /\n  0\n)\n')
        self.assert_location(error, 'RuntimeError', 2, 3, '  10 /', '10 /')

    def test_helper_defects_are_not_translated(self):
        with patch('pylite.runtime.double_value', side_effect=TypeError('helper defect')):
            with self.assertRaisesRegex(TypeError, 'helper defect'):
                run('double_value(1)')
        with patch('pylite.runtime.Transpiler.transpile', side_effect=ValueError('compiler defect')):
            with self.assertRaisesRegex(ValueError, 'compiler defect'):
                run('print(1)')

    def test_cr_only_lines(self):
        error = self.runtime_error('# heading\r\tprint(10 / 0)\r')
        self.assert_location(error, 'RuntimeError', 2, 11, '    print(10 / 0)', '10 / 0')

    def test_unicode_line_separator_is_string_content(self):
        source = 'print("a\u2028b", 1 / 0)\n'
        error = self.runtime_error(source)
        if HAS_DEBUG_RANGES:
            self.assertIn('[demo.lite, Line 1, Col 14]', str(error))
            self.assertTrue(str(error).endswith(' ' * 17 + '^' * 5))
        else:
            self.assertIn('[demo.lite, Line 1]:', str(error))
            self.assertTrue(str(error).endswith('1 | ' + source.rstrip('\n')))

    def test_parenthesized_spans(self):
        error = self.runtime_error('\nprint((1 + 2) / 0)\n')
        self.assert_location(error, 'RuntimeError', 2, 7,
                             'print((1 + 2) / 0)', '(1 + 2) / 0')
        with self.assertRaises(SemanticError) as caught:
            run('\nprint((missing))\n', 'demo.lite')
        self.assert_location(caught.exception, 'SemanticError', 2, 8,
                             'print((missing))', 'missing')

    def test_cli_success_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'valid.lite'
            file.write_text('let x = 2\nprint(x |> double_value)\n')
            for command in ['lex', 'parse', 'check', 'run']:
                with self.subTest(command=command):
                    result = subprocess.run([sys.executable, '-m', 'pylite', command, str(file)],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, '')
                    if command == 'run':
                        self.assertEqual(result.stdout, '4\n')
                    elif command == 'check':
                        self.assertEqual(result.stdout, 'Syntax is valid. No definite semantic errors.\n')
                    else:
                        self.assertTrue(result.stdout)

    def test_cli_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'demo.lite'
            for command, source, kind, output in [
                ('check', '\nprint(missing)\n', 'SemanticError', ''),
                ('run', '\nprint(missing)\n', 'SemanticError', ''),
                ('run', 'print("ready")\nprint(10 / 0)\n', 'RuntimeError', 'ready\n'),
                ('run', '\ndouble_value("x")\n', 'RuntimeError', ''),
            ]:
                with self.subTest(command=command, source=source):
                    file.write_text(source)
                    result = subprocess.run([sys.executable, '-m', 'pylite', command, str(file)],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, output)
                    self.assertIn(f'PyLite {kind} [{file}, Line 2', result.stderr)
                    self.assertNotIn('Traceback', result.stderr)


class RuntimeFallbackTests(unittest.TestCase):
    def test_python310_guard_and_helper_locations(self):
        cases = [
            ('if true:\r\n\tprint("é猫", 10 / 0)\r\nend if\r\n', 2,
             '    print("é猫", 10 / 0)', 'Cannot divide by zero'),
            ('\nprint("x" - 1)\n', 2, 'print("x" - 1)', 'incompatible values'),
            ('if true:\n\trepeat -1 times:\n\tend loop\nend if\n', 2,
             '    repeat -1 times:', 'nonnegative integer'),
            ('repeat 2 times:\n\tlet x = 1\nend loop\n', 2,
             '    let x = 1', 'declared more than once'),
            ('\n\tdouble_value("é")\n', 2, '    double_value("é")', 'expects a number'),
            ('print(\n  10 /\n  0\n)\n', 2, '  10 /', 'Cannot divide by zero'),
        ]
        with patch('pylite.runtime.sys', SimpleNamespace(version_info=(3, 10, 0))), \
                patch('pylite.runtime.dis.get_instructions',
                      side_effect=AssertionError('3.11 API called')) as instructions:
            for source, line, snippet, message in cases:
                with self.subTest(source=source):
                    with self.assertRaises(PyLiteRuntimeError) as caught:
                        run(source, 'fallback.lite')
                    text = str(caught.exception)
                    self.assertTrue(text.startswith(
                        f'PyLite RuntimeError [fallback.lite, Line {line}]:\n'))
                    self.assertTrue(text.endswith(f'{line} | {snippet}'))
                    self.assertIn(message, text)
                    self.assertNotIn('Col ', text)
                    self.assertNotIn('^', text)
                    self.assertNotIn('runtime.py', text)
            instructions.assert_not_called()

    def test_unavailable_instruction_positions(self):
        code = compile('1 / 0', '<probe>', 'exec')
        with patch('pylite.runtime.dis.get_instructions', return_value=[
                SimpleNamespace(offset=0),
        ]):
            self.assertIsNone(runtime_span(code, 0, '1 / 0'))
        with patch('pylite.runtime.dis.get_instructions', return_value=[
                SimpleNamespace(offset=0, positions=SimpleNamespace(
                    lineno=1, end_lineno=1, col_offset=None, end_col_offset=None)),
        ]):
            self.assertIsNone(runtime_span(code, 0, '1 / 0'))

    @unittest.skipUnless(sys.version_info >= (3, 11), 'requires -X no_debug_ranges')
    def test_cli_without_debug_ranges(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'fallback.lite'
            for operation in ['10 / 0', 'double_value("é")']:
                with self.subTest(operation=operation):
                    file.write_bytes(('print("ready")\r\nif true:\r\n\tprint('
                                      + operation + ')\r\nend if\r\n').encode('utf-8'))
                    result = subprocess.run([
                        sys.executable, '-X', 'no_debug_ranges', '-m', 'pylite', 'run', str(file),
                    ], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, 'ready\n')
                    self.assertIn(f'PyLite RuntimeError [{file}, Line 3]:', result.stderr)
                    self.assertTrue(result.stderr.endswith(f'3 |     print({operation})\n'))
                    for unwanted in ['Col ', '^', 'Traceback', 'runtime.py']:
                        self.assertNotIn(unwanted, result.stderr)
