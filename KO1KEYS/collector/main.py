"""KO1KEYS情報収集→新着判定→通知 を1回実行するエントリポイント。"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv

from sources import web_news
from notify import line

BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = BASE_DIR / "state.json"
JST = timezone(timedelta(hours=9))
QUIET_HOURS_START = 23  # 23:00
QUIET_HOURS_END = 7  # 7:00

load_dotenv(BASE_DIR / ".env")


def is_quiet_hours(now=None):
    hour = (now or datetime.now(JST)).hour
    return hour >= QUIET_HOURS_START or hour < QUIET_HOURS_END


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"seen_ids": []}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_all():
    items = []
    try:
        items.extend(web_news.collect())
    except Exception as e:
        print(f"[main] web_news failed: {e}")
    return items


def format_item(item):
    lines = [f"[{item['source']}] {item['title']}"]
    if item.get("url"):
        lines.append(item["url"])
    return "\n".join(lines)


def main():
    state = load_state()
    seen = set(state.get("seen_ids", []))

    items = collect_all()
    new_items = [i for i in items if i["id"] not in seen]

    if not new_items:
        print("新着情報なし")
        return

    if is_quiet_hours():
        print(f"静音時間帯(23:00-7:00 JST)のため通知を見送り: {len(new_items)}件は次回に持ち越し")
        return

    body = "\n\n".join(format_item(i) for i in new_items)
    text = f"KO1KEYS 新着情報 ({len(new_items)}件)\n\n{body}"

    line.send(text)

    seen.update(i["id"] for i in new_items)
    state["seen_ids"] = list(seen)
    save_state(state)
    print(f"通知済み: {len(new_items)}件")


if __name__ == "__main__":
    main()
