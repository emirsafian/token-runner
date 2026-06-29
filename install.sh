#!/bin/sh
# Installs tokenrun. Pure Python, no dependencies.
#
#   curl -fsSL https://raw.githubusercontent.com/emirsafian/token-runner/main/install.sh | sh
#
# Fetches the tokenrun package into ~/.local/share/tokenrun and adds a small
# `tokenrun` launcher to ~/.local/bin. To uninstall, delete both.
set -eu

REPO="${TOKENRUN_REPO:-emirsafian/token-runner}"
BRANCH="${TOKENRUN_BRANCH:-main}"

LIB="${HOME}/.local/share/tokenrun"
BIN="${HOME}/.local/bin"

command -v python3 >/dev/null 2>&1 || { echo "This needs Python 3. Install it and run again." >&2; exit 1; }
command -v curl    >/dev/null 2>&1 || { echo "This needs curl." >&2; exit 1; }
command -v tar     >/dev/null 2>&1 || { echo "This needs tar." >&2; exit 1; }

echo "Downloading tokenrun..."
mkdir -p "$LIB" "$BIN"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
curl -fsSL "https://codeload.github.com/${REPO}/tar.gz/refs/heads/${BRANCH}" | tar -xzf - -C "$tmp"
pkg="$(find "$tmp" -maxdepth 2 -type d -name tokenrun | head -n1)"
[ -n "$pkg" ] || { echo "Could not find the tokenrun package in the download." >&2; exit 1; }
rm -rf "$LIB/tokenrun"
cp -R "$pkg" "$LIB/tokenrun"

wrapper="${BIN}/tokenrun"
printf '#!/bin/sh\nexec env PYTHONPATH="%s" python3 -m tokenrun "$@"\n' "$LIB" > "$wrapper"
chmod +x "$wrapper"

echo "Done. Installed 'tokenrun' to ${BIN}."

case ":${PATH}:" in
  *":${BIN}:"*) ;;
  *)
    echo
    echo "One more thing: ${BIN} isn't on your PATH yet. Add it with:"
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc"
    ;;
esac
