from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import NamedTuple

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from lxml import html
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from ..extensions import db
from ..models import Artist, CachedAnalyticsMetadata, ChordLine, Song


class SongData(NamedTuple):
    title: str
    key: str
    url: str
    roman_numerals: list[str]


class HooktheoryScraper:
    BASE_URL = "https://www.hooktheory.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; MusicLibraryBot/1.0; +https://github.com/musiclib)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self, sleep_time: float = 2.0, use_selenium: bool = True):
        self.sleep_time = sleep_time
        self.use_selenium = use_selenium
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.driver = None
        
        if self.use_selenium:
            self._init_selenium()

    def _init_selenium(self) -> None:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument(f"user-agent={self.HEADERS['User-Agent']}")
        
        try:
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"Warning: Could not initialize Chrome driver: {e}")
            print("Falling back to requests (may not extract all data)")
            self.use_selenium = False
            self.driver = None

    def __del__(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

    def get_with_retry(self, url: str, max_retries: int = 3) -> requests.Response | None:
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    wait_time = (attempt + 1) * self.sleep_time * 2
                    print(f"  Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"  HTTP {response.status_code} for {url}")
                    return None
            except requests.RequestException as e:
                print(f"  Request error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(self.sleep_time)
        return None

    def search_taylor_swift_songs(self) -> list[str]:
        search_url = f"{self.BASE_URL}/theorytab/artists/t/taylor-swift"
        print(f"Searching for Taylor Swift songs at {search_url}")
        
        response = self.get_with_retry(search_url)
        if not response:
            print("Failed to fetch Taylor Swift artist page")
            return []
        
        soup = BeautifulSoup(response.text, "lxml")
        song_urls = []
        
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/theorytab/view/" in href and href.startswith("/"):
                full_url = f"{self.BASE_URL}{href}"
                if full_url not in song_urls:
                    song_urls.append(full_url)
        
        print(f"Found {len(song_urls)} song URLs")
        return song_urls

    def extract_song_data(self, url: str) -> SongData | None:
        if self.use_selenium and self.driver:
            return self._extract_with_selenium(url)
        else:
            return self._extract_with_requests(url)

    def _extract_with_selenium(self, url: str) -> SongData | None:
        try:
            self.driver.get(url)
            
            wait = WebDriverWait(self.driver, 10)
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            time.sleep(2)
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, "lxml")
            
            title = self._extract_title(soup, url)
            key = self._extract_key(soup)
            roman_numerals = self._extract_roman_numerals(soup)
            
            if not title:
                print(f"  Could not extract title from {url}")
                return None
            
            if not roman_numerals:
                print(f"  No Roman numerals found for {title}")
                return None
            
            return SongData(
                title=title,
                key=key,
                url=url,
                roman_numerals=roman_numerals
            )
        except Exception as e:
            print(f"  Selenium error: {e}")
            return None

    def _extract_with_requests(self, url: str) -> SongData | None:
        response = self.get_with_retry(url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, "lxml")
        
        title = self._extract_title(soup, url)
        key = self._extract_key(soup)
        roman_numerals = self._extract_roman_numerals(soup)
        
        if not title:
            print(f"  Could not extract title from {url}")
            return None
        
        if not roman_numerals:
            print(f"  No Roman numerals found for {title} (JavaScript may be required)")
            return None
        
        return SongData(
            title=title,
            key=key,
            url=url,
            roman_numerals=roman_numerals
        )

    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        title_elem = soup.find("h1")
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            title_text = re.sub(r"\s+by\s+.*$", "", title_text, flags=re.IGNORECASE)
            return title_text.strip()
        
        page_title = soup.find("title")
        if page_title:
            title_text = page_title.get_text(strip=True)
            title_text = re.sub(r"\s+by\s+.*$", "", title_text, flags=re.IGNORECASE)
            title_text = re.sub(r"\s+[-–—]\s+.*$", "", title_text)
            return title_text.strip()
        
        url_parts = url.rstrip("/").split("/")
        if url_parts:
            title_from_url = url_parts[-1].replace("-", " ").title()
            return title_from_url
        
        return ""

    def _extract_key(self, soup: BeautifulSoup) -> str:
        # Check using the specific XPath provided (handling variable tab-ID)
        try:
            tree = html.fromstring(str(soup))
            # The xpath provided: //*[@id="tab-951274"]/div/div[2]/div/div[2]/div[1]/div/div/div[1]/div/div[1]/span
            xpath_query = "//*[starts-with(@id, 'tab-')]/div/div[2]/div/div[2]/div[1]/div/div/div[1]/div/div[1]/span"
            elements = tree.xpath(xpath_query)
            if elements:
                key_text = elements[0].text_content()
                if key_text:
                    # Extract just the key part from the text to be safe
                    key_match = re.search(r"\b([A-G][#b]?\s*(?:major|minor|maj|min)?)\b", key_text, re.IGNORECASE)
                    if key_match:
                        return self._normalize_key(key_match.group(1))
        except Exception as e:
            print(f"Warning: Error using XPath for key extraction: {e}")

        # Check the specific tab-controls structure first (bug fix)
        tab_controls = soup.find("div", class_="tab-controls")
        if tab_controls:
            control_div = tab_controls.find("div", class_="div-control-with-label")
            if control_div:
                # Look for key text within this specific structure
                key_text = control_div.get_text(strip=True)
                if key_text:
                    # Extract just the key part from the text
                    key_match = re.search(r"\b([A-G][#b]?\s*(?:major|minor|maj|min)?)\b", key_text, re.IGNORECASE)
                    if key_match:
                        return self._normalize_key(key_match.group(1))
        
        key_indicators = [
            ("meta", {"name": "key"}),
            ("span", {"class": "key"}),
            ("div", {"class": "key"}),
        ]
        
        for tag, attrs in key_indicators:
            elem = soup.find(tag, attrs)
            if elem:
                if tag == "meta":
                    key = elem.get("content", "")
                else:
                    key = elem.get_text(strip=True)
                if key:
                    return self._normalize_key(key)
        
        title_elem = soup.find("h1")
        if title_elem:
            title_text = title_elem.get_text()
            key_match = re.search(r"\bin\s+([A-G][#b]?\s*(?:major|minor|maj|min)?)\b", title_text, re.IGNORECASE)
            if key_match:
                return self._normalize_key(key_match.group(1))
        
        breadcrumb = soup.find("div", class_="breadcrumb")
        if breadcrumb:
            text = breadcrumb.get_text()
            key_match = re.search(r"\b([A-G][#b]?\s*(?:major|minor|maj|min)?)\b", text, re.IGNORECASE)
            if key_match:
                return self._normalize_key(key_match.group(1))
        
        return ""

    def _normalize_key(self, key: str) -> str:
        key = key.strip()
        key = re.sub(r"\s*(major|maj)\s*", " major", key, flags=re.IGNORECASE)
        key = re.sub(r"\s*(minor|min)\s*", " minor", key, flags=re.IGNORECASE)
        key = re.sub(r"\s+", " ", key).strip()
        
        parts = key.split()
        if len(parts) >= 2:
            note = parts[0]
            quality = parts[1].lower()
            if quality in ("major", "maj"):
                return f"{note} major"
            elif quality in ("minor", "min"):
                return f"{note} minor"
        
        return key

    def _extract_roman_numerals(self, soup: BeautifulSoup) -> list[str]:
        roman_numerals: list[str] = []

        def extract_concatenated_times_text(container: Tag) -> str:
            parts: list[str] = []
            for tspan in container.find_all("tspan", class_="times"):
                text = tspan.get_text(strip=True)
                if text:
                    parts.append(text)

            numeral = "".join(parts).replace("\u200b", "").strip()
            if numeral and self._is_valid_roman_numeral(numeral):
                return numeral
            return ""

        chord_label_groups = soup.find_all(
            "g",
            attrs={"data-type": re.compile(r"^chord-label-rel-")},
        )
        if chord_label_groups:
            for group in chord_label_groups:
                numeral = extract_concatenated_times_text(group)
                if numeral:
                    roman_numerals.append(numeral)
            if roman_numerals:
                return roman_numerals

        for text_elem in soup.find_all("text"):
            numeral = extract_concatenated_times_text(text_elem)
            if numeral:
                roman_numerals.append(numeral)

        if roman_numerals:
            return roman_numerals

        # Last-resort fallback: treat individual tspans as numerals.
        for tspan in soup.find_all("tspan", class_="times"):
            numeral = tspan.get_text(strip=True)
            if numeral and self._is_valid_roman_numeral(numeral):
                roman_numerals.append(numeral)

        return roman_numerals

    def _is_valid_roman_numeral(self, text: str) -> bool:
        text = text.strip()
        if not text:
            return False
        
        pattern = r"^[#b♯♭]?[IiVv]+[°ø+]?(\d+)?(/[IiVv]+)?$"
        return bool(re.match(pattern, text))

    def scrape_taylor_swift(
        self,
        limit: int | None = None,
        force: bool = False
    ) -> dict[str, int]:
        print("Starting Hooktheory scraper for Taylor Swift...")
        
        if self.use_selenium and not self.driver:
            print("Warning: Selenium not available, some data may not be extracted")
        
        artist = Artist.query.filter_by(name="Taylor Swift").first()
        if not artist:
            artist = Artist(name="Taylor Swift")
            db.session.add(artist)
            db.session.commit()
            print(f"Created artist: Taylor Swift (ID: {artist.id})")
        else:
            print(f"Found existing artist: Taylor Swift (ID: {artist.id})")
        
        song_urls = self.search_taylor_swift_songs()
        if limit:
            song_urls = song_urls[:limit]
        
        stats = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}
        
        for idx, url in enumerate(song_urls, 1):
            print(f"\n[{idx}/{len(song_urls)}] Processing {url}")
            
            existing_song = Song.query.filter_by(
                source="hooktheory",
                source_url=url
            ).first()
            
            if existing_song and not force:
                print(f"  Skipping (already exists): {existing_song.title}")
                stats["skipped"] += 1
                time.sleep(self.sleep_time / 2)
                continue
            
            song_data = self.extract_song_data(url)
            if not song_data:
                stats["errors"] += 1
                time.sleep(self.sleep_time)
                continue
            
            print(f"  Title: {song_data.title}")
            print(f"  Key: {song_data.key or 'Unknown'}")
            print(f"  Roman numerals: {len(song_data.roman_numerals)}")
            
            if existing_song:
                song = existing_song
                song.key = song_data.key or song.key
                song.last_scraped_at = datetime.now(timezone.utc)
                
                ChordLine.query.filter_by(song_id=song.id).delete()
                
                print(f"  Updated existing song (ID: {song.id})")
                stats["updated"] += 1
            else:
                song = Song(
                    artist_id=artist.id,
                    title=song_data.title,
                    key=song_data.key or None,
                    source="hooktheory",
                    source_url=url,
                    tab_type="roman_numerals",
                    last_scraped_at=datetime.now(timezone.utc)
                )
                db.session.add(song)
                db.session.flush()
                
                print(f"  Created new song (ID: {song.id})")
                stats["created"] += 1

            CachedAnalyticsMetadata.query.filter_by(
                subject_type="song",
                subject_id=song.id,
                metric="chord_analytics.song",
            ).delete()
            CachedAnalyticsMetadata.query.filter_by(
                subject_type="global",
                subject_id=0,
                metric="chord_analytics.overall",
            ).delete()
            if song.album_id is not None:
                CachedAnalyticsMetadata.query.filter_by(
                    subject_type="album",
                    subject_id=song.album_id,
                    metric="chord_analytics.album",
                ).delete()

            for line_num, numeral in enumerate(song_data.roman_numerals, 1):
                chord_line = ChordLine(
                    song_id=song.id,
                    line_number=line_num,
                    content=numeral
                )
                db.session.add(chord_line)
            
            db.session.commit()
            
            time.sleep(self.sleep_time)
        
        print("\n" + "=" * 60)
        print("Scraping complete!")
        print(f"  Created: {stats['created']} songs")
        print(f"  Updated: {stats['updated']} songs")
        print(f"  Skipped: {stats['skipped']} songs")
        print(f"  Errors: {stats['errors']} songs")
        print("=" * 60)
        
        return stats
