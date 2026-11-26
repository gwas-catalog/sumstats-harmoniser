"""Exercise the publication module's rendered shell in an isolated directory."""

import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "modules/local/ftp_copy.nf"
STUDY = "GCST000123"


class FtpCopyChecksumTests(unittest.TestCase):
    def run_copy(self, data_matches=True, index_matches=True, source_present=True):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        task = root / "task"
        inputs = root / "inputs"
        ftp = root / "ftp"
        launch = root / "launch"
        final = launch / STUDY / "final"
        bindir = root / "bin"
        for directory in (task, inputs, ftp, final, bindir):
            directory.mkdir(parents=True, exist_ok=True)

        names = {
            "htsv": STUDY + ".h.tsv.gz",
            "tbi": STUDY + ".h.tsv.gz.tbi",
            "running_log": STUDY + ".running.log",
            "yaml": STUDY + ".h.tsv.gz-meta.yaml",
            "tsv": STUDY + ".tsv.gz",
            "raw_yaml": STUDY + ".tsv.gz-meta.yaml",
        }
        (final / names["htsv"]).write_bytes(b"expected data")
        (final / names["tbi"]).write_bytes(b"expected index")
        if not source_present:
            (final / names["htsv"]).unlink()
        (task / names["htsv"]).write_bytes(b"expected data" if data_matches else b"different data")
        (task / names["tbi"]).write_bytes(b"expected index" if index_matches else b"different index")
        for key in ("running_log", "yaml", "tsv", "raw_yaml"):
            (task / names[key]).write_text("fixture\n")
        for key in ("tsv", "raw_yaml"):
            (inputs / names[key]).write_text("fixture\n")
        accession = bindir / "accession_id.sh"
        accession.write_text("#!/bin/sh\nprintf '%s\\n' GCST000001-GCST001000\n")
        accession.chmod(0o755)

        template = MODULE.read_text().split('    shell:\n    """\n', 1)[1].rsplit('    """', 1)[0]
        template = template.replace("${params.ftp}", str(ftp))
        template = template.replace("${params.all_harm_folder}", str(inputs))
        template = template.replace("${launchDir}", str(launch))
        template = template.replace("\\$", "$")
        env = dict(os.environ, GCST=STUDY, PATH=str(bindir) + os.pathsep + os.environ["PATH"], **names)
        result = subprocess.run(
            ["bash", "-ue", "-c", template + '\nprintf "RESULT=%s\\n" "$copy"\n'],
            cwd=task, env=env, capture_output=True, text=True, check=True,
        )
        return result.stdout, inputs, ftp, launch, names

    def test_mismatched_data_does_not_report_success_or_remove_input(self):
        output, inputs, _, launch, names = self.run_copy(data_matches=False)
        self.assertIn("RESULT=failed_copy", output)
        self.assertTrue((inputs / names["tsv"]).is_file())
        self.assertTrue((inputs / names["raw_yaml"]).is_file())
        self.assertTrue((launch / STUDY).is_dir())

    def test_mismatched_index_does_not_report_success_or_remove_input(self):
        output, inputs, _, launch, names = self.run_copy(index_matches=False)
        self.assertIn("RESULT=failed_copy", output)
        self.assertTrue((inputs / names["tsv"]).is_file())
        self.assertTrue((launch / STUDY).is_dir())

    def test_missing_checksum_source_does_not_remove_input(self):
        output, inputs, _, launch, names = self.run_copy(source_present=False)
        self.assertIn("RESULT=failed_copy", output)
        self.assertTrue((inputs / names["tsv"]).is_file())
        self.assertTrue((launch / STUDY).is_dir())

    def test_matching_bundle_records_checksums_and_removes_staged_inputs(self):
        output, inputs, ftp, _, names = self.run_copy()
        self.assertIn("RESULT=copied", output)
        self.assertFalse((inputs / names["tsv"]).exists())
        folder = ftp / "GCST000001-GCST001000" / STUDY / "harmonised"
        expected = "{}  {}\n{}  {}\n".format(
            hashlib.md5(b"expected data").hexdigest(), names["htsv"],
            hashlib.md5(b"expected index").hexdigest(), names["tbi"],
        )
        self.assertEqual((folder / "md5sum.txt").read_text(), expected)


if __name__ == "__main__":
    unittest.main()
