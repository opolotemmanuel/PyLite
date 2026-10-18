"""End-to-end language and diagnostic regression checks."""
import subprocess
import sys
import unittest
from pathlib import Path

from pylite import Lexer, LexError, Parser, ParseError, Runtime, run, transpile

ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = '''const greeting = "Hello"
let count = 0

repeat 3 times:
    count = count + 1
    print(greeting, count)
end loop

if count == 3:
    print("Done")
end if

unless count < 3:
    count |> double_value |> print
end unless
'''
EXPECTED = ['Hello 1', 'Hello 2', 'Hello 3', 'Done', '6']
HAS_DEBUG_RANGES = (
    sys.version_info >= (3, 11)
    and any(position[2] is not None
            for position in compile('1 / 0', '<probe>', 'exec').co_positions())
)


class AcceptanceTests(unittest.TestCase):
    def test_acceptance_line_endings_and_indentation(self):
        for ending in ('\n', '\r\n', '\r'):
            for indented in (True, False):
                source = ACCEPTANCE if indented else '\n'.join(line.lstrip() for line in ACCEPTANCE.split('\n'))
                source = '# comment\n' + source.replace('count = count + 1', 'count = count + 1 # increment')
                with self.subTest(ending=repr(ending), indented=indented):
                    output = []
                    run(source.replace('\n', ending), output=output.append)
                    self.assertEqual(output, EXPECTED)

    def test_transpiled_code_executes(self):
        output = []
        runtime = Runtime(output=output.append)
        environment = runtime.environment()
        exec(compile(transpile(ACCEPTANCE), '<transpiled>', 'exec'), environment, environment)
        self.assertEqual(output, EXPECTED)

    def test_scope_and_declaration_execution(self):
        output = []
        run('if true:\nlet x=4\nend if\nprint(x)', output=output.append)
        self.assertEqual(output, ['4'])
        for source in ('if false:\nlet x=1\nend if\nprint(x)',
                       'repeat 2 times:\nlet x=1\nend loop'):
            result = self.cli(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Line', result.stderr)

    def test_pipeline_order_and_escapes(self):
        output = []
        run('int("-3") |> abs |> double_value |> str |> len |> print\n'
            'print("a\\n\\t\\r\\\"\\\\", true, false)', output=output.append)
        self.assertEqual(output, ['1', 'a\n\t\r"\\ true false'])

    @staticmethod
    def cli(source):
        interpreter = [sys.executable]
        if 'no_debug_ranges' in sys._xoptions:
            interpreter += ['-X', 'no_debug_ranges']
        return subprocess.run([*interpreter, '-m', 'pylite', 'run', '-c', source],
                              cwd=ROOT, capture_output=True, text=True)

    def test_invalid_program_cli_diagnostics(self):
        cases = {
            'read': ('print(missing)', 'not declared'),
            'assign': ('missing=1', 'not declared'),
            'constant': ('const x=1\nx=2', 'constant'),
            'duplicate': ('let x=1\nlet x=2', 'already declared'),
            'division': ('print(1/0)', 'divide by zero'),
            'function': ('missing(1)', 'Unknown function'),
            'character': ('@', 'Unexpected character'),
            'string': ('print("unclosed)', 'Unclosed string'),
            'colon': ('if true\nend if', "Expected ':'"),
            'ending': ('if true:\nend loop', "Expected 'end if'"),
            'negative count': ('repeat -1 times:\nend loop', 'repeat count'),
            'boolean count': ('repeat true times:\nend loop', 'repeat count'),
            'fractional count': ('repeat 3/2 times:\nend loop', 'repeat count'),
            'string count': ('repeat "3" times:\nend loop', 'repeat count'),
            'condition': ('if 1:\nend if', 'condition must'),
        }
        for name, (source, message) in cases.items():
            with self.subTest(name=name):
                result = self.cli(source)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(message, result.stderr)
                runtime_case = name in {'division', 'negative count', 'boolean count',
                                        'fractional count', 'string count', 'condition'}
                if runtime_case and not HAS_DEBUG_RANGES:
                    self.assertIn('PyLite RuntimeError [<command>, Line 1]:', result.stderr)
                    self.assertTrue(result.stderr.rstrip().endswith('1 | ' + source.split('\n')[0]))
                    self.assertNotIn('Col ', result.stderr)
                    self.assertNotIn('^', result.stderr)
                else:
                    self.assertRegex(result.stderr, r'Line \d+, Col \d+')
                self.assertNotIn('Traceback', result.stderr)

    def test_unicode_diagnostic_line(self):
        # These are string contents, not PyLite line separators.
        for separator in ('\v', '\f', '\x85', '\u2028', '\u2029'):
            prefix = f'print("a{separator}b")\n'
            for source, error, parse in ((prefix + '@', LexError, lambda s: Lexer(s).tokenize()),
                                          (prefix + 'let x=', ParseError, lambda s: Parser(s).parse())):
                with self.subTest(separator=repr(separator), error=error):
                    with self.assertRaises(error) as caught:
                        parse(source)
                    self.assertIn('Line 2, Col', str(caught.exception))
                    self.assertIn('2 | ' + source.split('\n')[1], str(caught.exception))


if __name__ == '__main__':
    unittest.main()
