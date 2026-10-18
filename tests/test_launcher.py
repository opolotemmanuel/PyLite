"""Exercise the actual Windows launcher, including legacy native quoting."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHELLS = [path for name in ('pwsh', 'powershell') if (path := shutil.which(name))]


@unittest.skipUnless(sys.platform == 'win32' and SHELLS, 'Requires Windows and PowerShell')
class LauncherTests(unittest.TestCase):
    def launch(self, arguments, explicit=True, cwd=None, extra_path=None):
        results = []
        environment = dict(os.environ)
        search_paths = [str(Path(sys.executable).parent)]
        if extra_path is not None:
            search_paths.append(str(extra_path))
        environment['PATH'] = os.pathsep.join([*search_paths, environment.get('PATH', '')])
        for shell in SHELLS:
            command = [shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'pylite.ps1')]
            if explicit:
                command += ['-PythonPath', sys.executable]
            results.append(subprocess.run(command + arguments, cwd=cwd, env=environment,
                                          capture_output=True, text=True, timeout=30))
        return results

    def test_explicit_interpreter_and_exit_status(self):
        for arguments, status, expected in [(['run', '-c', 'print(2 + 3)'], 0, '5\n'),
                                             (['run', '-c', 'print(missing)'], 1, '')]:
            for result in self.launch(arguments):
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual(result.stdout, expected)
                self.assertNotIn('Traceback', result.stderr)

    def test_active_python_and_location_independence(self):
        with tempfile.TemporaryDirectory() as directory:
            # A second candidate must not be concatenated into the executable path.
            (Path(directory) / 'python.exe').write_bytes(b'not the selected interpreter')
            for result in self.launch(['run', 'examples/extensions.lite'], explicit=False,
                                      cwd=directory, extra_path=directory):
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('Literals: 3.14 1000.0 0.025', result.stdout)

    def test_inline_quotes_backslashes_and_multiline_source(self):
        source = 'let text = "spaces and \\\\ backslash"\nprint(text, "say \\\"hi\\\"")'
        for result in self.launch(['run', '-c', source]):
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, 'spaces and \\ backslash say "hi"\n')


if __name__ == '__main__':
    unittest.main()
