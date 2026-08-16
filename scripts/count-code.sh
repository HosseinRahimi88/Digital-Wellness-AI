#!/usr/bin/env bash
# The counts quoted in docs/reports/PROJECT_MAP.md and README.md, from the tree itself.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "endpoints    $(grep -rhoE '@router\.(get|post|put|patch|delete)' api/routers | wc -l)"
echo "routers      $(ls api/routers/*.py | grep -v __init__ | wc -l)"
echo "services     $(find services -name '*.py' ! -name '__init__.py' | wc -l)"
echo "js modules   $(find frontend/assets/js -name '*.js' | wc -l)"
echo "pages        $(ls frontend/*.html | wc -l)"
echo "stylesheets  $(ls frontend/assets/css/*.css | wc -l)"
echo "test files   $(find tests -name 'test_*.py' | wc -l)"
echo "schema fields $(python3 -c 'from core.feature_schema import FEATURE_SCHEMA; print(len(FEATURE_SCHEMA))' 2>/dev/null || echo '?')"
