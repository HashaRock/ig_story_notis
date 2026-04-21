import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path


class StateManager:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._seen: set[int] = set()
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            entries = json.loads(self._path.read_text())
            cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
            for entry in entries:
                seen_at = datetime.fromisoformat(entry["seen_at"])
                if seen_at > cutoff:
                    self._seen.add(entry["id"])
        except (json.JSONDecodeError, KeyError):
            # corrupt state file — start fresh
            self._seen = set()

    def is_seen(self, story_id: int) -> bool:
        return story_id in self._seen

    def mark_seen(self, story_id: int) -> None:
        self._seen.add(story_id)
        self._persist()

    def _persist(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        # reload existing entries to preserve seen_at timestamps
        existing: dict[int, str] = {}
        if self._path.exists():
            try:
                for entry in json.loads(self._path.read_text()):
                    existing[entry["id"]] = entry["seen_at"]
            except (json.JSONDecodeError, KeyError):
                pass

        entries = [
            {"id": sid, "seen_at": existing.get(sid, now)}
            for sid in self._seen
        ]

        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(entries, indent=2))
        os.replace(tmp, self._path)
