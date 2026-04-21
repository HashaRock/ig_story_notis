import logging

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
        self._loader.login(self._config.ig_username, self._config.ig_password)
        self._loader.save_session_to_file(str(self._config.session_file_path))
        log.info("Login successful — session saved.")

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
