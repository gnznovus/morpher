from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from morpher.targets import normalize_target_url


@dataclass(frozen=True)
class ConnectionRecord:
    site_url: str
    site_name: str
    ref_no: str
    plugin_version: str
    wordpress_version: str
    paired_at: float
    credential_key: str

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ConnectionRecord":
        site_url = normalize_target_url(str(payload.get("site_url") or ""))
        return cls(
            site_url=site_url,
            site_name=str(payload.get("site_name") or "WordPress").strip() or "WordPress",
            ref_no=str(payload.get("ref_no") or "").strip().upper(),
            plugin_version=str(payload.get("plugin_version") or "").strip(),
            wordpress_version=str(payload.get("wordpress_version") or "").strip(),
            paired_at=float(payload.get("paired_at") or 0),
            credential_key=str(payload.get("credential_key") or site_url).strip() or site_url,
        )


class ConnectionStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path.home() / ".morpher" / "connections.json"

    def all(self) -> tuple[ConnectionRecord, ...]:
        payload = self._read()
        items = payload.get("connections") or []
        if not isinstance(items, list):
            return ()

        records: list[ConnectionRecord] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                records.append(ConnectionRecord.from_dict(item))
            except (TypeError, ValueError):
                continue
        return tuple(sorted(records, key=lambda record: record.paired_at, reverse=True))

    def get(self, site_url: str) -> ConnectionRecord | None:
        target = normalize_target_url(site_url)
        return next((record for record in self.all() if record.site_url == target), None)

    def upsert(self, record: ConnectionRecord) -> ConnectionRecord:
        records = [item for item in self.all() if item.site_url != record.site_url]
        records.append(record)
        self._write(records)
        return record

    def delete(self, site_url: str) -> None:
        target = normalize_target_url(site_url)
        records = [item for item in self.all() if item.site_url != target]
        self._write(records)

    def _read(self) -> dict[str, object]:
        if not self.path.exists():
            return {"version": 1, "connections": []}
        try:
            decoded = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "connections": []}
        return decoded if isinstance(decoded, dict) else {"version": 1, "connections": []}

    def _write(self, records: list[ConnectionRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "connections": [asdict(record) for record in sorted(records, key=lambda item: item.site_url)],
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)
