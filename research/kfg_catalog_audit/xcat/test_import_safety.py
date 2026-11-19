"""Offline regression tests; set KHIPU_XCAT_INPUTS for the pinned-data replay."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


class ImportSafetyTests(unittest.TestCase):
    def run_code(self, code, cwd, optimized=False):
        return subprocess.run([sys.executable, *(['-O'] if optimized else []), '-B', '-c',
            f'import sys; sys.path.insert(0, {str(HERE)!r});\n' + code],
            cwd=cwd, capture_output=True, text=True, check=False)

    def test_clean_import_without_inputs_or_io(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_code('''from unittest.mock import patch
import builtins
from pathlib import Path
with patch.object(builtins, 'open', side_effect=RuntimeError('unexpected data read')), patch.object(Path, 'read_bytes', side_effect=RuntimeError('unexpected data read')):
    import compare
    import verify_okr
assert 'okr_khipu' not in sys.modules
assert '_pinned_okr_khipu' not in sys.modules
''', directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, '')
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_missing_and_tampered_inputs_including_optimized(self):
        for optimized in (False, True):
            with self.subTest(optimized=optimized), tempfile.TemporaryDirectory() as directory:
                for module, call, filename in [('compare', 'compare', 'corpus.json.gz'),
                                                ('verify_okr', 'verify', 'okr_khipu.py')]:
                    code = f'''import {module}
try:
    {module}.{call}()
except FileNotFoundError:
    pass
else:
    raise RuntimeError('missing input accepted')
'''
                    result = self.run_code(code, directory, optimized)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    Path(directory, filename).write_bytes(b'not the pinned input')
                    code = code.replace('FileNotFoundError', 'ValueError').replace('missing input', 'tampered input')
                    result = self.run_code(code, directory, optimized)
                    self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(os.environ.get('KHIPU_XCAT_INPUTS'), 'set KHIPU_XCAT_INPUTS for pinned replay')
    def test_pinned_replay_byte_identical_and_native_verification(self):
        inputs = os.environ['KHIPU_XCAT_INPUTS']
        for optimized in (False, True):
            flags = ['-O'] if optimized else []
            result = subprocess.run([sys.executable, *flags, '-B', str(HERE / 'compare.py'), '--input-dir', inputs], capture_output=True, check=True)
            self.assertEqual(result.stdout, (HERE / 'result.json').read_bytes())
            result = subprocess.run([sys.executable, *flags, '-B', str(HERE / 'verify_okr.py'), '--input-dir', inputs], capture_output=True, check=True)
            self.assertEqual(result.stdout, b'Across 619 artifacts, replayed 47 single-group and 7 multigroup exact R2 relations.\n')


if __name__ == '__main__':
    unittest.main()
