from __future__ import annotations

import html as html_lib
import json
import re
import time
from dataclasses import dataclass
from typing import Iterable, Iterator

import requests
from bs4 import BeautifulSoup


@dataclass(frozen=True, slots=True)
class UltimateGuitarTabSummary:
    song_title: str
    tab_url: str
    tab_type: str
    tab_id: int | None = None
    song_id: int | None = None


@dataclass(frozen=True, slots=True)
class UltimateGuitarTab:
    song_title: str
    artist_name: str
    tab_url: str
    tab_type: str
    raw_content: str
    lines: list[str]
    normalized_chords: list[str]


_CH_TAG_RE = re.compile(r"\[ch\]([^\[]*?)\[/ch\]", re.IGNORECASE)
_TAB_TAG_RE = re.compile(r"\[/?tab\]", re.IGNORECASE)


class UltimateGuitarScraper:
    def __init__(
        self,
        *,
        sleep_seconds: float = 1.0,
        max_retries: int = 2,
        timeout_seconds: float = 20.0,
        session: requests.Session | None = None,
    ) -> None:
        self.sleep_seconds = max(sleep_seconds, 0.0)
        self.max_retries = max(max_retries, 0)
        self.timeout_seconds = timeout_seconds

        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "musiclib-ultimate-guitar-scraper/1.0",
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
            }
        )

    def iter_taylor_swift_chords(
        self,
        *,
        max_pages: int | None = None,
        limit: int | None = None,
    ) -> Iterator[UltimateGuitarTabSummary]:
        yield from self.iter_artist_tabs(
            artist_path="/artist/taylor_swift_16027",
            tab_filter="chords",
            max_pages=max_pages,
            limit=limit,
        )

    def iter_artist_tabs(
        self,
        *,
        artist_path: str,
        tab_filter: str = "chords",
        max_pages: int | None = None,
        limit: int | None = None,
    ) -> Iterator[UltimateGuitarTabSummary]:
        page = 1
        seen = 0

        while True:
            if max_pages is not None and page > max_pages:
                return

            url = (
                f"https://www.ultimate-guitar.com{artist_path}"
                f"?filter={tab_filter}&page={page}"
            )
            html_text = self._get(url)
            payload = self._parse_js_store(html_text)
            page_data = payload.get("store", {}).get("page", {}).get("data", {})

            tabs = self._extract_tab_summaries(page_data)
            for tab in tabs:
                yield tab
                seen += 1
                if limit is not None and seen >= limit:
                    return

            pagination = page_data.get("pagination") or {}
            pages = pagination.get("pages")
            if not pages or pagination.get("current") is None:
                return

            last_page = max(p.get("page", 0) for p in pages if isinstance(p, dict))
            if page >= last_page:
                return

            page += 1

    def fetch_tab(self, tab_url: str) -> UltimateGuitarTab:
        html_text = self._get(tab_url)
        payload = self._parse_js_store(html_text)

        page_data = payload.get("store", {}).get("page", {}).get("data", {})
        tab_meta = page_data.get("tab") or {}
        tab_view = page_data.get("tab_view") or {}
        wiki_tab = tab_view.get("wiki_tab") or {}

        raw = wiki_tab.get("content")
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("UltimateGuitar tab missing wiki_tab content")

        song_title = tab_meta.get("song_name") or ""
        artist_name = tab_meta.get("artist_name") or ""
        tab_type = tab_meta.get("type_name") or tab_meta.get("type") or ""
        url = tab_meta.get("tab_url") or tab_url

        lines = parse_ug_wiki_tab_to_lines(raw)
        chords = extract_normalized_chords(raw)

        return UltimateGuitarTab(
            song_title=song_title,
            artist_name=artist_name,
            tab_url=url,
            tab_type=tab_type,
            raw_content=raw,
            lines=lines,
            normalized_chords=chords,
        )

    def _get(self, url: str) -> str:
        last_exc: Exception | None = None

        for attempt in range(self.max_retries + 1):
            if attempt:
                time.sleep(min(2**attempt, 10))

            try:
                resp = self.session.get(url, timeout=self.timeout_seconds)

                if (
                    resp.status_code in {429, 500, 502, 503, 504}
                    and attempt < self.max_retries
                ):
                    last_exc = RuntimeError(f"HTTP {resp.status_code} for {url}")
                    continue

                resp.raise_for_status()

                if self.sleep_seconds:
                    time.sleep(self.sleep_seconds)

                return resp.text
            except Exception as exc:  # noqa: BLE001
                last_exc = exc

        raise last_exc or RuntimeError(f"Failed to fetch {url}")

    def _parse_js_store(self, html_text: str) -> dict:
        soup = BeautifulSoup(html_text, "html.parser")
        store_el = soup.select_one("div.js-store[data-content]")
        if store_el is None:
            raise ValueError("Unable to locate UltimateGuitar js-store payload")

        data = store_el.get("data-content")
        if not isinstance(data, str) or not data:
            raise ValueError("UltimateGuitar js-store payload missing data-content")

        decoded = html_lib.unescape(data)
        return json.loads(decoded)

    def _extract_tab_summaries(self, page_data: dict) -> list[UltimateGuitarTabSummary]:
        combined: list[dict] = []
        for key in ("feat_tabs", "other_tabs"):
            raw = page_data.get(key)
            if isinstance(raw, list):
                combined.extend([t for t in raw if isinstance(t, dict)])

        tabs: dict[int, UltimateGuitarTabSummary] = {}

        for t in combined:
            tab_url = t.get("tab_url")
            song_title = t.get("song_name")
            tab_type = t.get("type_name") or t.get("type")

            if not tab_url or not song_title:
                continue

            tab_id = t.get("id") if isinstance(t.get("id"), int) else None
            song_id = t.get("song_id") if isinstance(t.get("song_id"), int) else None

            if tab_id is None:
                key = hash((song_title, tab_url))
                tabs[key] = UltimateGuitarTabSummary(
                    song_title=song_title,
                    tab_url=tab_url,
                    tab_type=tab_type or "",
                    tab_id=None,
                    song_id=song_id,
                )
            else:
                tabs[tab_id] = UltimateGuitarTabSummary(
                    song_title=song_title,
                    tab_url=tab_url,
                    tab_type=tab_type or "",
                    tab_id=tab_id,
                    song_id=song_id,
                )

        return list(tabs.values())


