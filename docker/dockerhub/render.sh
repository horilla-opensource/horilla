#!/bin/sh
# Render a Docker Hub description from the template + a notice fragment.
#
# Usage: render.sh <variant> <version>
#   variant: canonical | legacy
#   version: e.g. 1.13.8   (substituted into __VERSION__)
#
# Writes the rendered markdown to stdout. Run from the repo root.
set -eu

VARIANT="${1:?usage: render.sh <canonical|legacy> <version>}"
VERSION="${2:?usage: render.sh <canonical|legacy> <version>}"
DIR="docker/dockerhub"

case "$VARIANT" in
  canonical) NOTICE="$DIR/notice-canonical.md" ;;
  legacy)    NOTICE="$DIR/notice-legacy.md" ;;
  *) echo "unknown variant: $VARIANT" >&2; exit 1 ;;
esac

# awk rather than sed: the notice is multi-line markdown containing slashes,
# backticks and newlines, all of which need escaping in a sed replacement.
awk -v notice_file="$NOTICE" '
  /^__NOTICE__$/ {
    while ((getline line < notice_file) > 0) print line
    next
  }
  { print }
' "$DIR/README.md" | sed "s/__VERSION__/$VERSION/g"
