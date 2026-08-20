
import os
import base64
import tempfile
import yt_dlp


YOUTUBE_CLIENT = {
    "youtube": {
        "player_client": ["android_vr"]
    }
}


def create_cookie_file():
    cookies_b64 = os.getenv("YOUTUBE_COOKIES_B64")

    if not cookies_b64:
        return None

    # حذف هدر/فوتر certutil در صورت وجود
    lines = cookies_b64.splitlines()

    clean_lines = []

    for line in lines:
        if not line.startswith("-----"):
            clean_lines.append(line.strip())

    encoded = "".join(clean_lines)

    try:
        cookie_data = base64.b64decode(encoded)
    except Exception as e:
        raise RuntimeError(
            f"YOUTUBE_COOKIES_B64 نامعتبر است: {e}"
        )

    cookie_file = os.path.join(
        tempfile.gettempdir(),
        "youtube_cookies.txt"
    )

    with open(cookie_file, "wb") as f:
        f.write(cookie_data)

    return cookie_file


COOKIE_FILE = create_cookie_file()


def get_video_data(url):

    ydl_opts = {
        "quiet": False,
        "no_warnings": False,
        "noplaylist": True,

        "extractor_args": YOUTUBE_CLIENT,

        "socket_timeout": 30,
        "retries": 3,
    }

    if COOKIE_FILE:
        ydl_opts["cookiefile"] = COOKIE_FILE

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            url,
            download=False
        )

        video_info = {
            "title": info.get("title") or "نامشخص",
            "channel": (
                info.get("channel")
                or info.get("uploader")
                or "نامشخص"
            ),
            "views": info.get("view_count") or 0,
            "likes": info.get("like_count") or 0,
            "duration": info.get("duration") or 0,
        }

        qualities = {}

        for f in info.get("formats", []):

            height = f.get("height")

            if (
                height
                and f.get("ext") == "mp4"
                and f.get("url")
            ):
                qualities[str(height)] = f["url"]

        qualities = dict(
            sorted(
                qualities.items(),
                key=lambda x: int(x[0]),
                reverse=True
            )
        )

        return video_info, qualities


def download_video(url, quality):

    output_dir = "/tmp/youtube_downloads"

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    output_template = os.path.join(
        output_dir,
        "%(id)s.%(ext)s"
    )

    ydl_opts = {
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,

        "extractor_args": YOUTUBE_CLIENT,

        "socket_timeout": 30,
        "retries": 3,

        "format": (
            f"bestvideo[height<={quality}]"
            f"+bestaudio/"
            f"best[height<={quality}]"
        ),

        "outtmpl": output_template,

        "merge_output_format": "mp4",
    }

    if COOKIE_FILE:
        ydl_opts["cookiefile"] = COOKIE_FILE

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            url,
            download=True
        )

        filename = ydl.prepare_filename(info)

        base, _ = os.path.splitext(filename)

        mp4_file = base + ".mp4"

        if os.path.exists(mp4_file):
            return mp4_file

        return filename

