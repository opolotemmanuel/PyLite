import ast
import subprocess
import sys
import unittest
from pathlib import Path
from pylite import run, Parser, ParseError, RuntimeError, transpile

class RuntimeTests(unittest.TestCase):
    def execute(self, source):
        output = []
        runtime = run(source, output=output.append)
        return output, runtime.variables

    def test_bindings_arithmetic(self):
        output, variables = self.execute('let x = 1\nx = x + 1\nprint(x, 2+3*4, (2+3)*4, -10, 5/2)')
        self.assertEqual(output, ['2 14 20 -10 2.5'])
        self.assertEqual(variables, {'x': 2})

    def test_constants(self):
        with self.assertRaisesRegex(RuntimeError, "Cannot change constant"):
            run('const x = 1\nx = 2')

    def test_undeclared_and_duplicate(self):
        for source in ('x = 1', 'print(x)', 'let x=1\nlet x=2', 'let len=2'):
            with self.subTest(source=source), self.assertRaises(RuntimeError):
                run(source)

    def test_conditionals(self):
        source = 'if true:\nprint("yes")\nend if\nunless false:\nprint("also")\nend unless\nif false:\nprint("no")\nend if'
        self.assertEqual(self.execute(source)[0], ['yes', 'also'])

    def test_nested_loops(self):
        source = 'let n=0\nrepeat 2 times:\nrepeat 3 times:\nn=n+1\nend loop\nend loop\nprint(n)'
        self.assertEqual(self.execute(source)[0], ['6'])

    def test_zero_repeat(self):
        self.assertEqual(self.execute('repeat 0 times:\nprint("no")\nend loop')[0], [])

    def test_bad_counts(self):
        for count in ('-1', 'true', '"three"', '3/2'):
            with self.subTest(count=count), self.assertRaisesRegex(RuntimeError, 'repeat count'):
                run(f'repeat {count} times:\nend loop')

    def test_condition_requires_boolean(self):
        with self.assertRaisesRegex(RuntimeError, 'condition must'):
            run('if 1:\nend if')

    def test_pipeline(self):
        self.assertEqual(self.execute('2 + 3 |> double_value |> print')[0], ['10'])

    def test_builtins_strings(self):
        self.assertEqual(self.execute('print(len("abc"), abs(-2), int("4"), "a"+"b", str(false))')[0], ['3 2 4 ab false'])

    def test_multiline_call(self):
        self.assertEqual(self.execute('print(\n1 +\n2,\n"ok"\n)')[0], ['3 ok'])

    def test_runtime_errors_positions(self):
        with self.assertRaisesRegex(RuntimeError, 'Line 2, Col 8.*divide by zero'):
            run('let x=2\nprint(x/0)')

    def test_invalid_operations(self):
        for source in ('print(true+1)', 'print("a"-1)', 'print(unknown(1))', 'print(len(2))', 'print(true<1)'):
            with self.subTest(source=source), self.assertRaises(RuntimeError):
                run(source)

    def test_comparisons(self):
        self.assertEqual(self.execute('print(1==1, 1!=2, 1<2, 2>1, 2<=2, 2>=2, true==1)')[0],
                         ['true true true true true true false'])

    def test_parse_failures(self):
        samples = ['end if', 'if true:\nend loop', 'repeat 2:\nend loop', 'if true\nend if',
                   'let if=1', 'let x=', 'print(1', '1 2', '1 |> 2', '1 < 2 < 3', 'if true:\nprint(1)']
        for source in samples:
            with self.subTest(source=source), self.assertRaises(ParseError):
                Parser(source).parse()

    def test_ast_and_empty(self):
        self.assertIsInstance(Parser('print(1)').parse(), ast.Module)
        self.assertIn('_lite_call', transpile('print(1)'))
        self.assertEqual(self.execute('')[0], [])

    def test_isolated_runs(self):
        run('let x=1')
        with self.assertRaises(RuntimeError):
            run('print(x)')

    def test_examples(self):
        root = Path(__file__).resolve().parents[1]
        output, _ = self.execute((root / 'examples/full_program.lite').read_text())
        self.assertEqual(output, ['PyLite is running', 'Step 1', 'Step 2', 'Halfway to four', 'Step 3',
                                  'Finished', '6', 'Result: 20', 'true'])

    def test_cli(self):
        root = Path(__file__).resolve().parents[1]
        for command in ('run', 'check', 'transpile'):
            result = subprocess.run([sys.executable, '-m', 'pylite', command, 'examples/full_program.lite'],
                                    cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout)

    def test_inline_cli(self):
        root = Path(__file__).resolve().parents[1]
        cases = [(['-c', 'print(2 + 3)'], 0, '5\n'),
                 (['-c', 'let x=2\nx |> double_value |> print'], 0, '4\n'),
                 (['-c', 'print(1/0)'], 1, ''),
                 ([], 2, ''),
                 (['examples/demo.lite', '-c', 'print(1)'], 2, '')]
        for arguments, status, output in cases:
            with self.subTest(arguments=arguments):
                result = subprocess.run([sys.executable, '-m', 'pylite', 'run', *arguments],
                                        cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual(result.stdout, output)

if __name__ == '__main__':
    unittest.main()
