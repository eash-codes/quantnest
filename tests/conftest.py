import pytest

@pytest.fixture(autouse=True)
def isolate_cwd(tmp_path, monkeypatch):
    # Ensures Path("data/...") is under a fresh temp folder for every test
    monkeypatch.chdir(tmp_path)
