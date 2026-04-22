import logging
import time

import instaloader
import requests

from config import Config
from discord_notifier import DiscordNotifier
from ig_client import IGClient
from state_manager import StateManager

log = logging.getLogger(__name__)


def run_poll_loop(
    ig: IGClient,
    notifier: DiscordNotifier,
    state: StateManager,
    config: Config,
) -> None:
    log.info(
        "Polling @%s every %ds. Press Ctrl+C to stop.",
        config.ig_target_account,
        config.poll_interval_seconds,
    )
    while True:
        try:
            stories = ig.get_stories(config.ig_target_account)
            for item in stories:
                if not state.is_seen(item.mediaid):
                    notifier.send_story_notification(item, config.ig_target_account)
                    state.mark_seen(item.mediaid)
                    log.info("Notified: story %s.", item.mediaid)
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 429:
                log.warning("Instagram rate limit hit — backing off 10 minutes.")
                time.sleep(600)
                continue
            log.error("HTTP error in poll cycle: %s", exc, exc_info=True)
        except instaloader.exceptions.LoginRequiredException:
            log.warning("Instagram session expired — refreshing.")
            try:
                ig.refresh_session()
            except Exception as exc:
                log.error("Session refresh failed: %s — will retry next poll.", exc)
        except KeyboardInterrupt:
            log.info("Shutting down.")
            return
        except Exception as exc:
            log.error("Unexpected error in poll cycle: %s", exc, exc_info=True)

        time.sleep(config.poll_interval_seconds)
