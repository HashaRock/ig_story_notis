import logging
import sys

from config import Config
from discord_notifier import DiscordNotifier
from ig_client import IGClient
from poller import run_poll_loop
from state_manager import StateManager


def main() -> None:
    try:
        config = Config.load()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    state = StateManager(config.state_file_path)
    ig = IGClient(config)
    ig.login()
    notifier = DiscordNotifier(config.discord_webhook_url)

    run_poll_loop(ig, notifier, state, config)


if __name__ == "__main__":
    main()
