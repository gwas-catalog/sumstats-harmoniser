"""Exercise the failed-copy task shell without a production filesystem."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "modules/local/failed_copy.nf"
STUDY = "GCST000123"
BUCKET = "GCST000001-GCST001000"


class FailedCopyPublicationTests(unittest.TestCase):
    def run_failed_copy(self, existing_bundle=False, has_log=True):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        task = root / "task"
        ftp = root / "ftp"
        launch = root / "launch"
        bindir = root / "bin"
        for directory in (task, ftp, launch / STUDY, bindir):
            directory.mkdir(parents=True, exist_ok=True)
        report = STUDY + ".running.log"
        if has_log:
            (task / report).write_text("Result\tFAILED_HARMONIZATION\n")
        if existing_bundle:
            folder = ftp / BUCKET / STUDY / "harmonised"
            folder.mkdir(parents=True)
            (folder / (STUDY + ".h.tsv.gz")).write_bytes(b"existing bundle")
        accession = bindir / "accession_id.sh"
        accession.write_text("#!/bin/sh\nprintf '%s\\n' GCST000001-GCST001000\n")
        accession.chmod(0o755)

        template = MODULE.read_text().split('    shell:\n    """\n', 1)[1].rsplit('    """', 1)[0]
        template = template.replace("${params.ftp}", str(ftp))
        template = template.replace("${launchDir}", str(launch))
        template = template.replace("\\$", "$")
        env = dict(os.environ, GCST=STUDY, running_log=report,
                   PATH=str(bindir) + os.pathsep + os.environ["PATH"])
        result = subprocess.run(
            ["bash", "-ue", "-c", template + '\nprintf "RESULT=%s\\n" "$copy"\n'],
            cwd=task, env=env, capture_output=True, text=True, check=True,
        )
        return result.stdout, ftp, report

    def test_failure_does_not_create_public_harmonised_directory(self):
        output, ftp, report = self.run_failed_copy()
        self.assertIn("RESULT=copied", output)
        self.assertFalse((ftp / BUCKET / STUDY / "harmonised").exists())
        self.assertEqual((ftp / report).read_text(), "Result\tFAILED_HARMONIZATION\n")

    def test_failure_without_report_does_not_create_public_folder(self):
        _, ftp, _ = self.run_failed_copy(has_log=False)
        self.assertFalse((ftp / BUCKET / STUDY / "harmonised").exists())

    def test_failure_preserves_existing_published_data(self):
        _, ftp, _ = self.run_failed_copy(existing_bundle=True)
        data = ftp / BUCKET / STUDY / "harmonised" / (STUDY + ".h.tsv.gz")
        self.assertEqual(data.read_bytes(), b"existing bundle")


if __name__ == "__main__":
    unittest.main()
