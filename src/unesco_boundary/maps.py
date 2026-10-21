# SPDX-License-Identifier: Apache-2.0
# Adapted from cloudcollection/UNESCO_Map_SC; see NOTICE.
"""Download official map documents without treating a download as a boundary."""

import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .evidence import sha256, write_json


def map_links(html, page_url):
    links = {}
    for tag in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        url = urljoin(page_url, tag["href"]).split("#")[0]
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.hostname == "whc.unesco.org" and re.fullmatch(r"/(?:en/)?document/\d+/?", parsed.path):
            links[url] = tag.get_text(" ", strip=True)
    return sorted(links.items())


def document_extension(body):
    if body.startswith(b"%PDF-"):
        return ".pdf"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if body.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if body.startswith((b"II*\x00", b"MM\x00*")):
        return ".tif"
    if body.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    raise ValueError("Response is not a recognized PDF/image; inspect archived bytes (possibly HTML)")


def download_maps(pid, run, client):
    if pid <= 0:
        raise ValueError("UNESCO ID must be positive")
    page_url = f"https://whc.unesco.org/en/list/{pid}/maps/"
    body, meta = client.fetch(page_url)
    if meta["status_code"] != 200:
        raise ValueError(f"Map page returned HTTP {meta['status_code']}")
    links = map_links(body.decode("utf-8", errors="replace"), page_url)
    records = []
    folder = Path(run) / "maps" / str(pid)
    folder.mkdir(parents=True, exist_ok=True)
    for url, title in links:
        record = {"url": url, "title": title, "maps_page": page_url}
        try:
            content, response = client.fetch(url)
            if response["status_code"] != 200:
                raise ValueError(f"HTTP {response['status_code']}")
            ext = document_extension(content)
            doc_id = urlparse(url).path.strip("/").split("/")[-1]
            target = folder / (doc_id + ext)
            target.write_bytes(content)
            record.update({"status": "downloaded_document", "file": f"maps/{pid}/{target.name}",
                           "sha256": sha256(content), "bytes": len(content), "retrieved_at": response["retrieved_at"]})
        except Exception as exc:
            record.update({"status": "document_error", "error": str(exc)})
        records.append(record)
    manifest = {"unesco_id": pid, "maps_page": page_url, "status": "documents_found" if links else "no_document_links_detected",
                "note": "Document discovery is not proof of map completeness or property geometry. Check the official page if no links are detected.", "documents": records}
    write_json(folder / "manifest.json", manifest)
    return manifest
