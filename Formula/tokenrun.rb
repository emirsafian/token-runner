# Homebrew formula for token-runner (the `tokenrun` command).
#
# The live formula lives in the emirsafian/homebrew-tap repo. To cut a release:
# tag it, get the tarball sha256, fill the version + sha below, and copy this
# file into the tap as Formula/tokenrun.rb. (release.sh automates version + sha.)
class Tokenrun < Formula
  desc "Terminal speedometer and pixel runner game for your AI coding token usage"
  homepage "https://github.com/emirsafian/token-runner"
  url "https://github.com/emirsafian/token-runner/archive/refs/tags/v0.2.0.tar.gz"
  sha256 "642c5c4d14154a8c9b45b048d7001d54680d1b899e8a56001add9a75b77861a4"
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
