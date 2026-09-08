"""YC public-company-page snapshot adapter.

This adapter intentionally saves raw, dated public evidence before any LLM sees it.
It does not try to infer missing founder, traction, or market facts.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import ssl
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol


class SourceError(RuntimeError):
    """Raised when a public-source snapshot cannot be collected safely."""


class HttpGet(Protocol):
    def get(self, url: str) -> str: ...


class UrllibHttpGet:
    def get(self, url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "SignalDesk research snapshot/0.1"},
        )
        context = _ssl_context()
        with urllib.request.urlopen(request, timeout=30, context=context) as response:
            return response.read().decode("utf-8", errors="replace")


@dataclass(frozen=True)
class YCPageSnapshot:
    source_url: str
    title: str
    description: str
    fetched_at: str
    content_sha256: str


def collect_snapshot(
    seed_path: Path,
    output_path: Path,
    http_get: HttpGet | None = None,
    now: datetime | None = None,
) -> list[YCPageSnapshot]:
    """Fetch each allow-listed YC page and persist only public page metadata."""
    seed = json.loads(seed_path.read_text())
    urls = seed["company_urls"]
    if not 10 <= len(urls) <= 20:
        raise SourceError("A source snapshot must contain 10-20 company URLs.")
    if any(not url.startswith("https://www.ycombinator.com/companies/") for url in urls):
        raise SourceError("YC source adapter accepts only YC company profile URLs.")

    client = http_get or UrllibHttpGet()
    timestamp = (now or datetime.now(UTC)).replace(microsecond=0).isoformat()
    snapshots = [_snapshot_page(url, client, timestamp) for url in urls]
    payload = {
        "source": "Y Combinator public company pages",
        "fetched_at": timestamp,
        "seed_file": str(seed_path),
        "pages": [asdict(snapshot) for snapshot in snapshots],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n")
    return snapshots


def _snapshot_page(url: str, http_get: HttpGet, timestamp: str) -> YCPageSnapshot:
    page = http_get.get(url)
    title = _meta_value(page, "og:title") or _title(page)
    description = _meta_value(page, "og:description") or _meta_value(page, "description")
    if not title or not description:
        raise SourceError(f"{url}: expected title and description metadata were not found.")
    return YCPageSnapshot(
        source_url=url,
        title=title,
        description=description,
        fetched_at=timestamp,
        content_sha256=hashlib.sha256(page.encode()).hexdigest(),
    )


def _meta_value(page: str, property_name: str) -> str | None:
    for tag in re.findall(r"<meta\b[^>]*>", page, re.IGNORECASE):
        attributes = {
            name.lower(): html.unescape(value)
            for name, value in re.findall(
                r'''([\w:-]+)\s*=\s*["']([^"']*)["']''',
                tag,
                re.IGNORECASE,
            )
        }
        if attributes.get("property") == property_name or attributes.get("name") == property_name:
            return attributes.get("content", "").strip() or None
    return None


def _title(page: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", page, re.IGNORECASE | re.DOTALL)
    return html.unescape(re.sub(r"\s+", " ", match.group(1))).strip() if match else None


def _ssl_context() -> ssl.SSLContext:
    """Use the OS trust store, with an opt-in CA-bundle override for local Python setups."""
    ca_bundle = os.getenv("SIGNALDESK_CA_BUNDLE")
    return ssl.create_default_context(cafile=ca_bundle) if ca_bundle else ssl.create_default_context()
