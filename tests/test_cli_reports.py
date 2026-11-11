"""Saved-run reports through the real CLI and SQLite boundary."""
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from server import simulate
from store import Store

ROOT = Path(__file__).resolve().parents[1]


class SavedReportTests(unittest.TestCase):
    def command(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'cli.py'), *args],
                              capture_output=True, text=True, cwd=ROOT)

    def test_json_and_csv_reports_redact_without_modifying_saved_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'runs.db'
            store = Store(database)
            trace = simulate('baseline')
            trace['name'] = 'private-literal'
            run = store.save(trace)
            for format in ('json', 'csv'):
                with self.subTest(format=format):
                    result = self.command('report', run['id'], '--db', str(database),
                                          '--format', format, '--redact', 'private-literal')
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn('private-literal', result.stdout)
                    if format == 'json':
                        report = json.loads(result.stdout)
                        self.assertEqual(report['trace_name'], '[REDACTED]')
                        self.assertEqual(report['summary']['status'], 'pass')
                    else:
                        rows = list(csv.DictReader(io.StringIO(result.stdout)))
                        self.assertTrue(rows)
                        self.assertTrue(all(row['trace_name'] == '[REDACTED]' for row in rows))
            self.assertEqual(store.get(run['id'])['trace'], trace)

    def test_review_run_emits_report_with_nonzero_evaluation_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'runs.db'
            run = Store(database).save(simulate('timeout'))
            result = self.command('report', run['id'], '--db', str(database))
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads(result.stdout)['summary']['status'], 'review')

    def test_missing_database_and_run_return_json_errors_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'runs.db'
            missing_database = self.command('report', 'absent', '--db', str(database))
            self.assertFalse(database.exists())
            Store(database)
            missing_run = self.command('report', 'absent', '--db', str(database))
            for result in (missing_database, missing_run):
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')
                self.assertIn('error', json.loads(result.stderr))
