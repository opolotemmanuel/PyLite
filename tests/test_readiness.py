"""Readiness regressions and exact-output manual acceptance checks."""
from pathlib import Path
import subprocess
import sys
import unittest

from pylite import Parser, Runtime, check, run, transpile
from pylite.semantic import Analyzer
from pylite.binding_checks import SemanticAnalyzer
from pylite.parser import Parser as SyntaxParser
from pylite.symbols import SemanticError

ROOT = Path(__file__).resolve().parents[1]


class ReadinessTests(unittest.TestCase):
    def test_nested_stable_repeats_do_not_expand_exponentially(self):
        class CountingAnalyzer(Analyzer):
            visits = 0

            def block(self, body, state):
                self.visits += 1
                return super().block(body, state)

        depth = 12
        source = ('repeat 2 times:\n' * depth + 'print(1)\n'
                  + 'end loop\n' * depth)
        analyzer = CountingAnalyzer(source)
        result = analyzer.analyze(Parser(source).parse())
        self.assertFalse(result.errors + result.warnings)
        self.assertLessEqual(analyzer.visits, depth + 1)

    def test_repeat_fix_retains_second_iteration_binding_checks(self):
        self.assertTrue(check('repeat 2 times:\nlet x=1\nend loop').errors)
        result = check('let flag=true\nrepeat 2 times:\nif flag:\nlet x=1\nend if\nend loop')
        self.assertFalse(result.errors)
        self.assertTrue(any('already' in item.message for item in result.warnings))

    def test_manual_program_api_and_generated_code(self):
        source = (ROOT / 'examples/manual_test.lite').read_text(encoding='utf-8')
        expected = (ROOT / 'examples/manual_test.expected.txt').read_text(encoding='utf-8')
        analysis = check(source)
        self.assertFalse(analysis.errors + analysis.warnings)
        output = []
        run(source, output=output.append)
        self.assertEqual('\n'.join(output) + '\n', expected)
        output.clear()
        environment = Runtime(output=output.append).environment()
        exec(compile(transpile(source), '<manual-transpiled>', 'exec'), environment, environment)
        self.assertEqual('\n'.join(output) + '\n', expected)

    def test_manual_program_cli(self):
        result = subprocess.run([sys.executable, '-m', 'pylite', 'run', 'examples/manual_test.lite'],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        expected = (ROOT / 'examples/manual_test.expected.txt').read_text(encoding='utf-8')
        self.assertEqual(result.stdout, expected)

    def test_compatibility_function_hint_lists_actual_builtins(self):
        with self.assertRaises(SemanticError) as caught:
            SemanticAnalyzer().analyze(SyntaxParser('missing()').parse())
        for name in ('abs', 'len', 'str', 'int', 'print', 'double_value'):
            self.assertIn(name, str(caught.exception))


if __name__ == '__main__':
    unittest.main()
