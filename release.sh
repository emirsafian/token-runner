#!/bin/sh
# Cut a release and fill in the Homebrew formula in one go.
#
# Run this AFTER the project is on GitHub (you've done git init, commit, push,
# and 'origin' points at your GitHub repo).
#
#   ./release.sh 0.1.0                   tag it and fill Formula/tokenrun.rb
#   ./release.sh 0.1.0 ../homebrew-tap   also copy the formula into your tap repo
#
# It tags vX.Y.Z, pushes the tag, downloads the release tarball to get its
# sha256, and writes the version, your GitHub owner, and that sha256 into the
# formula.
set -eu

VERSION="${1:-}"
TAP_DIR="${2:-}"
if [ -z "$VERSION" ]; then
  echo "usage: ./release.sh <version> [path-to-homebrew-tap]   e.g. ./release.sh 0.1.0" >&2
  exit 1
fi
TAG="v${VERSION}"

for tool in git curl shasum; do
  command -v "$tool" >/dev/null 2>&1 || { echo "need $tool on PATH" >&2; exit 1; }
done

REMOTE="$(git remote get-url origin 2>/dev/null || true)"
[ -n "$REMOTE" ] || { echo "No 'origin' remote. Push the repo to GitHub first." >&2; exit 1; }
SLUG="$(printf '%s' "$REMOTE" | sed -E 's#^git@[^:]+:##; s#^https?://[^/]+/##; s#\.git$##')"
OWNER="${SLUG%%/*}"
REPO="${SLUG##*/}"

echo "repo:    $OWNER/$REPO"
echo "version: $TAG"
printf "tag and push %s to origin? [y/N] " "$TAG"
read ans || ans=""
case "$ans" in y|Y|yes) ;; *) echo "aborted." ; exit 1 ;; esac

git tag "$TAG"
git push origin "$TAG"

URL="https://github.com/${OWNER}/${REPO}/archive/refs/tags/${TAG}.tar.gz"
echo "fetching tarball for its checksum..."
SHA="$(curl -fsSL "$URL" | shasum -a 256 | cut -d ' ' -f1)"
[ -n "$SHA" ] || { echo "could not read a checksum from $URL" >&2; exit 1; }
echo "sha256:  $SHA"

F="Formula/tokenrun.rb"
sed -i.bak -E \
  -e "s#/refs/tags/v[0-9][0-9.]*\.tar\.gz#/refs/tags/${TAG}.tar.gz#g" \
  -e "s#sha256 \"[^\"]*\"#sha256 \"${SHA}\"#" \
  "$F"
rm -f "$F.bak"
echo "filled $F"

if [ -n "$TAP_DIR" ]; then
  mkdir -p "$TAP_DIR/Formula"
  cp "$F" "$TAP_DIR/Formula/tokenrun.rb"
  ( cd "$TAP_DIR" && git add Formula/tokenrun.rb \
      && git commit -m "tokenrun ${VERSION}" && git push )
  echo "pushed the formula to $TAP_DIR"
fi

echo
echo "done. commit the filled formula:"
echo "  git add $F && git commit -m \"tokenrun ${VERSION}\" && git push"
if [ -z "$TAP_DIR" ]; then
  echo
  echo "first release only: make a repo named 'homebrew-tap' and copy $F"
  echo "into it as Formula/tokenrun.rb (or re-run with the tap path as arg 2)."
fi
echo
echo "people then install with:"
echo "  brew install ${OWNER}/tap/tokenrun"
