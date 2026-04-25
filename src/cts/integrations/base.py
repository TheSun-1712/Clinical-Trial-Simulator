from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


class CachedAPIClient:
    def __init__(self, cache_dir: str = "artifacts/api_cache", offline: bool = True, requests_per_second: float = 5.0) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.offline = offline
        self.requests_per_second = max(0.1, requests_per_second)
        self._last_request_ts = 0.0

    def _cache_path(self, namespace: str, key: str) -> Path:
        safe_key = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in key)
        return self.cache_dir / namespace / f"{safe_key}.json"

    def _rate_limit(self) -> None:
        delay = 1.0 / self.requests_per_second
        now = time.time()
        elapsed = now - self._last_request_ts
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_request_ts = time.time()

    def get_json(self, url: str, namespace: str, key: str, fixture: dict[str, Any] | None = None, retries: int = 2) -> dict[str, Any]:
        path = self._cache_path(namespace, key)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        if self.offline:
            payload = fixture or {}
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return payload
        last_error: Exception | None = None
        for _ in range(max(1, retries + 1)):
            try:
                self._rate_limit()
                with urlopen(url, timeout=15) as response:  # noqa: S310
                    payload = json.loads(response.read().decode("utf-8"))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                return payload
            except (URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                time.sleep(0.25)
        if fixture is not None:
            return fixture
        raise RuntimeError(f"API request failed for {url}") from last_error

