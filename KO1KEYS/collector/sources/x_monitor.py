"""KO1KEYSキーワードでXを検索し、注目度の高い投稿を抽出する。

snscrapeはAPIキー無しでX検索結果を取得できるOSSツール。
X側の仕様変更で動作しなくなる可能性がある点は運用上の制約として承知の上で使用する。
"""
import os
import subprocess
import json
from datetime import datetime, timedelta, timezone


def fetch_posts(keyword: str, since_hours: int = 24, limit: int = 100):
    since = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).strftime("%Y-%m-%d")
    query = f"{keyword} since:{since}"
    cmd = [
        "snscrape",
        "--jsonl",
        "--max-results", str(limit),
        "twitter-search", query,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    posts = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        posts.append(json.loads(line))
    return posts


def filter_by_engagement(posts, min_likes: int, min_retweets: int):
    filtered = []
    for p in posts:
        likes = p.get("likeCount") or 0
        retweets = p.get("retweetCount") or 0
        if likes >= min_likes or retweets >= min_retweets:
            filtered.append(p)
    filtered.sort(key=lambda p: (p.get("likeCount") or 0) + (p.get("retweetCount") or 0), reverse=True)
    return filtered


def collect():
    keywords = [k.strip() for k in (os.environ.get("SEARCH_KEYWORD") or "KO1KEYZ").split(",") if k.strip()]
    min_likes = int(os.environ.get("X_MIN_LIKES") or "50")
    min_retweets = int(os.environ.get("X_MIN_RETWEETS") or "10")

    items = []
    seen_ids = set()
    for keyword in keywords:
        posts = fetch_posts(keyword)
        top_posts = filter_by_engagement(posts, min_likes, min_retweets)
        for p in top_posts:
            item_id = f"x:{p.get('id')}"
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            items.append({
                "id": item_id,
                "title": (p.get("rawContent") or p.get("content") or "")[:120],
                "url": p.get("url"),
                "likes": p.get("likeCount") or 0,
                "retweets": p.get("retweetCount") or 0,
                "source": "x",
            })
    return items


if __name__ == "__main__":
    for item in collect():
        print(item)
