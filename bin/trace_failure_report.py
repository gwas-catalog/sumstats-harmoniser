#!/usr/bin/env python3
"""Fail a batch review when a Nextflow trace has failed or unfinished tasks."""
import argparse
import collections
import csv
import re
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', help='Nextflow TSV trace for a finished run')
    args = parser.parse_args()
    try:
        with open(args.trace, newline='', encoding='utf-8') as handle:
            reader = csv.DictReader(handle, delimiter='\t')
            if not reader.fieldnames or not {'name', 'status', 'exit'} <= set(reader.fieldnames):
                raise ValueError('trace must have name, status and exit columns')
            rows = list(reader)
        if not rows:
            raise ValueError('trace has no task records')
        counts = collections.Counter(row['status'] for row in rows)
        print('Task statuses: ' + ', '.join(f'{s}={n}' for s, n in sorted(counts.items())))
        problems = [r for r in rows if not (r['status'] == 'COMPLETED' and r['exit'] == '0')
                    and not (r['status'] == 'CACHED' and r['exit'] in ('0', '-'))]
        for row in problems:
            match = re.search(r'GCST\d+', row['name'])
            study = match.group() if match else 'unknown-study'
            print(f"{study} | {row['status']} | exit {row['exit']} | {row['name']}")
        if problems:
            print(f'REVIEW REQUIRED: {len(problems)} failed or unfinished tasks', file=sys.stderr)
            return 1
        print('All recorded tasks completed or were cached. Verify expected studies and output bundles separately.')
        return 0
    except (OSError, ValueError, csv.Error) as exc:
        print(f'Cannot assess trace: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
