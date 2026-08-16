#!/usr/bin/env bash
#
# Builds the single delivery archive: one zip, one root folder, the whole
# runnable project inside it.
#
# The file list comes from `git ls-files`, which is the only definition of
# "the project" that cannot drift. It excludes, for free and without a
# hand-maintained ignore list: .venv, __pycache__, .env, storage/*.json
# (real user data), editor scratch, and every stale file nobody deleted.
#
# The one deliberate subtraction is train.csv and test.csv -- 74 MB the
# running application never opens. Predictions come from the fitted models
# in artifacts/, which ARE included, and data/README.md explains where the
# two training files go for anyone who wants to retrain.
#
# validation.csv STAYS. It is not training material to the running app: it
# is the split-conformal calibration set that uncertainty_service reads at
# startup to compute every prediction's confidence interval. Dropping it
# costs the product a feature, which a boot test of this archive is how we
# found out.
#
# Usage: bash scripts/build-delivery-zip.sh [output-dir]

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-$ROOT/../delivery}"
STAGE="$(mktemp -d)"
NAME="Digital-Wellness-AI"

trap 'rm -rf "$STAGE"' EXIT

cd "$ROOT"
mkdir -p "$OUT_DIR" "$STAGE/$NAME"

# What is left out, and how each one comes back. Everything here is
# tracked in git - this is a transport limit on the archive, not a
# statement that the repository does without them.
#
#   data/train.csv, data/test.csv          74 MB the running app never
#                                          opens; copy them across from
#                                          any existing checkout.
#   data/*_augmented.csv                   83 MB regenerated exactly by
#                                          `python3 -m models.augment_future_score`
#                                          in about a minute - it is
#                                          deterministic, same input,
#                                          same bytes.
#   artifacts/archive_*/*.pkl              20 MB of superseded models
#                                          kept as evidence; nothing
#                                          loads them. Copy across.
#
# validation.csv STAYS. It is not training material to the running app:
# it is the split-conformal calibration set that uncertainty_service
# reads at startup to compute every prediction's confidence interval.
# Dropping it costs the product a feature, which a boot test of this
# archive is how we found out.
OMITTED='^(data/(archive_pre_user_split_fix/.*|train|test)\.csv|data/[a-z]+_augmented\.csv|artifacts/archive_[^/]*/.*\.pkl)$'

git ls-files -z \
  | grep -zvE "$OMITTED" \
  | while IFS= read -r -d '' file; do
      mkdir -p "$STAGE/$NAME/$(dirname "$file")"
      cp -p "$file" "$STAGE/$NAME/$file"
    done

# Written into the archive so the list travels with it rather than
# living only in a chat message that scrolls away.
git ls-files | grep -E "$OMITTED" > "$STAGE/$NAME/OMITTED_FROM_ARCHIVE.txt"
cat >> "$STAGE/$NAME/OMITTED_FROM_ARCHIVE.txt" <<'NOTE'

# ---------------------------------------------------------------
# The files above are TRACKED IN GIT and are simply too large for this
# archive. Restore them before committing, or `git add -A` will stage
# their deletion:
#
#   data/train.csv, data/test.csv      copy from an existing checkout
#   artifacts/archive_*/*.pkl          copy from an existing checkout
#   data/*_augmented.csv               python3 -m models.augment_future_score
#
# Nothing here is needed to RUN the app - only to retrain it, and to
# keep the repository complete.
# ---------------------------------------------------------------
NOTE

# storage/ must exist for the app to start, and must arrive empty.
mkdir -p "$STAGE/$NAME/storage"
touch "$STAGE/$NAME/storage/.gitkeep"

ZIP="$OUT_DIR/$NAME.zip"
rm -f "$ZIP"
( cd "$STAGE" && zip -q -r -9 "$ZIP" "$NAME" )

echo "archive : $ZIP"
echo "size    : $(du -h "$ZIP" | cut -f1)"
echo "files   : $(unzip -l "$ZIP" | tail -1 | awk '{print $2}')"

# A zip that cannot be opened is not a delivery.
unzip -tqq "$ZIP" && echo "integrity: ok"

# Nothing private may ever leave in this file.
if unzip -l "$ZIP" | grep -qE '(\.env$|storage/[a-z_]+\.json|\.venv/|__pycache__)'; then
  echo "REFUSING: archive contains private or generated files" >&2
  exit 1
fi
echo "contents: no secrets, no user data, no build junk"
