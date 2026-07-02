# Homebrew formula for token-runner (the `tokenrun` command).
#
# The live formula lives in the emirsafian/homebrew-tap repo. To cut a release:
# tag it, get the tarball sha256, fill the version + sha below, and copy this
# file into the tap as Formula/tokenrun.rb. (release.sh automates version + sha.)
class Tokenrun < Formula
  desc "Terminal speedometer and pixel runner game for your AI coding token usage"
  homepage "https://github.com/emirsafian/token-runner"
  url "https://github.com/emirsafian/token-runner/archive/refs/tags/v0.3.0.tar.gz"
  sha256 "5ef961d4149ecf3222c37144e55e2561a28fc3a89120825a666131161c07278c"
  license "MIT"

  def install
    libexec.install "tokenrun"
    (bin/"tokenrun").write <<~SH
      #!/bin/sh
      exec env PYTHONPATH="#{libexec}" python3 -m tokenrun "$@"
    SH
  end

  test do
    system bin/"tokenrun", "--once", "--width", "60"
  end
end
