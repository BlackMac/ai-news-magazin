#!/usr/bin/env python3
"""
Validates Die Inferenz HTML files against the Readability-First design system.
Usage: python3 validate-design.py [file.html ...] or without args to check all.
"""

import sys
import re
import glob
import os
from html.parser import HTMLParser

# ─── Configuration ───────────────────────────────────────────────────────────

REQUIRED_FONTS = ["Source Serif 4", "Inter"]
BANNED_FONTS = ["Playfair Display", "Old Standard TT", "Libre Baskerville", "IM Fell English"]

REQUIRED_CSS_VARS_LIGHT = ["--bg", "--bg-surface", "--text-primary", "--text-body",
                           "--text-muted", "--accent", "--link", "--border"]
BANNED_CSS_VARS = ["--paper", "--ink", "--ink-light", "--ink-faded"]

MIN_FONT_SIZE_REM = 0.7

# ─── HTML Parser ─────────────────────────────────────────────────────────────

class DesignValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors = []
        self.warnings = []
        self.info = []

        # State
        self.html_lang = None
        self.has_skip_link = False
        self.has_main = False
        self.has_nav = False
        self.nav_labels = []
        self.has_theme_toggle = False
        self.has_sticky_header = False
        self.heading_levels = []
        self.article_ids = []
        self.article_labelledby = []
        self.time_elements = []
        self.time_has_datetime = []
        self.inline_style_count = 0
        self.inline_style_examples = []
        self.external_links = []
        self.external_links_have_rel = []
        self.tool_card_count = 0
        self.in_tool_grid = False
        self.tool_grid_depth = 0
        self.css_content = ""
        self.in_style = False
        self.current_tag = None
        self.sr_only_sources = 0
        self.sources_sections = 0
        self.focus_visible = False
        self.has_reduced_motion = False
        self.has_dark_mode_toggle = False
        self.has_dark_mode_css = False
        self.has_print_styles = False
        self.has_scroll_spy = False
        self.img_sepia_count = 0
        self.has_hyphenation = False
        self.has_max_width_68ch = False
        self.script_content = ""
        self.in_script = False
        self.yt_card_count = 0
        self.in_yt_grid = False
        self.yt_grid_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self.current_tag = tag

        if tag == "html":
            self.html_lang = attrs_dict.get("lang")

        if tag == "style":
            self.in_style = True

        if tag == "script":
            self.in_script = True

        if tag == "a":
            href = attrs_dict.get("href", "")
            cls = attrs_dict.get("class", "")
            if "skip-link" in cls or "skip" in cls:
                self.has_skip_link = True
            if href.startswith("http"):
                self.external_links.append(href)
                rel = attrs_dict.get("rel", "")
                self.external_links_have_rel.append("noopener" in rel)

        if tag == "main":
            self.has_main = True

        if tag == "nav":
            self.has_nav = True
            label = attrs_dict.get("aria-label", "")
            if label:
                self.nav_labels.append(label)

        if tag == "button":
            cls = attrs_dict.get("class", "")
            if "theme-toggle" in cls or "theme" in cls:
                self.has_theme_toggle = True

        if tag == "header":
            cls = attrs_dict.get("class", "")
            if "site-header" in cls:
                self.has_sticky_header = True

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            self.heading_levels.append(level)

        if tag == "article":
            aid = attrs_dict.get("id", "")
            if aid:
                self.article_ids.append(aid)
            labelledby = attrs_dict.get("aria-labelledby", "")
            if labelledby:
                self.article_labelledby.append(labelledby)

        if tag == "time":
            self.time_elements.append(True)
            self.time_has_datetime.append("datetime" in attrs_dict)

        if tag == "div" or tag == "section":
            cls = attrs_dict.get("class", "")
            if "tool-grid" in cls:
                self.in_tool_grid = True
                self.tool_grid_depth = 0
            if "yt-grid" in cls:
                self.in_yt_grid = True
                self.yt_grid_depth = 0

        if self.in_tool_grid and tag == "div":
            self.tool_grid_depth += 1
            cls = attrs_dict.get("class", "")
            # Only count direct children with "tool-card" as a whole class
            if cls and "tool-card" in cls.split():
                self.tool_card_count += 1

        if self.in_yt_grid and tag == "div":
            self.yt_grid_depth += 1
            cls = attrs_dict.get("class", "")
            if cls and "yt-card" in cls.split():
                self.yt_card_count += 1

        if tag == "img":
            style = attrs_dict.get("style", "")
            if "sepia" in style:
                self.img_sepia_count += 1

        # Count inline styles
        if "style" in attrs_dict and tag not in ("html",):
            self.inline_style_count += 1
            if len(self.inline_style_examples) < 3:
                self.inline_style_examples.append(f"<{tag} style=\"{attrs_dict['style'][:60]}...\">")

        if tag == "h3":
            cls = attrs_dict.get("class", "")
            if "sr-only" in cls or "visually-hidden" in cls:
                self.sr_only_sources += 1

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
        if tag == "script":
            self.in_script = False
        if tag == "div":
            if self.in_tool_grid:
                self.tool_grid_depth -= 1
                if self.tool_grid_depth <= 0:
                    self.in_tool_grid = False
            if self.in_yt_grid:
                self.yt_grid_depth -= 1
                if self.yt_grid_depth <= 0:
                    self.in_yt_grid = False

    def handle_data(self, data):
        if self.in_style:
            self.css_content += data
        if self.in_script:
            self.script_content += data
        if self.current_tag in ("div",) and "Quellen" in data:
            self.sources_sections += 1

    def validate(self, filename, content):
        """Run all validations and return results."""
        self.feed(content)
        is_homepage = "index.html" in filename
        is_reportage = "reportagen/" in filename
        is_edition = "editions/" in filename and not is_reportage
        basename = os.path.basename(filename)

        # ── lang="de" ──
        if self.html_lang != "de":
            self.errors.append(f'lang="de" fehlt auf <html> (gefunden: "{self.html_lang}")')

        # ── Fonts ──
        for font in REQUIRED_FONTS:
            if font not in self.css_content and font not in content:
                self.errors.append(f'Pflicht-Font "{font}" nicht gefunden')

        for font in BANNED_FONTS:
            if font in self.css_content:
                self.errors.append(f'Alter Font "{font}" noch in CSS vorhanden')

        # ── CSS Variables ──
        for var in REQUIRED_CSS_VARS_LIGHT:
            if var + ":" not in self.css_content and var + " :" not in self.css_content:
                # Check with regex for more flexibility
                if not re.search(re.escape(var) + r'\s*:', self.css_content):
                    self.errors.append(f'CSS-Variable "{var}" fehlt')

        for var in BANNED_CSS_VARS:
            if re.search(re.escape(var) + r'\s*:', self.css_content):
                self.errors.append(f'Alte CSS-Variable "{var}" noch vorhanden')

        # ── Dark Mode ──
        if "data-theme" in self.css_content or 'data-theme="dark"' in self.css_content:
            self.has_dark_mode_css = True
        if "prefers-color-scheme: dark" in self.css_content:
            self.has_dark_mode_css = True

        if not self.has_dark_mode_css:
            self.errors.append("Dark Mode CSS fehlt (kein data-theme oder prefers-color-scheme)")

        if not self.has_theme_toggle:
            self.errors.append("Dark Mode Toggle-Button fehlt")

        # ── Skip Link ──
        if not self.has_skip_link:
            self.errors.append("Skip-Link fehlt (Accessibility)")

        # ── Main Element ──
        if not self.has_main:
            self.errors.append("<main> Element fehlt")

        # ── Nav Labels ──
        if self.has_nav and len(self.nav_labels) == 0:
            self.warnings.append("Keine <nav> mit aria-label gefunden")

        # ── Sticky Header ──
        if not self.has_sticky_header:
            if "position: sticky" in self.css_content or "position:sticky" in self.css_content:
                self.has_sticky_header = True
        if not self.has_sticky_header:
            self.warnings.append("Sticky Header nicht erkannt")

        # ── Heading Hierarchy ──
        if self.heading_levels:
            if self.heading_levels[0] != 1:
                self.warnings.append(f"Erste Heading ist h{self.heading_levels[0]}, sollte h1 sein")
            h1_count = self.heading_levels.count(1)
            if h1_count > 1:
                self.warnings.append(f"{h1_count} h1-Elemente gefunden (sollte 1 sein)")
            if h1_count == 0:
                self.errors.append("Kein h1-Element gefunden")
            # Check for skipped levels
            for i in range(1, len(self.heading_levels)):
                if self.heading_levels[i] > self.heading_levels[i-1] + 1:
                    self.warnings.append(
                        f"Heading-Level übersprungen: h{self.heading_levels[i-1]} → h{self.heading_levels[i]}")
                    break

        # ── Articles with aria-labelledby (editions only) ──
        if is_edition:
            articles_without_label = len(self.article_ids) - len(self.article_labelledby)
            if articles_without_label > 0:
                self.warnings.append(
                    f"{articles_without_label} Artikel ohne aria-labelledby")

        # ── Time elements ──
        times_without_dt = sum(1 for has_dt in self.time_has_datetime if not has_dt)
        if times_without_dt > 0:
            self.warnings.append(f"{times_without_dt} <time>-Elemente ohne datetime-Attribut")

        # ── Inline Styles ──
        if self.inline_style_count > 0:
            self.warnings.append(
                f"{self.inline_style_count} Inline-Styles gefunden (sollten in CSS sein)")
            for ex in self.inline_style_examples:
                self.info.append(f"  Beispiel: {ex}")

        # ── External Links rel ──
        links_without_rel = sum(1 for has_rel in self.external_links_have_rel if not has_rel)
        if links_without_rel > 0:
            self.warnings.append(
                f'{links_without_rel}/{len(self.external_links)} externe Links ohne rel="noopener noreferrer"')

        # ── Tool Radar Count (editions only) ──
        if is_edition and self.tool_card_count > 0:
            if self.tool_card_count not in (4, 6):
                self.errors.append(
                    f"Tool-Radar hat {self.tool_card_count} Tools (muss 4 oder 6 sein)")
            else:
                self.info.append(f"Tool-Radar: {self.tool_card_count} Tools (OK)")

        # ── Sepia Filter ──
        if self.img_sepia_count > 0:
            self.warnings.append(
                f"{self.img_sepia_count} Bilder mit Sepia-Filter (altes Design)")

        # ── CSS Checks ──

        # Focus-visible
        if ":focus-visible" in self.css_content:
            self.focus_visible = True
        if not self.focus_visible:
            self.errors.append(":focus-visible Styles fehlen (Accessibility)")

        # Reduced Motion
        if "prefers-reduced-motion" in self.css_content:
            self.has_reduced_motion = True
        if not self.has_reduced_motion:
            self.errors.append("prefers-reduced-motion wird nicht respektiert")

        # Print Styles
        if "@media print" in self.css_content:
            self.has_print_styles = True
        if not self.has_print_styles:
            self.warnings.append("Print-Stylesheet fehlt")

        # Hyphenation
        if "hyphens: auto" in self.css_content:
            self.has_hyphenation = True
        if not self.has_hyphenation:
            self.warnings.append("CSS hyphens: auto fehlt (wichtig für Deutsch)")

        # Max-width 68ch
        if "68ch" in self.css_content:
            self.has_max_width_68ch = True
        if not self.has_max_width_68ch and not is_homepage:
            self.warnings.append("max-width: 68ch für Artikeltext nicht gefunden")

        # Old newspaper patterns
        # Check for column-count on analysis body (not TOC which legitimately uses columns)
        if re.search(r'\.analysis[_-]?body\s*\{[^}]*column-count\s*:\s*2', self.css_content, re.DOTALL):
            self.errors.append("Altes 2-Spalten-Layout für Analyse-Text noch vorhanden")

        if 'feTurbulence' in content or 'fractalNoise' in content:
            self.errors.append("Alte Papier-Textur (SVG-Filter) noch vorhanden")

        if 'box-shadow' in self.css_content and 'paper' in self.css_content.lower():
            self.warnings.append("Möglicherweise alter Paper-Box-Shadow vorhanden")

        # Font size check
        font_sizes = re.findall(r'font-size:\s*([\d.]+)rem', self.css_content)
        for size_str in font_sizes:
            size = float(size_str)
            if size < MIN_FONT_SIZE_REM:
                self.errors.append(f"Font-Size {size}rem unter Minimum ({MIN_FONT_SIZE_REM}rem)")
                break

        # ── Script Checks (editions only) ──
        if is_edition:
            if "IntersectionObserver" in self.script_content:
                self.has_scroll_spy = True
            if not self.has_scroll_spy:
                self.warnings.append("Scroll-Spy (IntersectionObserver) fehlt")

        if "localStorage" in self.script_content and "theme" in self.script_content:
            self.has_dark_mode_toggle = True
        if not self.has_dark_mode_toggle:
            self.warnings.append("Theme-Toggle Script (localStorage) fehlt")

        # ── Content Width ──
        if "800px" not in self.css_content and "width-content" not in self.css_content:
            self.warnings.append("Einheitliche Content-Breite (800px) nicht gefunden")

        return self.errors, self.warnings, self.info


