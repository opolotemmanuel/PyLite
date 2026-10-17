"""Run explicitly after pip install ., outside the checkout, in local/CI checks."""
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile

ROOT = Path(__file__).resolve().parents[1]
script = Path(sysconfig.get_path('scripts')) / ('pylite.exe' if os.name == 'nt' else 'pylite')
environment = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME')}
with tempfile.TemporaryDirectory() as directory:
    imported = subprocess.run([sys.executable, '-I', '-c', 'import pylite; print(pylite.__file__)'],
                              cwd=directory, env=environment, capture_output=True, text=True, check=True)
    assert Path(imported.stdout.strip()).is_relative_to(Path(sys.prefix)), imported.stdout
    for prefix in ([sys.executable, '-I', '-m', 'pylite'], [str(script)]):
        for args, expected in [(['run', '-c', 'print(2 + 3)'], '5\n'),
                               (['run', str(ROOT / 'examples/demo.lite')], 'Passed\n20\n' + 'Executing step\n' * 5),
                               (['run', str(ROOT / 'examples/full_program.lite')],
                                'PyLite is running\nStep 1\nStep 2\nHalfway to four\nStep 3\nFinished\n6\nResult: 20\ntrue\n'),
                               (['run', str(ROOT / 'examples/extensions.lite')],
                                'Literals: 3.14 1000.0 0.025\nIt\'s PyLite say "hello" backslash: \\\n0.05\nNested blocks still work: 2\n')]:
            result = subprocess.run(prefix + args, cwd=directory, env=environment,
                                    capture_output=True, text=True, check=True)
            assert result.stdout == expected, (args, result.stdout, expected)
        for filename in ('demo.lite', 'full_program.lite', 'extensions.lite'):
            for command in ('lex', 'check', 'transpile'):
                args = [command, str(ROOT / 'examples' / filename)]
                if command == 'lex':
                    args += ['--json']
                result = subprocess.run(prefix + args, cwd=directory, env=environment,
                                        capture_output=True, text=True, check=True)
                if command == 'lex':
                    assert json.loads(result.stdout)[-1]['kind'] == 'EOF'
        bad = Path(directory) / 'invalid.lite'
        bad.write_text('print(missing)', encoding='utf-8')
        result = subprocess.run(prefix + ['check', str(bad)], cwd=directory, env=environment,
                                capture_output=True, text=True)
        assert result.returncode == 1 and 'SemanticError' in result.stderr
        assert 'Traceback' not in result.stderr
print('Installed module and entry point verified outside the checkout.')
