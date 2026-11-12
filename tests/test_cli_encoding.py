"""Report exports retain UTF-8 when redirected from a narrow-locale shell."""
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from server import simulate

ROOT = Path(__file__).resolve().parents[1]


class CLIEncodingTests(unittest.TestCase):
    def test_unicode_json_and_csv_reports_override_narrow_stdout_encoding(self):
        trace = simulate('baseline')
        trace['name'] = '\u8bb0\u5f55'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'trace.json'
            path.write_text(json.dumps(trace), encoding='utf-8')
            for format in ('json', 'csv'):
                with self.subTest(format=format):
                    result = subprocess.run(
                        [sys.executable, str(ROOT / 'cli.py'), 'evaluate', str(path), '--format', format],
                        capture_output=True, cwd=ROOT, env={**os.environ, 'PYTHONIOENCODING': 'ascii'})
                    self.assertEqual(result.returncode, 0, result.stderr.decode('ascii'))
                    output = result.stdout.decode('utf-8')
                    if format == 'json':
                        self.assertEqual(json.loads(output)['trace_name'], trace['name'])
                    else:
                        rows = list(csv.DictReader(io.StringIO(output)))
                        self.assertTrue(rows)
                        self.assertTrue(all(row['trace_name'] == trace['name'] for row in rows))
