#!/usr/bin/env bash
# Fetch (vendor) the front-end libraries used by the web UI into
# static/vendor/. Idempotent: already-present files are skipped.
# Primary registry is npmmirror (this host is on a China network);
# registry.npmjs.org is the fallback.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR="$HERE/static/vendor"
mkdir -p "$VENDOR"

MARKED_VER=12.0.2
KATEX_VER=0.16.11
CHARTJS_VER=4.4.4

MIRRORS=(
  "https://registry.npmmirror.com"
  "https://registry.npmjs.org"
)

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# fetch_pkg <name> <version> -> extracts tarball into $TMP/<name>/package
fetch_pkg() {
  local name="$1" ver="$2" tgz="$TMP/$1-$2.tgz" ok=""
  [ -d "$TMP/$name/package" ] && return 0
  for reg in "${MIRRORS[@]}"; do
    echo "  downloading $name@$ver from $reg ..."
    if curl -fL --retry 3 --connect-timeout 15 -o "$tgz" \
        "$reg/$name/-/$name-$ver.tgz"; then
      ok=1; break
    fi
  done
  [ -n "$ok" ] || { echo "ERROR: cannot download $name@$ver" >&2; exit 1; }
  mkdir -p "$TMP/$name"
  tar -xzf "$tgz" -C "$TMP/$name"
}

# ---- marked -----------------------------------------------------------
if [ -f "$VENDOR/marked/marked.min.js" ]; then
  echo "marked: already present, skip"
else
  echo "marked@$MARKED_VER:"
  fetch_pkg marked "$MARKED_VER"
  mkdir -p "$VENDOR/marked"
  if [ -f "$TMP/marked/package/marked.min.js" ]; then
    cp "$TMP/marked/package/marked.min.js" "$VENDOR/marked/marked.min.js"
  else
    cp "$TMP/marked/package/lib/marked.umd.js" "$VENDOR/marked/marked.min.js"
  fi
  echo "marked: done"
fi

# ---- KaTeX (js + css + auto-render + fonts) ---------------------------
if [ -f "$VENDOR/katex/katex.min.js" ] && [ -f "$VENDOR/katex/katex.min.css" ] \
   && [ -f "$VENDOR/katex/auto-render.min.js" ] && [ -d "$VENDOR/katex/fonts" ]; then
  echo "katex: already present, skip"
else
  echo "katex@$KATEX_VER:"
  fetch_pkg katex "$KATEX_VER"
  mkdir -p "$VENDOR/katex"
  cp "$TMP/katex/package/dist/katex.min.js"  "$VENDOR/katex/"
  cp "$TMP/katex/package/dist/katex.min.css" "$VENDOR/katex/"
  cp "$TMP/katex/package/dist/contrib/auto-render.min.js" "$VENDOR/katex/"
  rm -rf "$VENDOR/katex/fonts"
  cp -r "$TMP/katex/package/dist/fonts" "$VENDOR/katex/fonts"
  echo "katex: done"
fi

# ---- Chart.js ---------------------------------------------------------
if [ -f "$VENDOR/chartjs/chart.umd.js" ]; then
  echo "chartjs: already present, skip"
else
  echo "chart.js@$CHARTJS_VER:"
  fetch_pkg chart.js "$CHARTJS_VER"
  mkdir -p "$VENDOR/chartjs"
  cp "$TMP/chart.js/package/dist/chart.umd.js" "$VENDOR/chartjs/"
  echo "chartjs: done"
fi

echo "vendor files ready under $VENDOR"
