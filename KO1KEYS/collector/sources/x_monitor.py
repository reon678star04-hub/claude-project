"""KO1KEYSキーワードでXを検索し、注目度の高い投稿を抽出する。

twikit（作業用Xアカウントのログイン状態を使った非公式クライアント）を使用する。
X公式APIの無料プランは検索/読み取りができないため、無料で実現するための代替手段。
X側の規約上は非公式な利用にあたり、使用するアカウントが凍結・制限されるリスクがある点は
作業用の別アカウントを使うことで本アカウントへの影響を避ける前提で運用する。
"""
import os
import asyncio
from twikit import Client

COOKIES_PATH = os.path.join(os.path.dirname(__file__), "..", "x_cookies.json")


async def _login(client: Client):
    username = os.environ.get("X_USERNAME")
    email = os.environ.get("X_EMAIL")
    password = os.environ.get("X_PASSWORD")
    if not all([username, email, password]):
        raise RuntimeError("X_USERNAME / X_EMAIL / X_PASSWORD が設定されていません")

    if os.path.exists(COOKIES_PATH):
        client.load_cookies(COOKIES_PATH)
        return

    await client.login(auth_info_1=username, auth_info_2=email, password=password)
    client.save_cookies(COOKIES_PATH)


async def _search(keyword: str, limit: int):
    client = Client("ja-JP")
    await _login(client)
    tweets = await client.search_tweet(keyword, "Latest", count=limit)
    return tweets


def fetch_posts(keyword: str, limit: int = 100):
    return asyncio.run(_search(keyword, limit))


def filter_by_engagement(posts, min_likes: int, min_retweets: int):
    filtered = [p for p in posts if (p.favorite_count or 0) >= min_likes or (p.retweet_count or 0) >= min_retweets]
    filtered.sort(key=lambda p: (p.favorite_count or 0) + (p.retweet_count or 0), reverse=True)
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
            item_id = f"x:{p.id}"
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            items.append({
                "id": item_id,
                "title": (p.text or "")[:120],
                "url": f"https://x.com/{p.user.screen_name}/status/{p.id}",
                "likes": p.favorite_count or 0,
                "retweets": p.retweet_count or 0,
                "source": "x",
            })
    return items


if __name__ == "__main__":
    for item in collect():
        print(item)
