"""Actual staged Hugging Face Space package acceptance; no Hub writes."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.stage_release import stage

ROOT = Path(__file__).resolve().parents[1]
PIN = 'a' * 40  # Deliberately synthetic source SHA; this test publishes nothing.


class StageReleaseTests(unittest.TestCase):
    def test_staged_space_runtime_layout_and_file_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'staged'
            manifest = stage(ROOT, output, PIN)
            self.assertEqual(manifest['source_sha'], PIN)
            self.assertFalse(manifest['released'])
            self.assertFalse(manifest['runtime_verified'])
            self.assertFalse(manifest['provider_commits'])
            root = output / 'space'
            self.assertTrue((root / 'space/app.py').is_file())
            self.assertTrue((root / 'space/index.html').is_file())
            self.assertTrue((root / 'space/app.js').is_file())
            self.assertTrue((root / 'space/style.css').is_file())
            self.assertTrue((root / 'src/core.py').is_file())
            self.assertTrue((root / 'model/yachay_nb_v0.json').is_file())
            self.assertFalse((root / 'app.py').exists())
            self.assertIn('CMD ["python", "space/app.py"]',
                          (root / 'Dockerfile').read_text(encoding='utf-8'))
            for group, files in manifest['files'].items():
                for name, expected_sha in files.items():
                    from hashlib import sha256
                    self.assertEqual(
                        sha256((output / group / name).read_bytes()).hexdigest(),
                        expected_sha, f'{group}/{name}'
                    )

    def test_space_dockerfile_pins_base_digest_and_binds_container_interface(self):
        # app.py defaults HOST to loopback; inside the Space container that
        # leaves app_port 7860 unreachable from the Hub router.
        import re
        text = (ROOT / 'space/Dockerfile').read_text(encoding='utf-8')
        base = [l for l in text.splitlines() if l.startswith('FROM ')]
        self.assertEqual(len(base), 1)
        self.assertRegex(base[0], r'^FROM python:3\.12\.\d+-slim@sha256:[0-9a-f]{64}$')
        env = ' '.join(l for l in text.splitlines() if l.startswith('ENV '))
        self.assertIn('HOST=0.0.0.0', env.split())
        self.assertIn('PORT=7860', env.split())
        self.assertIsNone(re.search(r'(?i)(token|secret|password)', text))

    def test_staged_package_runs_actual_loopback_http(self):
        """Executes the *staged* Space files, not the source checkout imports."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'staged'
            stage(ROOT, output, PIN)
            script = r'''
import json, sys, threading
from urllib.request import Request, urlopen
sys.path.insert(0, sys.argv[1])
from space.app import make_server
server = make_server(host='127.0.0.1', port=0)
port = server.server_address[1]
worker = threading.Thread(target=server.serve_forever, daemon=True)
worker.start()
try:
    base = f'http://127.0.0.1:{port}'
    with urlopen(base + '/', timeout=3) as response:
        assert response.status == 200
        assert b'Khipu' in response.read()
    with urlopen(base + '/assets/app.js', timeout=3) as response:
        assert response.status == 200
        assert b'function render' in response.read()
    with urlopen(base + '/api/healthz', timeout=3) as response:
        health = json.load(response)
        assert health['archival_ids'] == 702
        assert health['production_qualified'] is False
    payload = json.dumps({'cords':[3,4], 'declared_total':7,
                          'question':'how do I verify a sum', 'kh_id':'KH0001'}).encode()
    request = Request(base + '/api/analyze', data=payload,
                      headers={'Content-Type':'application/json'}, method='POST')
    with urlopen(request, timeout=3) as response:
        parsed = json.load(response)
        assert parsed['arithmetic']['state'] == 'ARITHMETIC_EQUAL_ONLY'
        assert parsed['reference']['kh_id'] == 'KH0001'
        assert parsed['production_qualified'] is False
finally:
    server.shutdown()
    server.server_close()
'''
            result = subprocess.run(
                [sys.executable, '-B', '-c', script, str(output / 'space')],
                cwd=directory, capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stderr[-1000:])

    def test_staging_requires_valid_pin_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'new'
            with self.assertRaisesRegex(ValueError, 'REVIEWED_SOURCE_SHA_REQUIRED'):
                stage(ROOT, output, 'main')
            self.assertFalse(output.exists())
            stage(ROOT, output, PIN)
            with self.assertRaisesRegex(ValueError, 'OUTPUT_EXISTS'):
                stage(ROOT, output, PIN)

    def test_model_digest_tamper_blocks_before_writing(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / 'clone'
            for name in ('data', 'model', 'docs', 'space', 'src'):
                shutil.copytree(ROOT / name, project / name,
                                ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            model = project / 'model/yachay_nb_v0.json'
            model.write_bytes(model.read_bytes() + b' ')
            output = Path(directory) / 'stage'
            with self.assertRaisesRegex(ValueError, 'MODEL_DIGEST_MISMATCH'):
                stage(project, output, PIN)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()