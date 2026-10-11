import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

MAILPIT = os.getenv("MAILPIT_BASE_URL", "http://mailpit:8025").rstrip("/")
OUTPUT = "/out/email_confirmation_links.txt"
POLL_SECONDS = max(1, int(os.getenv("POLL_SECONDS", "2")))
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def get_json(path: str):
    request = urllib.request.Request(f"{MAILPIT}{path}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


def message_text(message: dict) -> str:
    parts = [message.get("Text", ""), message.get("HTML", ""), message.get("Snippet", "")]
    return html.unescape("\n".join(str(part) for part in parts))


def confirmation_links(message: dict):
    links = []
    for raw in URL_RE.findall(message_text(message)):
        link = raw.rstrip(".,);]}")
        lowered = link.lower()
        if "login-actions/action-token" in lowered or "verify" in lowered or "verification" in lowered:
            if link not in links:
                links.append(link)
    return links


def load_seen():
    try:
        with open(OUTPUT, "r", encoding="utf-8") as file:
            return {line.split("\t", 1)[0] for line in file if line.strip()}
    except FileNotFoundError:
        return set()


def append_message(message_id: str, message: dict):
    links = confirmation_links(message)
    if not links:
        return
    sender = (message.get("From") or {}).get("Address", "")
    recipients = ", ".join(item.get("Address", "") for item in (message.get("To") or []) if item.get("Address"))
    timestamp = message.get("Created") or datetime.now(timezone.utc).isoformat()
    with open(OUTPUT, "a", encoding="utf-8") as file:
        for link in links:
            file.write(f"{message_id}\t{timestamp}\t{recipients or sender}\t{link}\n")


def main():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    seen = load_seen()
    while True:
        try:
            listing = get_json("/api/v1/messages?limit=100")
            for item in listing.get("messages", []):
                message_id = item.get("ID") or item.get("id")
                if not message_id or message_id in seen:
                    continue
                message = get_json(f"/api/v1/message/{urllib.parse.quote(message_id, safe='')}")
                append_message(message_id, message)
                seen.add(message_id)
        except Exception as error:
            print(f"mailpit link writer: {error}", flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
