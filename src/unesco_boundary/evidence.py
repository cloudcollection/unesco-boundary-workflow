"""Archive response bytes before interpretation; replay without network access."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ArchiveClient:
    def __init__(self, run, user_agent=None, offline=False, delay=1.1):
        if not offline and (not user_agent or not any(x in user_agent for x in ("@", "https://", "http://"))):
            raise ValueError("Set --user-agent with your own contact email or project URL")
        self.root = Path(run) / "raw"
        self.root.mkdir(parents=True, exist_ok=True)
        self.offline = offline
        self.delay = max(1.1, delay)
        self.last_request = 0.0
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent or "unesco-boundary-workflow/offline"

    def fetch(self, url):
        key = sha256(url.encode("utf-8"))
        body_path = self.root / (key + ".body")
        meta_path = self.root / (key + ".json")
        if body_path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            body = body_path.read_bytes()
            if meta["sha256"] != sha256(body) or meta["url"] != url:
                raise ValueError("Archived response failed integrity check: " + key)
            return body, meta
        if self.offline:
            raise FileNotFoundError("Offline archive miss: " + url)
        for attempt in range(3):
            time.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                response = self.session.get(url, timeout=(15, 120))
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
                continue
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                retry_after = response.headers.get("Retry-After", "")
                time.sleep(min(60, float(retry_after)) if retry_after.isdigit() else 2 ** attempt)
                continue
            body = response.content
            meta = {"url": url, "final_url": response.url, "status_code": response.status_code,
                    "content_type": response.headers.get("Content-Type", ""),
                    "retrieved_at": utc_now(), "sha256": sha256(body), "bytes": len(body)}
            # Store unsuccessful responses too, so HTTP failures remain inspectable.
            body_path.write_bytes(body)
            write_json(meta_path, meta)
            return body, meta
        raise RuntimeError("Request attempts exhausted")

    def json(self, url):
        body, meta = self.fetch(url)
        if meta["status_code"] != 200:
            raise ValueError(f"HTTP {meta['status_code']}: {url}")
        data = json.loads(body.decode("utf-8-sig"))
        if isinstance(data, dict) and data.get("error"):
            raise ValueError("Remote API error: " + json.dumps(data["error"]))
        return data
