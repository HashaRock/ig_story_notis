import logging
import time

import instaloader
import requests

log = logging.getLogger(__name__)

_IG_PINK = 0xE1306C


class DiscordNotifier:
    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url
        self._session = requests.Session()

    def send_story_notification(
        self, item: instaloader.StoryItem, target_username: str
    ) -> None:
        story_url = (
            f"https://www.instagram.com/stories/{target_username}/{item.mediaid}/"
        )
        embed: dict = {
            "title": f"New story from @{target_username}",
            "url": story_url,
            "color": _IG_PINK,
            "timestamp": item.date_utc.isoformat(),
            "footer": {"text": "Instagram Stories • link requires IG login"},
        }

        if item.is_video:
            embed["description"] = f"[Watch video]({item.video_url})"
            payload = {"content": item.video_url, "embeds": [embed]}
        else:
            embed["image"] = {"url": item.url}
            payload = {"embeds": [embed]}

        self._send_with_retry(payload)

    def _send_with_retry(self, payload: dict) -> None:
        delays = [1, 2, 4]
        for attempt, delay in enumerate(delays, start=1):
            try:
                resp = self._session.post(self._webhook_url, json=payload, timeout=10)
                if resp.status_code in (200, 204):
                    return
                if resp.status_code == 429 or resp.status_code >= 500:
                    log.warning(
                        "Discord webhook returned %d (attempt %d/%d) — retrying in %ds.",
                        resp.status_code, attempt, len(delays), delay,
                    )
                    time.sleep(delay)
                else:
                    log.error("Discord webhook error %d: %s", resp.status_code, resp.text)
                    return
            except requests.RequestException as exc:
                log.warning("Discord request failed (attempt %d/%d): %s", attempt, len(delays), exc)
                time.sleep(delay)
        log.error("Discord notification failed after %d attempts — skipping.", len(delays))
