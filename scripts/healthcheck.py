import importlib
import os
import shutil
import sys


REQUIRED_MODULES = (
    "telebot",
    "yt_dlp",
    "boto3",
)

REQUIRED_ENV = (
    "BOT_TOKEN",
    "FILONE_ACCESS_KEY",
    "FILONE_SECRET_KEY",
    "FILONE_BUCKET",
    "FILONE_ENDPOINT",
)


def check_command(name: str) -> None:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required command not found: {name}")
    print(f"OK command: {name} -> {path}")


def check_module(name: str) -> None:
    importlib.import_module(name)
    print(f"OK Python module: {name}")


def main() -> int:
    print(f"Python: {sys.version.split()[0]}")

    for command in ("ffmpeg", "node"):
        check_command(command)

    for module in REQUIRED_MODULES:
        check_module(module)

    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    if missing:
        print("WARN missing environment variables:")
        for name in missing:
            print(f"  - {name}")
        print("The runtime dependencies are healthy, but bot.py cannot start until these variables are supplied.")
    else:
        print("OK required bot environment variables are present")

    if not os.getenv("YOUTUBE_COOKIES_B64"):
        print("WARN YOUTUBE_COOKIES_B64 is not set; YouTube access may fail for protected requests.")

    if not os.getenv("YOUTUBE_POT_PROVIDER_URL"):
        print("WARN YOUTUBE_POT_PROVIDER_URL is not set; requests requiring the configured POT provider may fail.")

    print("Health check completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
