# Die Inferenz

Dieses Projekt erzeugt ein professionell designtes, deutschsprachiges AI-Nachrichtenmagazin und published es auf GitHub Pages.

## Repo-Struktur

```
ai_news_agent.py          # Python-Script: holt AI-News aus RSS-Feeds & Web-Quellen
editions/                  # Archiv aller Ausgaben (YYYY-MM-DD.html)
editions/reportagen/       # Eigene Seiten für In-Depth-Reportagen (YYYY-MM-DD.html)
editions/published-topics.md  # Tracking publizierter Themen (Duplikat-Vermeidung)
reportage-themen.md        # Wunschliste für Reportage-Themen
index.html                 # Homepage: Editions-Übersicht mit Mini-Editionen
hardware-guide.html        # Referenzseite: Inferenz-Hardware für Zuhause (GPUs, Apple Silicon, Benchmarks)
about.html                 # Erklärt die Aggregations-Pipeline
impressum.html             # Impressum (Pflicht nach TMG)
datenschutz.html           # Datenschutzerklärung (Pflicht nach DSGVO)
assets/fonts/              # Self-hosted Webfonts (Inter, Source Serif 4, DM Mono, Fraunces)
assets/fonts/fonts.css     # @font-face Deklarationen
assets/images/thumbs/      # Lokal gespeicherte YouTube-Thumbnails (VIDEO_ID.jpg)
assets/images/icons/       # Lokal gespeicherte Tool-Favicons (domain.com.png)
CNAME                      # Custom Domain für GitHub Pages (die-inferenz.de)
```

## Publishing