# ─── Runner ──────────────────────────────────────────────────────────────────

def validate_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    validator = DesignValidator()
    errors, warnings, info = validator.validate(filepath, content)
    return errors, warnings, info


def main():
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        base = os.path.dirname(os.path.abspath(__file__))
        files = []
        files.append(os.path.join(base, "index.html"))
        files.extend(sorted(glob.glob(os.path.join(base, "editions", "*.html"))))
        files.extend(sorted(glob.glob(os.path.join(base, "editions", "reportagen", "*.html"))))
        files = [f for f in files if os.path.exists(f)]

    if not files:
        print("Keine HTML-Dateien gefunden.")
        sys.exit(1)

    total_errors = 0
    total_warnings = 0

    for filepath in files:
        relpath = os.path.relpath(filepath, os.path.dirname(os.path.abspath(__file__)))
        errors, warnings, info = validate_file(filepath)
        total_errors += len(errors)
        total_warnings += len(warnings)

        if errors or warnings:
            status = "FAIL" if errors else "WARN"
            print(f"\n{'=' * 60}")
            print(f"  {status}  {relpath}")
            print(f"{'=' * 60}")

            if errors:
                for e in errors:
                    print(f"  \033[91mERROR\033[0m  {e}")
            if warnings:
                for w in warnings:
                    print(f"  \033[93m WARN\033[0m  {w}")
            if info:
                for i in info:
                    print(f"  \033[90m INFO\033[0m  {i}")
        else:
            print(f"  \033[92m  OK \033[0m  {relpath}")

    print(f"\n{'─' * 60}")
    print(f"  Ergebnis: {len(files)} Dateien, {total_errors} Fehler, {total_warnings} Warnungen")

    if total_errors > 0:
        print(f"  \033[91m{'─' * 58}\033[0m")
        print(f"  \033[91m  {total_errors} FEHLER müssen behoben werden.\033[0m")
        sys.exit(1)
    elif total_warnings > 0:
        print(f"  \033[93m  Alles OK, aber {total_warnings} Warnungen prüfen.\033[0m")
    else:
        print(f"  \033[92m  Alles perfekt!\033[0m")

    sys.exit(0)


if __name__ == "__main__":
    main()
