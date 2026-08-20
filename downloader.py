import os
import base64
import tempfile
from pathlib import Path

import yt_dlp


# ============================================================
# Configuration
# ============================================================

POT_PROVIDER_URL = os.getenv(
    "YOUTUBE_POT_PROVIDER_URL",
    ""
).strip().rstrip("/")


# ============================================================
# YouTube Cookies
# ============================================================

def create_cookie_file():
    cookies_b64 = os.getenv("YOUTUBE_COOKIES_B64")

    if not cookies_b64:
        print("⚠️ YOUTUBE_COOKIES_B64 تنظیم نشده است.")
        return None

    try:
        # حذف فاصله‌ها و خطوط خالی
        lines = cookies_b64.splitlines()
        clean_lines = []

        for line in lines:
            line = line.strip()

            if not line:
                continue

            # اگر مقدار با header/footer اضافی آمده باشد
            if line.startswith("-----"):
                continue

            clean_lines.append(line)

        encoded = "".join(clean_lines)

        cookie_data = base64.b64decode(
            encoded,
            validate=True
        )

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

    print(
        f"🍪 YouTube cookies loaded: "
        f"{len(cookie_data)} bytes"
    )

    return cookie_file


COOKIE_FILE = create_cookie_file()


# ============================================================
# PO Token Provider
# ============================================================

def configure_pot_provider(opts):
    """
    Configure bgutil-ytdlp-pot-provider.

    Railway example:

    YOUTUBE_POT_PROVIDER_URL=
    http://bgutil-ytdlp-pot-provider.railway.internal:4416
    """

    if not POT_PROVIDER_URL:
        print()
        print("=" * 70)
        print("⚠️ PO TOKEN PROVIDER")
        print("=" * 70)
        print(
            "YOUTUBE_POT_PROVIDER_URL تنظیم نشده است."
        )
        print(
            "PO Token Provider غیرفعال است."
        )
        print("=" * 70)
        print()

        return

    print()
    print("=" * 70)
    print("🔐 PO TOKEN PROVIDER")
    print("=" * 70)
    print(
        f"Provider URL: {POT_PROVIDER_URL}"
    )
    print(
        "Provider mode: automatic"
    )
    print("=" * 70)

    extractor_args = opts.setdefault(
        "extractor_args",
        {}
    )

    # bgutil HTTP provider
    #
    # معادل:
    #
    # --extractor-args
    # youtubepot-bgutilhttp:base_url=http://...
    #
    extractor_args[
        "youtubepot-bgutilhttp"
    ] = [
        f"base_url={POT_PROVIDER_URL}"
    ]


# ============================================================
# Base yt-dlp Options
# ============================================================

def get_ydl_opts():

    opts = {
        # ----------------------------------------------------
        # General
        # ----------------------------------------------------

        "quiet": False,

        "no_warnings": False,

        "noplaylist": True,

        "socket_timeout": 30,

        "retries": 5,

        "fragment_retries": 5,

        "file_access_retries": 3,

        "continuedl": True,

        "overwrites": True,

        # ----------------------------------------------------
        # Fragment downloads
        # ----------------------------------------------------

        "concurrent_fragment_downloads": 4,

        # ----------------------------------------------------
        # JavaScript runtime
        # ----------------------------------------------------

        "js_runtimes": {
            "deno": {}
        },

        # ----------------------------------------------------
        # Remote EJS components
        # ----------------------------------------------------

        "remote_components": [
            "ejs:github"
        ],

        # ----------------------------------------------------
        # YouTube clients
        #
        # web اصلی است.
        # mweb به عنوان fallback استفاده می‌شود.
        # ----------------------------------------------------

        "extractor_args": {
            "youtube": [
                "player_client=web,mweb"
            ]
        }
    }

    # ========================================================
    # Cookies
    # ========================================================

    if COOKIE_FILE:
        opts["cookiefile"] = COOKIE_FILE

    # ========================================================
    # PO Token Provider
    # ========================================================

    configure_pot_provider(opts)

    return opts


# ============================================================
# Print Available Formats
# ============================================================

