#!/bin/bash
# Run Nextflow with a known trace path and fail if the trace contains task errors.
set -u
if [ "$#" -lt 2 ]; then
    echo 'Usage: nextflow_with_failure_report.sh TRACE NEXTFLOW_ARGS...' >&2
    exit 2
fi
trace=$1
shift
if [ -e "$trace" ]; then
    echo "Refusing to overwrite existing trace: $trace" >&2
    exit 2
fi
script_dir=$(cd "$(dirname "$0")" && pwd)
nextflow "$@" -with-trace "$trace"
nextflow_status=$?
python3 "$script_dir/trace_failure_report.py" "$trace"
report_status=$?
if [ "$nextflow_status" -ne 0 ] || [ "$report_status" -ne 0 ]; then
    echo "Harmonisation needs review: Nextflow exit=$nextflow_status, trace review exit=$report_status" >&2
    exit 1
fi
exit 0
