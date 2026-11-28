from pathlib import Path
import tomllib


def test_pyproject_and_hanzo_config_present():
    root = Path(__file__).resolve().parent.parent
    pyproject = root / "pyproject.toml"
    assert pyproject.exists()
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert "project" in data
    assert (root / "hanzo.yml").exists()
    assert (root / "README.md").exists()
