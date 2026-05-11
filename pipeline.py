#!/usr/bin/env python3
"""
DailyGrass News Pipeline
1. Fetch politics RSS feeds
2. Prepare article drafts for Hermes to rewrite
3. Build Hugo site
4. Deploy to GitHub Pages
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SITE_DIR = Path("/volume1/AI/dailygrass")
CONTENT_DIR = SITE_DIR / "content" / "posts"
PUBLIC_DIR = SITE_DIR / "public"
FEEDS_FILE = SITE_DIR / ".feeds.json"

# Politics RSS feeds
RSS_FEEDS = {
    "reuters": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=bwp",
    "bbc": "https://feeds.bbci.co.uk/news/politics/rss.xml",
    "ap": "https://rsshub.app/apnews/topics/apf-politics",
    "guardian": "https://www.theguardian.com/politics/rss",
    "politico": "https://rss.politico.com/politics-news.xml",
    "thehill": "https://thehill.com/feed",
    "reuters_world": "https://www.reutersagency.com/feed/?taxonomy=best-regions&post_type=bwp&best_region=world",
}

CATEGORIES = [
    "US Politics",
    "World Affairs",
    "Policy & Legislation",
    "Elections",
    "International Relations",
    "Economy & Trade",
]


def fetch_feeds():
    """Fetch and parse RSS feeds, return a list of article candidates."""
    try:
        import feedparser
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "feedparser"],
            capture_output=True,
        )
        import feedparser

    articles = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:  # Top 3 per source
                articles.append(
                    {
                        "source": source,
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "summary": entry.get("summary", entry.get("description", "")),
                        "published": entry.get("published", datetime.now().isoformat()),
                    }
                )
        except Exception as e:
            print(f"  [WARN] Failed to fetch {source}: {e}")

    return articles


def create_article_frontmatter(title, date, category, tags, summary):
    """Create Hugo frontmatter for an article."""
    tags_yaml = "\n".join(f"  - {t}" for t in tags)
    return f"""---
title: "{title}"
date: {date}
draft: false
categories:
  - {category}
tags:
{tags_yaml}
summary: "{summary}"
---

"""


def save_article_draft(filename, frontmatter, content):
    """Save a Hugo markdown article."""
    filepath = CONTENT_DIR / filename
    with open(filepath, "w") as f:
        f.write(frontmatter)
        f.write(content)
    print(f"  [OK] Saved: {filepath.name}")
    return filepath


def build_site():
    """Run Hugo build."""
    result = subprocess.run(
        ["hugo"], cwd=SITE_DIR, capture_output=True, text=True
    )
    if result.returncode == 0:
        print("  [OK] Hugo build successful")
    else:
        print(f"  [ERR] Hugo build failed: {result.stderr}")
    return result.returncode == 0


def deploy():
    """Push built site to gh-pages."""
    os.chdir(PUBLIC_DIR)
    subprocess.run(["git", "init"], capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "DailyGrass Deploy"],
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "deploy@dailygrass.news"],
        capture_output=True,
    )
    subprocess.run(["git", "add", "-A"], capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"Daily update {datetime.now().strftime('%Y-%m-%d')}"],
        capture_output=True,
    )

    # Use token from git credentials
    result = subprocess.run(
        [
            "git",
            "push",
            "-f",
            "https://github.com/moobaozi/dailygrass.git",
            "HEAD:gh-pages",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("  [OK] Deployed to GitHub Pages")
    else:
        print(f"  [ERR] Deploy failed: {result.stderr[:200]}")
    return result.returncode == 0


def list_today_articles():
    """List today's articles in the content dir."""
    today = datetime.now().strftime("%Y-%m-%d")
    articles = sorted(CONTENT_DIR.glob(f"{today}-*.md"))
    return articles


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "fetch":
        print("[DailyGrass Pipeline] Fetching RSS feeds...")
        articles = fetch_feeds()
        # Save for Hermes to process
        output = {"fetched_at": datetime.now().isoformat(), "articles": articles}
        with open(FEEDS_FILE, "w") as f:
            json.dump(output, f, indent=2)
        print(f"  [OK] Saved {len(articles)} article candidates to .feeds.json")

    elif cmd == "build":
        print("[DailyGrass Pipeline] Building Hugo site...")
        build_site()

    elif cmd == "deploy":
        print("[DailyGrass Pipeline] Deploying to GitHub Pages...")
        deploy()

    elif cmd == "publish":
        print("[DailyGrass Pipeline] Building + Deploying...")
        if build_site():
            deploy()

    elif cmd == "list":
        today = datetime.now().strftime("%Y-%m-%d")
        articles = list(CONTENT_DIR.glob("*.md"))
        print(f"Total articles: {len(articles)}")
        for a in sorted(articles, reverse=True)[:10]:
            print(f"  {a.name}")

    else:
        print("""DailyGrass Pipeline Commands:
  fetch   - Fetch latest politics RSS feeds
  build   - Build Hugo site
  deploy  - Deploy to GitHub Pages
  publish - Build + Deploy
  list    - List recent articles
""")
