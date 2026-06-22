#!/usr/bin/env bash
# Sync generated SDK code from the sdk-gen workspace into this repo.
#
# Usage: ./scripts/sync-generated.sh <path/to/sdk-gen/out/python>
#
# Copies only files that the emitter owns. Hand-written runtime/domain files
# (_base_client.py, _async_base_client.py, _config.py, _retries.py, sandbox.py)
# are preserved.

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <path/to/sdk-gen/out/python>" >&2
    exit 1
fi

SRC="$1"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -d "$SRC/porter_sandbox" ]]; then
    echo "Error: $SRC/porter_sandbox not found" >&2
    exit 1
fi

# Files the emitter owns (overwrite freely).
# Note: porter_sandbox/__init__.py is hand-written (it re-exports the public
# client/domain classes alongside generated wrappers). Don't sync it.
GENERATED_FILES=(
    porter_sandbox/_client.py
    porter_sandbox/_errors.py
    porter_sandbox/_models.py
    porter_sandbox/enums.py
)

for f in "${GENERATED_FILES[@]}"; do
    if [[ -f "$SRC/$f" ]]; then
        cp "$SRC/$f" "$REPO_ROOT/$f"
        echo "  copied $f"
    fi
done

# Public client and namespace wrappers are generated too. Copy top-level
# generated modules, but preserve hand-written runtime/domain modules.
for f in "$SRC"/porter_sandbox/*.py; do
    name="$(basename "$f")"
    case "$name" in
        __init__.py|_*.py|enums.py|sandbox.py)
            continue
            ;;
    esac
    cp "$f" "$REPO_ROOT/porter_sandbox/$name"
    echo "  copied porter_sandbox/$name"
done

# Resources are a whole directory.
rm -rf "$REPO_ROOT/porter_sandbox/resources"
cp -r "$SRC/porter_sandbox/resources" "$REPO_ROOT/porter_sandbox/resources"
echo "  copied porter_sandbox/resources/"

# Generated tests go alongside hand-written ones.
mkdir -p "$REPO_ROOT/tests"
if [[ -f "$SRC/tests/test_models_round_trip.py" ]]; then
    cp "$SRC/tests/test_models_round_trip.py" "$REPO_ROOT/tests/test_models_round_trip.py"
    echo "  copied tests/test_models_round_trip.py"
fi

echo "Done."