- GitHub Pages Repo: `BlackMac/ai-news-magazin` (https://die-inferenz.de)
- Source-Code und publizierte Dateien leben im selben Repo
- GitHub Pages serviert direkt vom `main`-Branch
- Custom Domain: `die-inferenz.de` (konfiguriert via `CNAME`-Datei)
- Alte URL `blackmac.github.io/ai-news-magazin` leitet automatisch auf `die-inferenz.de` weiter

## Design-System: Readability-First

Alle Seiten folgen einem einheitlichen, auf maximale Lesbarkeit optimierten Design. Kein Zeitungs-Look, kein dekoratives Design — Fokus auf Inhalt und Leseerlebnis. Dark Mode wird unterstützt.

### Fonts (Self-Hosted)
- **Source Serif 4** (wght 400–700, italic 400) — Fließtext, Analyse-Abschnitte, Teaser
- **Inter** (wght 400–800) — Headlines, Kicker, Meta, Navigation, UI-Elemente
- **DM Mono** + **Fraunces** — nur About-Seite

Alle Fonts liegen als WOFF2 unter `assets/fonts/`. Keine externen Font-Requests (DSGVO-konform).

Font-Loading (Pfad relativ zur HTML-Datei):
```html
<!-- Root-Level (index.html, about.html, etc.) -->
<link rel="stylesheet" href="assets/fonts/fonts.css">
<!-- editions/*.html -->
<link rel="stylesheet" href="../assets/fonts/fonts.css">
<!-- editions/reportagen/*.html -->
<link rel="stylesheet" href="../../assets/fonts/fonts.css">
```

### Farbschema
```css
/* Light Mode */
--bg: #faf9f6;              /* Warmes Off-White */
--bg-surface: #f0eee8;      /* Cards, Hintergründe */
--bg-surface-hover: #e8e5dd; /* Hover-State */
--text-primary: #1a1a1a;    /* Headlines, starker Text */
--text-body: #2d2d2d;       /* Fließtext */
--text-muted: #5a5a5a;      /* Meta, Quellen */
--text-faint: #8a8a8a;      /* Kategorien, dezent */
--border: #d8d5cc;          /* Trennlinien */
--border-strong: #b0ada4;   /* Stärkere Trennlinien */
--accent: #b91c1c;          /* Kicker, Akzente */
--link: #1d4ed8;            /* Links */
--link-visited: #6d28d9;    /* Besuchte Links */

/* Dark Mode (via data-theme="dark" oder prefers-color-scheme) */
--bg: #121212;
--bg-surface: #1e1e1e;
--text-primary: #e8e6e0;
--text-body: #d0cec8;
--accent: #ef5350;
--link: #93c5fd;
```

### Layout-Prinzipien
- **Einheitliche Maximalbreite**: Alle Inhalte (Header, Artikel, Grids, Footer) auf `--width-content: 800px`
- **Artikeltext**: `max-width: 68ch` für optimale Zeilenlänge (60–68 Zeichen)
- **Single Column**: Kein Multi-Column-Layout für Fließtext — nur Grid für Tool-Radar und YouTube-Cards
- **Sticky Header**: Seiten-Header mit Logo, Nav und Dark-Mode-Toggle
- **Spacing-System**: CSS Custom Properties (`--space-1` bis `--space-24`)
- **Responsive Font-Scaling**: 18px → 19px (1024px+) → 20px (1280px+)
- **Hyphenation**: `hyphens: auto` mit `hyphenate-limit-chars: 6 3 2` (erfordert `lang="de"`)
- **Dark Mode Toggle**: Mond/Sonne-Button im Header, Auswahl in localStorage

### Typografie-Richtlinien
- **Fließtext**: `1.125rem`, line-height `1.75`, Source Serif 4
- **Headlines (h2)**: Inter, `font-weight: 700`, `text-wrap: balance`
- **Leitartikel-Headline**: `var(--text-3xl)` (2.25rem)
- **Kicker-Labels**: Inter, `0.7rem`, uppercase, `letter-spacing: 0.1em`, Akzentfarbe
- **Meta-Info**: Inter, `var(--text-sm)` (0.875rem), muted
- **Keine Schriftgröße unter `0.7rem`**

### Accessibility
- **Skip-Link**: Erstes fokussierbares Element, springt zu `#main-content`
- **Semantisches HTML**: `<article>`, `<section>`, `<nav>`, `<main>`, `<header>`, `<footer>`
- **ARIA-Labels**: Jede `<nav>` hat eindeutiges `aria-label`, Artikel haben `aria-labelledby`
- **Focus-Styles**: `outline: 3px solid var(--accent)` auf `:focus-visible`
- **Reduced Motion**: `prefers-reduced-motion` wird respektiert
- **Print-Stylesheet**: Nav ausgeblendet, Link-URLs angezeigt, Seitenumbrüche optimiert

### Seiten-Strukturen

**Edition (editions/YYYY-MM-DD.html):**
- Sticky Header mit Logo, Nav-Links, Dark-Mode-Toggle
- Edition-Header: Datum, Titel ("Ausgabe vom DD. Monat YYYY"), Untertitel
- Inhaltsverzeichnis als `<nav>`:
  - Nummerierte Artikel in 2-Spalten-Liste (gestapelt: Kategorie über Titel)
  - Separator-Linie vor Special-Sektionen
  - Special-Sektionen (Reportage, Tool-Radar, Werkstatt) als Flex-Row mit roter Left-Border
  - Scroll-Spy via IntersectionObserver hebt aktiven Artikel hervor
- Leitartikel mit größerer Headline (`--text-3xl`), roter Teaser-Border
- Weitere Artikel: Kicker, Headline, Meta mit `<time>`, Teaser (border-left), Analyse-Body (68ch), Quellen
- Reportage-Teaser als Card mit bg-surface, "Weiterlesen →"-Link
- "Tool-Radar"-Sektion: Immer genau 4 oder 6 neue/trendende AI-Tools des Tages (immer gerade Anzahl fürs Grid-Layout)
   - Grid-Layout mit abgerundeten Cards (8px radius), Hover-State
   - Pro Tool: Favicon (40×40), Name als Link, Beschreibung, Meta-Info
- "Aus der Werkstatt"-Sektion mit YouTube-Cards (Thumbnail, Label, Titel, Channel, Beschreibung)
   - Trending-Topic-Card: `border: 2px solid var(--accent)`, Full-Width mit 2-Spalten-Grid
- Footer mit Copyright, Links zu Impressum/Datenschutz und Nach-oben-Link
- Scripts: Scroll-Spy (IntersectionObserver) + Theme-Toggle (localStorage)

**Homepage (index.html):**
- Gleicher Sticky Header
- Editions-Liste mit Datum, Leitartikel-Headline + Teaser, Story-Links
- Reportagen-Archiv

**Reportage (editions/reportagen/YYYY-MM-DD.html):**
- Gleicher Sticky Header mit Navigation zurück zur Edition und Homepage
- Volltext mit Zwischenüberschriften, `max-width: 68ch`, Quellenangaben

**About-Seite (about.html):**
- Eigenes Design, erklärt die Pipeline-Stufen

### DSGVO / Datenschutz
- **Keine externen Requests** aus dem Browser: Fonts, Thumbnails und Favicons sind self-hosted
- **Kein Tracking, keine Cookies, keine Analytics**
- **Impressum** (`impressum.html`) und **Datenschutzerklärung** (`datenschutz.html`) im Footer jeder Seite verlinkt
- Hosting via GitHub Pages (GitHub Inc., USA) — in der Datenschutzerklärung dokumentiert

## Python-Script Dependencies

```
pip install feedparser requests beautifulsoup4 python-dateutil lxml
```

## Workflow: Neue Edition erstellen

1. **News aggregieren**: `python3 ai_news_agent.py --format json --output /tmp/news-raw.json`
   - Artikel ohne Datum (`"published": null`) werden aufgenommen — stammen von Web-gescrapten Quellen (Meta AI, Anthropic Blog)
2. **Datums-Verifizierung**: Für Artikel mit `published: null` parallel Agents starten, die per WebSearch das Veröffentlichungsdatum recherchieren. Alte Artikel (>24h) rausfiltern.
3. **Duplikat-Check**: Abgleich mit `editions/published-topics.md` — exakt selbes Ereignis überspringen, neue Entwicklungen aufnehmen und auf frühere Ausgabe verlinken
4. **Recherche & Fact-Checking**: Für jeden relevanten Artikel Hintergrund-Recherche via WebSearch, Fakten aus mindestens 2 unabhängigen Quellen verifizieren
5. **AI-Tool-Radar**: Neue und trendende AI-Tools des Tages recherchieren:
   - **Duplikat-Check PFLICHT**: Vor Aufnahme jedes Tools gegen die Liste "Tool-Radar — Bereits empfohlene Tools" in `editions/published-topics.md` prüfen. Kein Tool darf ein zweites Mal erscheinen.
   - **Aktualität PFLICHT**: Nur Tools aufnehmen, die in den letzten 7 Tagen gelauncht, aktualisiert oder viral gegangen sind. Ältere Tools sind nicht zulässig, auch wenn sie "neu entdeckt" werden. Bei der Recherche das Release-/Ankündigungsdatum verifizieren.
   - Via WebSearch nach neuen AI-Tool-Launches, Product Hunt AI-Kategorie, Hacker News Tool-Ankündigungen, Twitter/X AI-Tool-Trends suchen
   - Breites Spektrum: Coding-Assistenten, Productivity-Apps, Kreativ-Tools, Business-Automation, Agent-Frameworks, neue APIs
   - Immer genau 4 oder 6 Tools pro Ausgabe (gerade Anzahl fürs Grid-Layout)
   - Pro Tool recherchieren: Was macht es? Was ist neu/anders daran? Wer steckt dahinter? Seit wann verfügbar?
   - Icons/Logos beschaffen und **lokal speichern**: Favicon herunterladen via `curl -sL "https://www.google.com/s2/favicons?domain=DOMAIN&sz=64" -o assets/images/icons/DOMAIN.png`. Im HTML dann `assets/images/icons/DOMAIN.png` (bzw. relativer Pfad) referenzieren. Keine externen Bild-URLs im HTML!
   - **Auswahlkriterien**: Bevorzugt Tools die (a) gerade erst gelauncht wurden, (b) einen neuen Ansatz verfolgen, (c) auf Product Hunt/HN/Twitter trenden, oder (d) eine spannende Nische bedienen
6. **YouTube-Tutorials**: Via `yt-dlp` (ist installiert) recherchieren:
   - 2 aktuelle, technische KI-Tutorials von etablierten Creatorn
   - 1 **Trending Topic**: Video von einem kleineren Creator (< 100K Subs), das überproportional viele Views hat (mindestens 3x Subscriber-Count oder viral gehend). Kleinere Creator sind oft Frühindikatoren für Trends.
   - **Duplikat-Check PFLICHT für YouTube**: Vor Aufnahme jedes Videos (insbesondere Trending Topics) gegen die Liste "YouTube — Bereits empfohlene Videos" in `editions/published-topics.md` prüfen. Kein Video (gleiche Video-ID) darf ein zweites Mal erscheinen.
   - **Maximale Videolänge**: Alle empfohlenen Videos sollten unter 60 Minuten sein — idealerweise 10–30 Min. Keine Livestreams oder Mehrstunden-Kurse.
   - Recherche-Methode: `yt-dlp --flat-playlist --print "%(id)s|%(title)s|%(channel)s" "ytsearch20:SUCHBEGRIFF"` für Suche, dann `yt-dlp --print "%(id)s|%(title)s|%(channel)s|%(upload_date)s|%(duration_string)s|%(view_count)s|%(channel_follower_count)s" --skip-download URL` für Details inkl. Subscriber-Count
   - Thumbnails **lokal speichern**: `curl -sL "https://i.ytimg.com/vi/VIDEO_ID/mqdefault.jpg" -o assets/images/thumbs/VIDEO_ID.jpg`. Im HTML dann `assets/images/thumbs/VIDEO_ID.jpg` (bzw. relativer Pfad) referenzieren. Keine externen Bild-URLs im HTML!
7. **In-Depth-Reportage**: Thema aus `reportage-themen.md` (oder frei gewählt), gründlich recherchiert, 800-1500 Wörter
8. **Edition-HTML erzeugen**: Im Readability-Design (siehe Design-System oben). Inhalt auf Deutsch.
   - Nachrichtenartikel, Reportage-Teaser, Tool-Radar-Sektion, YouTube-Sektion
   - Reportage als eigene HTML-Seite unter `editions/reportagen/`
9. **Homepage aktualisieren**: `index.html` mit Mini-Edition ergänzen, inkl. Reportage-Teaser, Tool-Radar, YouTube-Werkstatt-Eintrag
   - Inhaltsverzeichnis der Edition muss Reportage, Tool-Radar und Werkstatt-Sektion enthalten
   - Homepage-Storyliste muss Reportage, Tool-Radar und Werkstatt verlinken
   - **Reportagen-Archiv**: Neue Reportage in die `<ul class="reportagen-list">` Sektion einfügen (chronologisch absteigend, neueste oben)
10. **Publizieren**: Änderungen committen und pushen (Source-Code und Pages leben im selben Repo)
11. **Themen-Tracking**: `published-topics.md` aktualisieren (Artikel, Tool-Radar-Tools UND YouTube-Videos in die jeweilige Sektion eintragen), Reportage-Thema aus Wunschliste löschen

## Sprache

Alle Magazin-Inhalte auf Deutsch. Code-Kommentare und technische Docs auf Englisch.
