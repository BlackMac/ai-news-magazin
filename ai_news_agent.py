#!/usr/bin/env python3
"""
AI News Agent - Zieht AI-Nachrichten der letzten 24 Stunden aus verschiedenen Quellen.

Strategie:
1. RSS-Feeds als primaere Quelle (schnell, strukturiert)
2. Web-Scraping als Fallback fuer Quellen ohne RSS
3. WebFetch -> curl Fallback bei Verbindungsproblemen
4. Filtert auf max. 24h alte Artikel
"""

import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass, field, asdict

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser


# --- Konfiguration ---

@dataclass
class Source:
    name: str
    url: str
    source_type: str  # "rss" oder "web"
    category: str  # "news", "research", "lab", "community"


SOURCES = [
    # Tier 1: Redaktionelle News (RSS)
    Source("MIT Technology Review", "https://www.technologyreview.com/topic/artificial-intelligence/feed", "rss", "news"),
    Source("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "rss", "news"),
    Source("VentureBeat AI", "https://venturebeat.com/category/ai/feed/", "rss", "news"),
    Source("Ars Technica", "https://feeds.arstechnica.com/arstechnica/technology-lab", "rss", "news"),
    Source("The Verge", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "rss", "news"),
    Source("Wired AI", "https://www.wired.com/feed/tag/ai/latest/rss", "rss", "news"),
    Source("AI News", "https://www.artificialintelligence-news.com/feed/", "rss", "news"),
    Source("Reuters AI", "https://www.reuters.com/technology/artificial-intelligence/rss", "rss", "news"),

    # Tier 1b: Deutschsprachige Redaktionelle News (RSS)
    Source("heise online", "https://www.heise.de/rss/heise-atom.xml", "rss", "news"),
    Source("Golem.de", "https://rss.golem.de/rss.php?feed=ATOM1.0", "rss", "news"),
    Source("t3n", "https://t3n.de/rss.xml", "rss", "news"),
    Source("Spiegel Netzwelt", "https://www.spiegel.de/netzwelt/index.rss", "rss", "news"),
    Source("Netzpolitik.org", "https://netzpolitik.org/feed/", "rss", "news"),

    # Tier 2: Lab-Blogs (RSS + Web-Fallback)
    Source("OpenAI Blog", "https://openai.com/blog/rss.xml", "rss", "lab"),
    Source("Google DeepMind", "https://deepmind.google/blog/rss.xml", "rss", "lab"),
    Source("Anthropic Blog", "https://www.anthropic.com/news", "web", "lab"),
    Source("Meta AI Blog", "https://ai.meta.com/blog/", "web", "lab"),
    Source("NVIDIA Blog", "https://developer.nvidia.com/blog/feed/", "rss", "lab"),
    Source("Hugging Face Blog", "https://huggingface.co/blog/feed.xml", "rss", "lab"),

    # Tier 3: Research
    Source("arXiv cs.AI", "https://rss.arxiv.org/rss/cs.AI", "rss", "research"),

    # Tier 4: Community
    Source("Hacker News AI", "https://hnrss.org/newest?q=AI+OR+LLM+OR+%22artificial+intelligence%22&points=50", "rss", "community"),
]


@dataclass
class Article:
    title: str
    url: str
    source: str
    category: str
    published: Optional[datetime] = None
    summary: str = ""


# --- Fetch-Funktionen ---

def fetch_url(url: str, timeout: int = 30) -> Optional[str]:
    """Versucht URL zu fetchen: requests -> curl Fallback."""
    # Versuch 1: requests
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200 and len(resp.text) > 100:
            return resp.text
        print(f"  [requests] Status {resp.status_code} fuer {url}", file=sys.stderr)
    except Exception as e:
        print(f"  [requests] Fehler fuer {url}: {e}", file=sys.stderr)

    # Versuch 2: curl Fallback
    try:
        print(f"  [curl] Fallback fuer {url}...", file=sys.stderr)
        result = subprocess.run(
            [
                "curl", "-sL",
                "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "--max-time", str(timeout),
                url
            ],
            capture_output=True, text=True, timeout=timeout + 5
        )
        if result.returncode == 0 and len(result.stdout) > 100:
            return result.stdout
        print(f"  [curl] Returncode {result.returncode} fuer {url}", file=sys.stderr)
    except Exception as e:
        print(f"  [curl] Fehler fuer {url}: {e}", file=sys.stderr)

    return None


def parse_date(date_str: str) -> Optional[datetime]:
    """Parst verschiedene Datumsformate und gibt UTC-aware datetime zurueck."""
    if not date_str:
        return None
    try:
        dt = dateutil_parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def is_within_24h(dt: Optional[datetime], cutoff: datetime) -> bool:
    """Prueft ob Datum innerhalb der letzten 24 Stunden liegt."""
    if dt is None:
        return False
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt >= cutoff
    except Exception:
        return False


# --- Quellen-Parser ---

def parse_rss_feed(content: str, source: Source, cutoff: datetime) -> list[Article]:
    """Parst RSS/Atom Feed und filtert auf 24h."""
    articles = []
    feed = feedparser.parse(content)

    for entry in feed.entries:
        # Datum ermitteln
        date_str = entry.get("published") or entry.get("updated") or entry.get("created")
        pub_date = parse_date(date_str)

        if not is_within_24h(pub_date, cutoff):
            continue

        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()

        # Summary extrahieren
        summary = ""
        if entry.get("summary"):
            soup = BeautifulSoup(entry.summary, "html.parser")
            summary = soup.get_text(separator=" ", strip=True)[:500]

        if title and link:
            articles.append(Article(
                title=title,
                url=link,
                source=source.name,
                category=source.category,
                published=pub_date,
                summary=summary,
            ))

    return articles


def parse_anthropic_blog(content: str, source: Source, cutoff: datetime) -> list[Article]:
    """Scrapet die Anthropic News-Seite."""
    articles = []
    soup = BeautifulSoup(content, "lxml")

    for item in soup.select("a[href*='/news/'], a[href*='/research/']"):
        title_el = item.select_one("h3, h2, [class*='title'], [class*='heading']")
        title = title_el.get_text(strip=True) if title_el else item.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        href = item.get("href", "")
        if not href:
            continue
        url = href if href.startswith("http") else f"https://www.anthropic.com{href}"

        # Datum suchen: zuerst auf der Uebersichtsseite
        date_el = item.find_parent().select_one("time, [class*='date'], [datetime]") if item.find_parent() else None
        pub_date = None
        if date_el:
            date_str = date_el.get("datetime") or date_el.get_text(strip=True)
            pub_date = parse_date(date_str)

        # Ohne Datum: aufnehmen, wird spaeter per WebSearch verifiziert
        # Mit Datum: nur aufnehmen wenn innerhalb 24h
        if pub_date is not None and not is_within_24h(pub_date, cutoff):
            continue

        summary_el = item.select_one("p, [class*='description'], [class*='excerpt']")
        summary = summary_el.get_text(strip=True)[:500] if summary_el else ""

        articles.append(Article(
            title=title,
            url=url,
            source=source.name,
            category=source.category,
            published=pub_date,
            summary=summary,
        ))

    return articles



def parse_meta_ai_blog(content: str, source: Source, cutoff: datetime) -> list[Article]:
    """Scrapet den Meta AI Blog. Artikel ohne Datum werden aufgenommen und spaeter verifiziert."""
    articles = []
    soup = BeautifulSoup(content, "lxml")
    seen_urls = set()

    for item in soup.select("a[href*='/blog/']"):
        title = item.get_text(strip=True)
        if not title or len(title) < 10:
            continue

        href = item.get("href", "")
        if not href or href == "/blog/":
            continue
        url = href if href.startswith("http") else f"https://ai.meta.com{href}"

        if url in seen_urls:
            continue
        seen_urls.add(url)

        articles.append(Article(
            title=title,
            url=url,
            source=source.name,
            category=source.category,
            published=None,
            summary="",
        ))

    return articles


def parse_web_source(content: str, source: Source, cutoff: datetime) -> list[Article]:
    """Dispatch fuer Web-Quellen."""
    if "anthropic" in source.url:
        return parse_anthropic_blog(content, source, cutoff)
    elif "meta.com" in source.url:
        return parse_meta_ai_blog(content, source, cutoff)
    return []


# --- Deduplizierung ---

def deduplicate(articles: list[Article]) -> list[Article]:
    """Entfernt Duplikate basierend auf URL und aehnlichen Titeln."""
    seen_urls = set()
    seen_titles = set()
    unique = []

    for a in articles:
        normalized_url = a.url.rstrip("/").lower()
        normalized_title = a.title.lower().strip()

        if normalized_url in seen_urls:
            continue
        if normalized_title in seen_titles:
            continue

        seen_urls.add(normalized_url)
        seen_titles.add(normalized_title)
        unique.append(a)

    return unique


# --- Hauptlogik ---

def fetch_all_news(max_age_hours: int = 24) -> list[Article]:
    """Holt alle News der letzten max_age_hours Stunden."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    all_articles: list[Article] = []
    stats = {"success": 0, "failed": 0, "sources": {}}

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"AI News Agent - Hole Artikel seit {cutoff.strftime('%Y-%m-%d %H:%M UTC')}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    for source in SOURCES:
        print(f"[{source.name}] Fetching...", file=sys.stderr)
        content = fetch_url(source.url)

        if not content:
            print(f"  FEHLGESCHLAGEN - keine Daten erhalten\n", file=sys.stderr)
            stats["failed"] += 1
            stats["sources"][source.name] = "failed"
            continue

        try:
            if source.source_type == "rss":
                articles = parse_rss_feed(content, source, cutoff)
            else:
                articles = parse_web_source(content, source, cutoff)

            all_articles.extend(articles)
            stats["success"] += 1
            stats["sources"][source.name] = f"{len(articles)} Artikel"
            print(f"  OK - {len(articles)} Artikel in den letzten {max_age_hours}h\n", file=sys.stderr)

        except Exception as e:
            print(f"  PARSE-FEHLER: {e}\n", file=sys.stderr)
            stats["failed"] += 1
            stats["sources"][source.name] = f"parse_error: {e}"

    # Deduplizieren und sortieren
    all_articles = deduplicate(all_articles)
    all_articles.sort(key=lambda a: a.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    # Stats ausgeben
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Ergebnis: {len(all_articles)} einzigartige Artikel", file=sys.stderr)
    print(f"Quellen: {stats['success']} OK, {stats['failed']} fehlgeschlagen", file=sys.stderr)
    for name, status in stats["sources"].items():
        print(f"  - {name}: {status}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    return all_articles


def format_output(articles: list[Article], output_format: str = "text") -> str:
    """Formatiert die Artikel als Text oder JSON."""
    if output_format == "json":
        data = []
        for a in articles:
            d = asdict(a)
            d["published"] = a.published.isoformat() if a.published else None
            data.append(d)
        return json.dumps(data, indent=2, ensure_ascii=False)

    # Text-Format
    lines = []
    lines.append(f"# AI News - Letzte 24 Stunden")
    lines.append(f"# Stand: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"# Anzahl: {len(articles)} Artikel")
    lines.append("")

    current_category = None
    category_labels = {
        "news": "Nachrichten",
        "lab": "Lab-Blogs & Ankuendigungen",
        "research": "Research",
        "community": "Community",
    }

    for a in articles:
        if a.category != current_category:
            current_category = a.category
            lines.append(f"\n## {category_labels.get(a.category, a.category)}\n")

        date_str = a.published.strftime("%Y-%m-%d %H:%M") if a.published else "Datum unbekannt"
        lines.append(f"### [{a.source}] {a.title}")
        lines.append(f"    Datum: {date_str}")
        lines.append(f"    URL:   {a.url}")
        if a.summary:
            lines.append(f"    {a.summary[:200]}...")
        lines.append("")

    return "\n".join(lines)


def main():
    import argparse

    ap = argparse.ArgumentParser(description="AI News Agent - Letzte 24h AI-Nachrichten")
    ap.add_argument("--hours", type=int, default=24, help="Max. Alter in Stunden (default: 24)")
    ap.add_argument("--format", choices=["text", "json"], default="text", help="Ausgabeformat")
    ap.add_argument("--output", type=str, default=None, help="Ausgabedatei (default: stdout)")
    args = ap.parse_args()

    articles = fetch_all_news(max_age_hours=args.hours)
    result = format_output(articles, output_format=args.format)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Ergebnis in {args.output} geschrieben.", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