def print_formats(info):

    print()
    print("=" * 70)
    print("AVAILABLE YOUTUBE FORMATS")
    print("=" * 70)

    formats = info.get(
        "formats",
        []
    )

    if not formats:
        print(
            "⚠️ No formats returned by YouTube."
        )
        print("=" * 70)
        return

    for f in formats:

        print(
            f"format_id={f.get('format_id')} | "
            f"height={f.get('height')} | "
            f"width={f.get('width')} | "
            f"ext={f.get('ext')} | "
            f"vcodec={f.get('vcodec')} | "
            f"acodec={f.get('acodec')} | "
            f"fps={f.get('fps')} | "
            f"filesize={f.get('filesize')} | "
            f"protocol={f.get('protocol')}"
        )

    print("=" * 70)


# ============================================================
# Format Score
# ============================================================

def format_score(fmt):

    score = 0

    # MP4 اولویت دارد
    if fmt.get("ext") == "mp4":
        score += 100

    # Video
    if fmt.get("vcodec") not in (
        None,
        "none"
    ):
        score += 50

    # Audio
    if fmt.get("acodec") not in (
        None,
        "none"
    ):
        score += 50

    # FPS
    fps = fmt.get("fps")

    if fps:
        try:
            score += min(
                int(float(fps)),
                60
            )
        except Exception:
            pass

    # Bitrate
    try:
        score += int(
            float(fmt.get("tbr") or 0)
        )
    except Exception:
        pass

    return score


# ============================================================
# Extract Available Qualities
# ============================================================

def extract_qualities(info):

    qualities = {}

    for fmt in info.get(
        "formats",
        []
    ):

        height = fmt.get("height")

        width = fmt.get("width")

        ext = fmt.get("ext")

        vcodec = fmt.get("vcodec")

        # بدون height
        if not height:
            continue

        # تبدیل امن
        try:
            height = int(height)
        except Exception:
            continue

        # کیفیت‌های خیلی پایین
        if height < 144:
            continue

        # فقط audio
        if not vcodec or vcodec == "none":
            continue

        # thumbnail / storyboard
        if ext == "mhtml":
            continue

        current = qualities.get(height)

        if current is None:
            qualities[height] = fmt
            continue

        if format_score(fmt) > format_score(current):
            qualities[height] = fmt

    return dict(
        sorted(
            qualities.items(),
            key=lambda item: item[0],
            reverse=True
        )
    )


# ============================================================
# Get Video Information
# ============================================================

def get_video_data(url):

    print()
    print("🔎 Extracting video information...")

    ydl_opts = get_ydl_opts()

    ydl_opts["skip_download"] = True

    with yt_dlp.YoutubeDL(
        ydl_opts
    ) as ydl:

        info = ydl.extract_info(
            url,
            download=False
        )

    if not info:
        raise RuntimeError(
            "❌ اطلاعات ویدیو دریافت نشد."
        )

    print_formats(info)

    # ========================================================
    # Video Information
    # ========================================================

    video_info = {
        "title": (
            info.get("title")
            or "نامشخص"
        ),

        "channel": (
            info.get("channel")
            or info.get("uploader")
            or "نامشخص"
        ),

        "views": (
            info.get("view_count")
            or 0
        ),

        "likes": (
            info.get("like_count")
            or 0
        ),

        "duration": (
            info.get("duration")
            or 0
        ),

        "thumbnail": (
            info.get("thumbnail")
            or ""
        ),

        "webpage_url": (
            info.get("webpage_url")
            or url
        ),

        "video_id": (
            info.get("id")
            or ""
        )
    }

    # ========================================================
    # Extract Qualities
    # ========================================================

    qualities = extract_qualities(info)

    available_qualities = [
        str(height)
        for height in qualities.keys()
    ]

    print()
    print(
        "🎥 AVAILABLE QUALITIES:",
        available_qualities
    )
    print()

    return (
        video_info,
        available_qualities
    )


# ============================================================
# Build Format Selector
# ============================================================

def build_format_selector(quality):

    quality = int(quality)

    # اولویت:
    #
    # 1. بهترین video تا کیفیت انتخابی
    # 2. بهترین audio
    # 3. fallback به format دارای video+audio
    #
    # این باعث می‌شود اگر مثلاً 720p جداگانه
    # موجود باشد، فقط به
