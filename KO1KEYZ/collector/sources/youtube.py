"""YouTube Data API v3で、一般ユーザー投稿を含む動画タイトル/概要からKO1KEYZ関連の最新情報を拾う。"""
import os
import requests

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def collect():
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("[youtube] skipped: YOUTUBE_API_KEY not set")
        return []

    keywords = [k.strip() for k in (os.environ.get("SEARCH_KEYWORD") or "KO1KEYZ").split(",") if k.strip()]

    items = []
    seen_ids = set()
    for keyword in keywords:
        params = {
            "key": api_key,
            "q": keyword,
            "part": "snippet",
            "type": "video",
            "order": "date",
            "maxResults": 10,
            "relevanceLanguage": "ja",
        }
        resp = requests.get(SEARCH_URL, params=params, timeout=10)
        resp.raise_for_status()
        for entry in resp.json().get("items", []):
            video_id = entry.get("id", {}).get("videoId")
            if not video_id:
                continue
            item_id = f"youtube:{video_id}"
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            snippet = entry.get("snippet", {})
            title = snippet.get("title", "")
            description = snippet.get("description", "")
            if keyword.lower() not in title.lower() and keyword.lower() not in description.lower():
                continue
            channel = snippet.get("channelTitle", "")
            items.append({
                "id": item_id,
                "title": f"{title} ({channel})" if channel else title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "source": "youtube",
            })
    return items


if __name__ == "__main__":
    for item in collect():
        print(item)
