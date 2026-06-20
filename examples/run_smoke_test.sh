#!/usr/bin/env bash
# Validate a doc-bench install against the 33 bundled fixtures.
#
# Exit code 0 = pass (clean run, schema-valid, low rejection rate).
# From a source checkout, this uses `uv run`; an installed wheel exposes the
# command directly as `doc-bench-smoke-test`.
#
# Usage:
#   ./examples/run_smoke_test.sh
set -euo pipefail

if command -v doc-bench-smoke-test >/dev/null 2>&1; then
    doc-bench-smoke-test
else
    uv run doc-bench-smoke-test
fi
