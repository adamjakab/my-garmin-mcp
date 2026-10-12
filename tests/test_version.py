import tomllib
from pathlib import Path

from my_garmin_mcp import __version__


def test_package_version_matches_pyproject():
    pyproject = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text())
    assert __version__ == pyproject["project"]["version"]
