#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Rebuild app/static/assets/css/tailwind.css
#
# Run this after adding a Tailwind class to any HTML file or JS file.
# Requires Node.js (any recent LTS). Nothing is left behind: the CLI is
# fetched with npx and the result is a single CSS file.
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
OUT="$ROOT/app/static/assets/css/tailwind.css"

printf '@tailwind base;\n@tailwind components;\n@tailwind utilities;\n' > "$HERE/.input.css"

echo "Scanning $ROOT/app/static for utility classes…"
npx --yes tailwindcss@3.4.17 \
  --config "$HERE/tailwind.config.js" \
  --input  "$HERE/.input.css" \
  --output "$OUT" \
  --minify

rm -f "$HERE/.input.css"
echo "Wrote $OUT ($(wc -c < "$OUT") bytes)"