def parse_ug_wiki_tab_to_lines(raw_content: str) -> list[str]:
    soup = BeautifulSoup(raw_content, "html.parser")
    chord_spans = soup.find_all("span", attrs={"data-name": True})
    
    if chord_spans:
        for br in soup.find_all("br"):
            br.replace_with("\n")
        
        lines: list[str] = []
        current_line_chords: list[str] = []
        
        def extract_chords_recursive(element):
            if hasattr(element, "children"):
                for child in element.children:
                    if child.name == "span" and child.get("data-name"):
                        chord = child.get("data-name", "").strip()
                        if chord:
                            current_line_chords.append(chord)
                    elif isinstance(child, str):
                        if "\n" in child:
                            for part in child.split("\n"):
                                if current_line_chords:
                                    lines.append(" ".join(current_line_chords))
                                    current_line_chords.clear()
                    else:
                        extract_chords_recursive(child)
        
        extract_chords_recursive(soup)
        
        if current_line_chords:
            lines.append(" ".join(current_line_chords))
        
        return [line for line in lines if line.strip()]
    
    lines: list[str] = []
    for line in raw_content.splitlines():
        cleaned = _TAB_TAG_RE.sub("", line)
        cleaned = _CH_TAG_RE.sub(lambda m: m.group(1), cleaned)
        cleaned = cleaned.strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def extract_normalized_chords(raw_content: str) -> list[str]:
    soup = BeautifulSoup(raw_content, "html.parser")
    chord_spans = soup.find_all("span", attrs={"data-name": True})
    
    if chord_spans:
        chords = [
            _normalize_chord_symbol(span.get("data-name", ""))
            for span in chord_spans
        ]
        unique = sorted({c for c in chords if c})
        return unique
    
    chords = [
        _normalize_chord_symbol(m.group(1))
        for m in _CH_TAG_RE.finditer(raw_content)
    ]
    unique = sorted({c for c in chords if c})
    return unique


_NOTE_RE = re.compile(r"^\s*([A-Ga-g])\s*([#b♯♭]?)\s*(.*)$")


def _normalize_chord_symbol(symbol: str) -> str:
    s = symbol.strip()
    if not s:
        return ""

    s = s.replace("♯", "#").replace("♭", "b")
    s = s.strip("()[]{}")

    if s.upper() in {"NC", "N.C."}:
        return "N.C."

    if "/" in s:
        main, bass = s.split("/", 1)
        main_norm = _normalize_chord_symbol(main)
        bass_norm = _normalize_bass_note(bass)
        if main_norm and bass_norm:
            return f"{main_norm}/{bass_norm}"
        return main_norm or bass_norm

    m = _NOTE_RE.match(s)
    if not m:
        return s

    root, accidental, rest = m.groups()
    root = root.upper()
    accidental = accidental.replace("♯", "#").replace("♭", "b")

    rest = rest.strip()
    rest_lower = rest.lower()

    if rest_lower.startswith("minor"):
        rest = "m" + rest[5:]
    elif rest_lower.startswith("min"):
        rest = "m" + rest[3:]
    elif rest.startswith("-"):
        rest = "m" + rest[1:]
    elif rest.startswith("M") and (len(rest) == 1 or rest[1].isdigit()):
        rest = "maj" + rest[1:]

    rest = rest.replace(" ", "")
    return f"{root}{accidental}{rest}"


def _normalize_bass_note(note: str) -> str:
    m = _NOTE_RE.match(note)
    if not m:
        return note.strip()

    root, accidental, _rest = m.groups()
    root = root.upper()
    accidental = accidental.replace("♯", "#").replace("♭", "b")
    return f"{root}{accidental}"


def iter_normalized_chords_by_line(lines: Iterable[str]) -> Iterator[list[str]]:
    for line in lines:
        chords = []
        for token in re.split(r"\s+", line):
            if not token:
                continue
            norm = _normalize_chord_symbol(token)
            if norm != token or _NOTE_RE.match(token):
                chords.append(norm)
        yield chords
