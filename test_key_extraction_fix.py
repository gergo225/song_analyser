#!/usr/bin/env python3
"""Test script to verify the key extraction bug fix."""

from bs4 import BeautifulSoup
from musiclib.scrapers.hooktheory import HooktheoryScraper


def test_key_extraction_from_tab_controls():
    """Test that key is correctly extracted from the tab-controls structure."""
    scraper = HooktheoryScraper(use_selenium=False)
    
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
    
    print("\n✅ All key extraction tests passed!")


if __name__ == "__main__":
    test_key_extraction_from_tab_controls()