from pathlib import Path

import pandas as pd
import pytest

from app.modules.playbooks.normalizer import is_url, load_csv_source

"""
Unit tests for normalize_playbook_sheet.py
Qué valida este test

Valida que:

detectas bien si algo es URL o path
puedes leer archivo local
fallas correctamente si el archivo no existe
puedes leer URL sin pegarle a internet real, usando monkeypatch

Cómo correr estos tests localmente

Desde backend/:

PYTHONPATH=. pytest tests/unit/scripts/test_normalize_playbook_sheet.py -q

O todos los unit tests:

PYTHONPATH=. pytest tests/unit/scripts -q
"""


# -----------------------------
# is_url tests
# -----------------------------


def test_is_url_valid_https():
    assert is_url("https://example.com/file.csv") is True


def test_is_url_valid_http():
    assert is_url("http://example.com/file.csv") is True


def test_is_url_invalid_local_path():
    assert is_url("/app/data/sheets/IHUI.csv") is False


def test_is_url_invalid_relative():
    assert is_url("data/sheets/IHUI.csv") is False


# -----------------------------
# load_csv_source (local)
# -----------------------------


def test_load_csv_source_local_file(tmp_path: Path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("col1,col2\nA,1\nB,2\n", encoding="utf-8")

    df = load_csv_source(str(csv_file))

    assert list(df.columns) == ["col1", "col2"]
    assert len(df) == 2
    assert df.iloc[0]["col1"] == "A"
    assert df.iloc[1]["col2"] == 2


def test_load_csv_source_local_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_csv_source("/tmp/file_that_does_not_exist_123.csv")


# -----------------------------
# load_csv_source (URL)
# -----------------------------


def test_load_csv_source_url(monkeypatch):
    expected_df = pd.DataFrame(
        [
            {"name": "alpha", "value": 1},
            {"name": "beta", "value": 2},
        ]
    )

    def mock_read_csv(source):
        assert source == "https://example.com/export.csv"
        return expected_df

    monkeypatch.setattr(pd, "read_csv", mock_read_csv)

    df = load_csv_source("https://example.com/export.csv")

    assert list(df.columns) == ["name", "value"]
    assert len(df) == 2
    assert df.iloc[0]["name"] == "alpha"
