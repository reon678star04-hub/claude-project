"""LINE Messaging APIでBot自身からユーザーへpush通知する（LINE Notifyは廃止済みのため代替）。"""
import os
import requests

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def send(text: str):
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    if not token or not user_id:
        print("[line] skipped: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID not set")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": text[:5000]}],
    }
    resp = requests.post(LINE_PUSH_URL, headers=headers, json=payload, timeout=10)
    resp.raise_for_status()
