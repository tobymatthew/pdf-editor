import pytest

from app import config


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "documents"
    monkeypatch.setattr(config, "DATA_DIR", str(data_dir))
    return data_dir
