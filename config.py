import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    ig_username: str
    ig_password: str
    ig_target_account: str
    ig_target_userid: int | None
    discord_webhook_url: str
    poll_interval_seconds: int
    data_dir: Path
    log_level: str
    session_file_path: Path
    state_file_path: Path

    @classmethod
    def load(cls) -> "Config":
        missing = [
            var for var in ("IG_USERNAME", "IG_PASSWORD", "DISCORD_WEBHOOK_URL")
            if not os.getenv(var)
        ]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        data_dir = Path(os.getenv("DATA_DIR", "./data"))
        data_dir.mkdir(parents=True, exist_ok=True)

        raw_userid = os.getenv("IG_TARGET_USERID")

        return cls(
            ig_username=os.environ["IG_USERNAME"],
            ig_password=os.environ["IG_PASSWORD"],
            ig_target_account=os.getenv("IG_TARGET_ACCOUNT", "zero2sudo"),
            ig_target_userid=int(raw_userid) if raw_userid else None,
            discord_webhook_url=os.environ["DISCORD_WEBHOOK_URL"],
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "120")),
            data_dir=data_dir,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            session_file_path=data_dir / "ig_session",
            state_file_path=data_dir / "seen_stories.json",
        )
