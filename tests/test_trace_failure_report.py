import subprocess
import os
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'bin/trace_failure_report.py'
WRAPPER = SCRIPT.parent / 'nextflow_with_failure_report.sh'


class ReportTests(unittest.TestCase):
    def report(self, text):
        with tempfile.TemporaryDirectory() as d:
            trace = Path(d) / 'trace.tsv'
            trace.write_text(text)
            return subprocess.run(['python3', str(SCRIPT), str(trace)], capture_output=True, text=True)

    def test_failure_includes_study_and_returns_error(self):
        r = self.report('name\tstatus\texit\nprocess (GCST123_chr1)\tFAILED\t1\n')
        self.assertEqual(r.returncode, 1)
        self.assertIn('GCST123 | FAILED | exit 1', r.stdout)

    def test_unfinished_task_is_an_error(self):
        self.assertEqual(self.report('name\tstatus\texit\na\tRUNNING\t-\n').returncode, 1)

    def test_empty_and_invalid_trace_are_errors(self):
        for text in ('', 'name\tstatus\texit\n', 'name\tstatus\na\tCOMPLETED\n'):
            self.assertEqual(self.report(text).returncode, 2)

    def test_complete_and_cached_are_accepted(self):
        self.assertEqual(self.report('name\tstatus\texit\na\tCOMPLETED\t0\nb\tCACHED\t-\n').returncode, 0)

    def test_wrapper_reports_ignored_task_error_as_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            nextflow = root / 'nextflow'
            nextflow.write_text('#!/bin/bash\nwhile [ "$#" -gt 0 ]; do if [ "$1" = -with-trace ]; then printf "name\\tstatus\\texit\\nprocess (GCST123)\\tFAILED\\t1\\n" > "$2"; fi; shift; done\nexit 0\n')
            nextflow.chmod(0o755)
            r = subprocess.run(['bash', str(WRAPPER), str(root / 'trace.tsv'), 'run', 'pipeline'],
                               env=dict(os.environ, PATH=str(root)+os.pathsep+os.environ['PATH']),
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn('GCST123 | FAILED', r.stdout)


if __name__ == '__main__':
    unittest.main()
