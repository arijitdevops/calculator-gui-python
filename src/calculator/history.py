"""Persistent calculation history backed by a JSON file.

The store keeps the most recent entries first and is capped so the file cannot
grow without bound.  Every filesystem access is guarded: a calculator that
cannot write its history should still start and still calculate.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

LOGGER = logging.getLogger(__name__)

__all__ = ["HistoryEntry", "HistoryStore", "default_history_path", "default_history_limit"]

#: Fallback cap on stored entries.
DEFAULT_LIMIT = 100

#: Directory name used under the per-user configuration root.
APP_DIRECTORY = "PyCalculator"


@dataclass(frozen=True)
class HistoryEntry:
    """One completed calculation."""

    expression: str
    result: str
    timestamp: str

    @classmethod
    def create(cls, expression: str, result: str) -> HistoryEntry:
        """Build an entry stamped with the current UTC time."""
        return cls(
            expression=expression.strip(),
            result=result.strip(),
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> Optional[HistoryEntry]:
        """Build an entry from decoded JSON, or ``None`` if the record is unusable."""
        expression = payload.get("expression")
        result = payload.get("result")
        if not isinstance(expression, str) or not isinstance(result, str):
            return None
        timestamp = payload.get("timestamp")
        if not isinstance(timestamp, str):
            timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return cls(expression=expression, result=result, timestamp=timestamp)

    def as_display_text(self) -> str:
        """Return the single line shown in the history panel."""
        return f"{self.expression} = {self.result}"


def user_config_directory() -> Path:
    """Return the per-user configuration directory for this application."""
    if sys.platform.startswith("win"):
        root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(root) / APP_DIRECTORY
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIRECTORY
    root = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(root) / APP_DIRECTORY.lower()


def default_history_path() -> Path:
    """Return the history file path, honouring ``CALCULATOR_HISTORY_FILE``."""
    override = os.environ.get("CALCULATOR_HISTORY_FILE")
    if override:
        return Path(override).expanduser()
    return user_config_directory() / "history.json"


def default_history_limit() -> int:
    """Return the entry cap, honouring ``CALCULATOR_HISTORY_LIMIT``."""
    raw = os.environ.get("CALCULATOR_HISTORY_LIMIT")
    if not raw:
        return DEFAULT_LIMIT
    try:
        limit = int(raw)
    except ValueError:
        LOGGER.warning(
            "CALCULATOR_HISTORY_LIMIT=%r is not an integer; using %d", raw, DEFAULT_LIMIT
        )
        return DEFAULT_LIMIT
    if limit < 1:
        LOGGER.warning("CALCULATOR_HISTORY_LIMIT must be positive; using %d", DEFAULT_LIMIT)
        return DEFAULT_LIMIT
    return limit


class HistoryStore:
    """Newest-first list of :class:`HistoryEntry` persisted as JSON.

    Args:
        path: Where to read and write.  Defaults to :func:`default_history_path`.
        limit: Maximum number of entries retained.  Defaults to
            :func:`default_history_limit`.
    """

    def __init__(self, path: Optional[Path] = None, limit: Optional[int] = None) -> None:
        self.path: Path = Path(path) if path is not None else default_history_path()
        self.limit: int = limit if limit is not None else default_history_limit()
        self._entries: List[HistoryEntry] = []

    @property
    def entries(self) -> List[HistoryEntry]:
        """A copy of the stored entries, newest first."""
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def load(self) -> List[HistoryEntry]:
        """Read the history file into memory.

        A missing, unreadable or corrupt file yields an empty history and is
        logged rather than raised: history is a convenience, not a dependency.
        """
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self._entries = []
            return self.entries
        except OSError as exc:
            LOGGER.warning("Could not read history from %s: %s", self.path, exc)
            self._entries = []
            return self.entries

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            LOGGER.warning("History file %s is not valid JSON (%s); starting empty", self.path, exc)
            self._entries = []
            return self.entries

        records = payload.get("entries") if isinstance(payload, dict) else payload
        if not isinstance(records, list):
            LOGGER.warning("History file %s has an unexpected shape; starting empty", self.path)
            self._entries = []
            return self.entries

        entries: List[HistoryEntry] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            entry = HistoryEntry.from_dict(record)
            if entry is not None:
                entries.append(entry)
        self._entries = entries[: self.limit]
        return self.entries

    def add(self, expression: str, result: str) -> HistoryEntry:
        """Record a calculation at the top of the history and persist it."""
        entry = HistoryEntry.create(expression, result)
        self._entries.insert(0, entry)
        del self._entries[self.limit :]
        self.save()
        return entry

    def clear(self) -> None:
        """Drop every entry and persist the empty history."""
        self._entries = []
        self.save()

    def save(self) -> bool:
        """Write the history to disk.

        Returns:
            ``True`` when the file was written, ``False`` when the write failed
            (which is logged and otherwise ignored).
        """
        payload = {
            "version": 1,
            "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "entries": [asdict(entry) for entry in self._entries],
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            os.replace(temporary, self.path)
            return True
        except OSError as exc:
            LOGGER.warning("Could not write history to %s: %s", self.path, exc)
            return False
