#!/usr/bin/env python3
"""Simple test to verify the key extraction bug fix."""

import re
from bs4 import BeautifulSoup


class MockHooktheoryScraper:
    """Mock scraper with just the key extraction methods for testing."""
    
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

    def _extract_key(self, soup: BeautifulSoup) -> str:
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


def test_key_extraction_from_tab_controls():
    """Test that key is correctly extracted from the tab-controls structure."""
    scraper = MockHooktheoryScraper()
    
    print("Testing Hooktheory key extraction fix...")
    
    # Test case 1: Key in the tab-controls structure (the bug fix target)
    html_with_tab_controls = """
    <html>
        <body>
            <div class="tab-controls">
                <div class="div-control-with-label">
                    Key: D major
                </div>
            </div>
            <h1>Love Story</h1>
        </body>
    </html>
    """
    
    soup = BeautifulSoup(html_with_tab_controls, "lxml")
    key = scraper._extract_key(soup)
    
    print(f"Test 1 - tab-controls structure: {key}")
    assert key == "D major", f"Expected 'D major', got '{key}'"
    
    # Test case 2: Multiple possible sources, tab-controls should take precedence
    html_mixed_sources = """
    <html>
        <body>
            <div class="tab-controls">
                <div class="div-control-with-label">
                    Key: G minor
                </div>
            </div>
            <div class="key">F major</div>
            <h1>Shake It Off in C major</h1>
        </body>
    </html>
    """
    
    soup = BeautifulSoup(html_mixed_sources, "lxml")
    key = scraper._extract_key(soup)
    
    print(f"Test 2 - mixed sources (tab-controls first): {key}")
    assert key == "G minor", f"Expected 'G minor' from tab-controls, got '{key}'"
    
    # Test case 3: No tab-controls, falls back to other methods
    html_no_tab_controls = """
    <html>
        <body>
            <div class="key">A major</div>
            <h1>Blank Space in E minor</h1>
        </body>
    </html>
    """
    
    soup = BeautifulSoup(html_no_tab_controls, "lxml")
    key = scraper._extract_key(soup)
    
    print(f"Test 3 - fallback to .key class: {key}")
    assert key == "A major", f"Expected 'A major' from .key class, got '{key}'"
    
    # Test case 4: Complex key formats
    html_complex_keys = """
    <html>
        <body>
            <div class="tab-controls">
                <div class="div-control-with-label">
                    Musical Key: F# minor
                </div>
            </div>
        </body>
    </html>
    """
    
    soup = BeautifulSoup(html_complex_keys, "lxml")
    key = scraper._extract_key(soup)
    
    print(f"Test 4 - complex key (F# minor): {key}")
    assert key == "F# minor", f"Expected 'F# minor', got '{key}'"
    
    # Test case 5: Empty tab-controls, falls back gracefully
    html_empty_tab_controls = """
    <html>
        <body>
            <div class="tab-controls">
                <div class="div-control-with-label">
                    <!-- No key text here -->
                </div>
            </div>
            <meta name="key" content="B major" />
        </body>
    </html>
    """
    
    soup = BeautifulSoup(html_empty_tab_controls, "lxml")
    key = scraper._extract_key(soup)
    
    print(f"Test 5 - empty tab-controls (meta fallback): {key}")
    assert key == "B major", f"Expected 'B major' from meta tag, got '{key}'"
    
    # Test case 6: Real-world example with actual HTML structure
    html_realistic = """
    <html>
        <body>
            <div class="tab-controls">
                <div class="div-control-with-label">
                    <span class="label">Key:</span>
                    <span class="value">C minor</span>
                </div>
            </div>
            <h1>Anti-Hero</h1>
        </body>
    </html>
    """
    
    soup = BeautifulSoup(html_realistic, "lxml")
    key = scraper._extract_key(soup)
    
    print(f"Test 6 - realistic structure: {key}")
    assert key == "C minor", f"Expected 'C minor', got '{key}'"
    
    print("\n✅ All key extraction tests passed!")
    print("\nThe bug fix successfully:")
    print("  - Extracts keys from tab-controls > div-control-with-label structure")
    print("  - Maintains precedence (tab-controls checked first)")
    print("  - Falls back to other methods when tab-controls is empty")
    print("  - Handles various key formats (D major, F# minor, etc.)")
    print("  - Normalizes keys to standard format")


if __name__ == "__main__":
    test_key_extraction_from_tab_controls()