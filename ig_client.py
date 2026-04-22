import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import instaloader

from config import Config

log = logging.getLogger(__name__)

_MOBILE_UA = (
    "Instagram 219.0.0.12.117 Android "
    "(28/9; 411dpi; 1080x2220; Xiaomi; Redmi Note 7; lavender; qcom; en_US; 190811114)"
)
_APP_ID = "936619743392459"


@dataclass
class StoryItem:
    mediaid: int
    is_video: bool
    url: str
    video_url: str | None
    date_utc: datetime


class IGClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._userid_cache: dict[str, int] = (
            {config.ig_target_account: config.ig_target_userid}
            if config.ig_target_userid else {}
        )
        self._loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
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
        if self._config.ig_target_userid:
            self._userid_cache[self._config.ig_target_account] = self._config.ig_target_userid
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

    def get_stories(self, username: str) -> list[StoryItem]:
        userid = self._get_userid(username)
        resp = self._loader.context._session.get(
            f"https://i.instagram.com/api/v1/feed/reels_media/?reel_ids={userid}",
            headers={"User-Agent": _MOBILE_UA, "x-ig-app-id": _APP_ID},
        )
        resp.raise_for_status()
        data = resp.json()

        items: list[StoryItem] = []
        for reel in data.get("reels_media", []):
            for raw in reel.get("items", []):
                is_video = raw.get("media_type") == 2
                image_url = raw["image_versions2"]["candidates"][0]["url"]
                video_url = raw["video_versions"][0]["url"] if is_video else None
                items.append(StoryItem(
                    mediaid=int(raw["pk"]),
                    is_video=is_video,
                    url=image_url,
                    video_url=video_url,
                    date_utc=datetime.fromtimestamp(raw["taken_at"], tz=timezone.utc),
                ))

        log.debug("Fetched %d story items from @%s.", len(items), username)
        return items

    def _get_userid(self, username: str) -> int:
        if self._userid_cache.get(username) is None:
            profile = instaloader.Profile.from_username(self._loader.context, username)
            self._userid_cache[username] = profile.userid
            log.debug("Resolved @%s → userid %d (cached).", username, profile.userid)
        return self._userid_cache[username]
