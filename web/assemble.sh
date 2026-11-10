#!/bin/sh
# Copy the static page and the Python modules it imports into one directory.
set -eu
cd "$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
out="${1:-_site}"
if [ -z "$out" ] || [ "$out" = "/" ]; then
  echo "refusing to assemble into '$out'" >&2
  exit 1
fi
rm -rf "$out"
mkdir -p "$out/app" "$out/data" "$out/scripts" "$out/fastavro" "$out/fonts"
cp web/index.html web/styles.css web/main.js web/runtime.py "$out/"
cp web/avro_container.py "$out/fastavro/__init__.py"
cp web/fonts/*.woff2 web/fonts/OFL.txt "$out/fonts/"
cp app/__init__.py app/analytics.py app/avro_io.py app/database.py app/repository.py app/settings.py app/validation.py "$out/app/"
cp data/departments.csv data/jobs.csv data/hired_employees.csv "$out/data/"
cp scripts/load_historical.py "$out/scripts/"
touch "$out/.nojekyll"
