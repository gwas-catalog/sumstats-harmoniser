"""Exercise the chromosome process shell with empty and populated splits."""
import gzip
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'modules/local/harmonization.nf'
CONCATENATE = MODULE.parent / 'concatenate_chr_splits.nf'


class ChromosomeTests(unittest.TestCase):
    def run_task(self, content):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / 'input.merged').write_text(content)
        (root / 'metadata.yaml').write_text('coordinate_system: 1-based\n')
        bindir = root / 'bin'
        bindir.mkdir()
        for name, script in {
            'utils.py': 'echo header-args',
            'main_pysam.py': 'echo called > invoked; printf "chromosome\\tbase_pair_location\\thm_code\\n1\\t42\\t10\\n" > chr1.merged_unsorted.hm; printf "hm_code\\tcount\\tdescription\\n" | gzip > chr1.merged.log.tsv.gz',
        }.items():
            p = bindir / name
            p.write_text('#!/bin/sh\n' + script + '\n')
            p.chmod(0o755)
        script = MODULE.read_text().split('    shell:\n    """\n', 1)[1].rsplit('    """', 1)[0]
        script = script.replace('${params.ref}', '/reference').replace('${chrom}', 'chr1').replace('\\$', '$')
        env = dict(os.environ, GCST='GCST000123', chrom='chr1', merged='input.merged', yaml='metadata.yaml', palin_mode='forward', PATH=str(bindir)+os.pathsep+os.environ['PATH'])
        result = subprocess.run(['bash', '-ue', '-c', script], cwd=root, env=env, text=True, capture_output=True)
        return root, result

    def test_header_only_is_an_empty_chromosome_not_an_error(self):
        root, result = self.run_task('chromosome\tbase_pair_location\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((root / 'invoked').exists())
        self.assertEqual((root / 'chr1.merged.hm').read_text(), '')
        with gzip.open(root / 'chr1.merged.log.tsv.gz', 'rt') as f:
            self.assertEqual(f.read(), 'hm_code\tcount\tdescription\n')

    def test_empty_file_is_an_error(self):
        _, result = self.run_task('')
        self.assertNotEqual(result.returncode, 0)

    def test_populated_split_is_harmonised(self):
        root, result = self.run_task('chromosome\tbase_pair_location\n1\t42\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((root / 'invoked').exists())
        self.assertIn('1\t42\t10', (root / 'chr1.merged.hm').read_text())

    def test_concatenation_fails_when_all_chromosomes_are_empty(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'chr1.merged.hm').write_text('')
            (root / 'chrMT.merged.hm').write_text('')
            script = CONCATENATE.read_text().split('    shell:\n    """\n', 1)[1].rsplit('    """', 1)[0].replace('\\$', '$')
            result = subprocess.run(['bash', '-ue', '-c', script], cwd=root,
                                    env=dict(os.environ, GCST='GCST000123'), capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('no harmonized variant rows', result.stderr)

    def test_concatenation_retains_rows_when_first_split_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'chr1.merged.hm').write_text('')
            (root / 'chr2.merged.hm').write_text('chromosome\tposition\n2\t42\n')
            script = CONCATENATE.read_text().split('    shell:\n    """\n', 1)[1].rsplit('    """', 1)[0].replace('\\$', '$')
            result = subprocess.run(['bash', '-ue', '-c', script], cwd=root,
                                    env=dict(os.environ, GCST='GCST000123'), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / 'harmonised.tsv').read_text(), 'chromosome\tposition\n2\t42\n')


if __name__ == '__main__':
    unittest.main()
