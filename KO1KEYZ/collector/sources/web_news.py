"""Google News RSSを使い、KO1KEYZに関するWeb/ニュース言及を無料で取得する。"""
import os
import feedparser
from urllib.parse import quote


def collect():
    keywords = [k.strip() for k in (os.environ.get("SEARCH_KEYWORD") or "KO1KEYZ").split(",") if k.strip()]

    items = []
    seen_ids = set()
    for keyword in keywords:
        url = f"https://news.google.com/rss/search?q={quote(keyword)}&hl=ja&gl=JP&ceid=JP:ja"
        feed = feedparser.parse(url)
        for entry in feed.entries:
            item_id = f"news:{entry.get('id') or entry.get('link')}"
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            items.append({
                "id": item_id,
                "title": entry.get("title", ""),
                "url": entry.get("link"),
                "source": "web_news",
            })
    return items


if __name__ == "__main__":
    for item in collect():
        print(item)
