"""Append-only JSONL governance audit log with thread-safe writes."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class BusEntry:
    timestamp: float
    agent: str
    event_type: str
    message: str
    content_hash: str


class GovernanceBus:
    def __init__(self, path: Optional[Path] = None):
        self._path = path
        self._entries: list[BusEntry] = []
        self._lock = threading.RLock()
        if path and path.exists():
            self._load()

    def post(self, agent: str, event_type: str, message: str) -> BusEntry:
        content = f"{agent}:{event_type}:{message}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        entry = BusEntry(
            timestamp=time.time(), agent=agent,
            event_type=event_type, message=message,
            content_hash=content_hash,
        )
        with self._lock:
            self._entries.append(entry)
            if self._path:
                self._append(entry)
        return entry

    def query(
        self,
        agent: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 100,
    ) -> list[BusEntry]:
        with self._lock:
            results = []
            for entry in reversed(self._entries):
                if agent and entry.agent != agent:
                    continue
                if event_type and entry.event_type != event_type:
                    continue
                if since and entry.timestamp < since:
                    continue
                results.append(entry)
                if len(results) >= limit:
                    break
            return list(reversed(results))

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def _append(self, entry: BusEntry) -> None:
        line = json.dumps({
            "ts": entry.timestamp, "agent": entry.agent,
            "type": entry.event_type, "msg": entry.message,
            "hash": entry.content_hash,
        })
        with open(self._path, "a") as f:
            f.write(line + "\n")

    def _load(self) -> None:
        for line in self._path.read_text().strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)
            self._entries.append(BusEntry(
                timestamp=data["ts"], agent=data["agent"],
                event_type=data["type"], message=data["msg"],
                content_hash=data["hash"],
            ))
