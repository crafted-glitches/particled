class Particled < Formula
  include Language::Python::Virtualenv

  desc "Audio-reactive particle visualizer"
  homepage "https://github.com/crafted-glitches/particled"
  url "https://files.pythonhosted.org/packages/source/p/particled/particled-0.1.0.tar.gz"
  sha256 "REPLACE_WITH_RELEASE_SHA256"
  license "MIT"

  depends_on "python@3.13"
  depends_on "portaudio"
  depends_on "glfw"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "particled", shell_output("#{bin}/particled --version")
  end
end
