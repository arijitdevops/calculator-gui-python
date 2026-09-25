"""Tests for the JSON-backed history store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from calculator.history import (
    HistoryEntry,
    HistoryStore,
    default_history_limit,
    default_history_path,
)


@pytest.fixture()
def store(tmp_path: Path) -> HistoryStore:
    """A history store pointed at a throwaway file."""
    return HistoryStore(path=tmp_path / "history.json", limit=5)


class TestHistoryEntry:
    def test_create_strips_and_stamps(self) -> None:
        entry = HistoryEntry.create("  1 + 1 ", " 2 ")
        assert entry.expression == "1 + 1"
        assert entry.result == "2"
        assert entry.timestamp.startswith("20")

    def test_display_text(self) -> None:
        assert HistoryEntry.create("2*3", "6").as_display_text() == "2*3 = 6"

    def test_from_dict_rejects_bad_records(self) -> None:
        assert HistoryEntry.from_dict({"expression": 1, "result": "2"}) is None
        assert HistoryEntry.from_dict({"result": "2"}) is None

    def test_from_dict_supplies_a_missing_timestamp(self) -> None:
        entry = HistoryEntry.from_dict({"expression": "1+1", "result": "2"})
        assert entry is not None and entry.timestamp


class TestHistoryStore:
    def test_starts_empty_when_the_file_is_missing(self, store: HistoryStore) -> None:
        assert store.load() == []
        assert len(store) == 0

    def test_add_puts_the_newest_entry_first(self, store: HistoryStore) -> None:
        store.add("1+1", "2")
        store.add("2+2", "4")
        assert [entry.expression for entry in store.entries] == ["2+2", "1+1"]

    def test_entries_survive_a_reload(self, store: HistoryStore) -> None:
        store.add("6*7", "42")
        reopened = HistoryStore(path=store.path, limit=store.limit)
        assert [entry.result for entry in reopened.load()] == ["42"]

    def test_limit_is_enforced(self, store: HistoryStore) -> None:
        for index in range(12):
            store.add(f"{index}+0", str(index))
        assert len(store) == 5
        assert store.entries[0].expression == "11+0"

    def test_limit_is_enforced_on_load(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        records = [
            {"expression": f"{i}", "result": f"{i}", "timestamp": "2024-01-01T00:00:00+00:00"}
            for i in range(30)
        ]
        path.write_text(json.dumps({"version": 1, "entries": records}), encoding="utf-8")
        assert len(HistoryStore(path=path, limit=4).load()) == 4

    def test_clear_empties_the_file(self, store: HistoryStore) -> None:
        store.add("1+1", "2")
        store.clear()
        assert store.entries == []
        assert json.loads(store.path.read_text(encoding="utf-8"))["entries"] == []

    def test_corrupt_file_is_tolerated(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text("{not json at all", encoding="utf-8")
        assert HistoryStore(path=path).load() == []

    def test_unexpected_shape_is_tolerated(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text(json.dumps({"entries": "nope"}), encoding="utf-8")
        assert HistoryStore(path=path).load() == []

    def test_bad_records_are_skipped(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text(
            json.dumps({"entries": [{"expression": "1+1", "result": "2"}, "junk", {"nope": True}]}),
            encoding="utf-8",
        )
        assert len(HistoryStore(path=path).load()) == 1

    def test_a_plain_list_is_accepted(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text(json.dumps([{"expression": "9-4", "result": "5"}]), encoding="utf-8")
        assert HistoryStore(path=path).load()[0].result == "5"

    def test_save_creates_missing_directories(self, tmp_path: Path) -> None:
        store = HistoryStore(path=tmp_path / "deep" / "nested" / "history.json")
        store.add("1+1", "2")
        assert store.path.is_file()


class TestConfiguration:
    def test_history_path_env_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "custom.json"
        monkeypatch.setenv("CALCULATOR_HISTORY_FILE", str(target))
        assert default_history_path() == target

    def test_limit_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CALCULATOR_HISTORY_LIMIT", "7")
        assert default_history_limit() == 7

    @pytest.mark.parametrize("raw", ["not-a-number", "0", "-3"])
    def test_invalid_limit_falls_back(self, raw: str, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CALCULATOR_HISTORY_LIMIT", raw)
        assert default_history_limit() == 100
