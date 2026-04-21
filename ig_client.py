import logging
import re

import instaloader

from config import Config

log = logging.getLogger(__name__)


class IGClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._userid_cache: dict[str, int] = {}
        self._loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            # suppress creating per-post directories
            dirname_pattern="/tmp",
        )

    def login(self) -> None:
        session_file = str(self._config.session_file_path)
        try:
            self._loader.load_session_from_file(
                self._config.ig_username, session_file
            )
            log.info("Loaded existing Instagram session from file.")
        except FileNotFoundError:
            log.info("No session file found — logging in with credentials.")
            self._full_login()
        except instaloader.exceptions.BadCredentialsException:
            log.warning("Saved session invalid — re-authenticating.")
            self._full_login()

    def _full_login(self) -> None:
        try:
            self._loader.login(self._config.ig_username, self._config.ig_password)
        except instaloader.exceptions.LoginException as exc:
            self._handle_checkpoint(exc)
        self._loader.save_session_to_file(str(self._config.session_file_path))
        log.info("Login successful — session saved.")

    def _handle_checkpoint(self, exc: Exception) -> None:
        msg = str(exc)
        match = re.search(r"(/auth_platform/\S+)", msg)
        if match:
            url = f"https://www.instagram.com{match.group(1)}"
            print(
                "\n*** Instagram checkpoint required ***\n"
                "Open the URL below in a browser while logged in as your burner account,\n"
                "complete the verification, then press Enter to retry login.\n\n"
                f"  {url}\n"
            )
            input("Press Enter once you have completed the verification...")
            self._reset_loader()
            self._loader.login(self._config.ig_username, self._config.ig_password)
        else:
            raise

    def _reset_loader(self) -> None:
        self._userid_cache.clear()
        self._loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            dirname_pattern="/tmp",
        )

    def refresh_session(self) -> None:
        log.info("Refreshing Instagram session.")
        self._userid_cache.clear()
        self._full_login()

    def get_stories(self, username: str) -> list[instaloader.StoryItem]:
        userid = self._get_userid(username)
        stories = list(self._loader.get_stories(userids=[userid]))
        items: list[instaloader.StoryItem] = []
        for story in stories:
            items.extend(story.get_items())
        log.debug("Fetched %d story items from @%s.", len(items), username)
        return items

    def _get_userid(self, username: str) -> int:
        if self._userid_cache.get(username) is None:
            profile = instaloader.Profile.from_username(self._loader.context, username)
            self._userid_cache[username] = profile.userid
            log.debug("Resolved @%s → userid %d (cached).", username, profile.userid)
        return self._userid_cache[username]
