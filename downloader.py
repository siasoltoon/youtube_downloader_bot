
import os
import base64
import tempfile
import yt_dlp


# ============================================================
# YouTube Cookies
# ============================================================

def create_cookie_file():
    cookies_b64 = os.getenv("YOUTUBE_COOKIES_B64")

    if not cookies_b64:
        print("⚠️ YOUTUBE_COOKIES_B64 تنظیم نشده است.")
        return None

    try:
        lines = cookies_b64.splitlines()

        clean_lines = []

        for line in lines:
            line = line.strip()

            if not line:
                continue

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

POT_PROVIDER_URL = os.getenv(
    "YOUTUBE_POT_PROVIDER_URL"
)


def configure_pot_provider(opts):
    """
    تنظیم bgutil-ytdlp-pot-provider
    از طریق Variable در Railway.
    """

    if not POT_PROVIDER_URL:
        print()
        print("=" * 70)
        print("⚠️ PO TOKEN PROVIDER")
        print("=" * 70)
        print("YOUTUBE_POT_PROVIDER_URL تنظیم نشده است.")
        print("=" * 70)
        return

    provider_url = POT_PROVIDER_URL.strip().rstrip("/")

    # جلوگیری از اشتباه رایج
    if "127.0.0.1" in provider_url:
        print()
        print("=" * 70)
        print("⚠️ WARNING: PO provider روی 127.0.0.1 تنظیم شده!")
        print("=" * 70)
        print(
            "YOUTUBE_POT_PROVIDER_URL باید Private Domain "
            "سرویس bgutil باشد."
        )
        print("=" * 70)

    print()
    print("=" * 70)
    print("🔐 PO TOKEN PROVIDER")
    print("=" * 70)
    print(f"Provider URL: {provider_url}")
    print("Provider mode: automatic")
    print("=" * 70)

    youtube_args = opts.setdefault(
        "extractor_args",
        {}
    ).setdefault(
        "youtube",
        {}
    )

    youtube_args["pot_provider"] = [
        f"bgutil:{provider_url}"
    ]


# ============================================================
# yt-dlp Options
# ============================================================

def get_ydl_opts():

    opts = {

        "quiet": False,

        "no_warnings": False,

        "noplaylist": True,

        "socket_timeout": 30,

        "retries": 3,

        "fragment_retries": 5,

        "concurrent_fragment_downloads": 4,

        # ----------------------------------------------------
        # JavaScript runtime
        # ----------------------------------------------------

        "js_runtimes": {
            "deno": {}
        },

        # ----------------------------------------------------
        # EJS remote components
        #
        # برای حل challengeهای جدید YouTube
        # ----------------------------------------------------

        "remote_components": {
            "ejs": [
                "github"
            ]
        },

        # ----------------------------------------------------
        # YouTube clients
        # ----------------------------------------------------

        "extractor_args": {

            "youtube": {

                "player_client": [
                    "web",
                    "mweb"
                ]
            }
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

    formats = info.get("formats", [])

    for f in formats:

        format_id = f.get("format_id")

        height = f.get("height")

        width = f.get("width")

        ext = f.get("ext")

        vcodec = f.get("vcodec")

        acodec = f.get("acodec")

        fps = f.get("fps")

        filesize = f.get("filesize")

        protocol = f.get("protocol")

        print(
            f"format_id={format_id} | "
            f"height={height} | "
            f"width={width} | "
            f"ext={ext} | "
            f"vcodec={vcodec} | "
            f"acodec={acodec} | "
            f"fps={fps} | "
            f"filesize={filesize} | "
            f"protocol={protocol}"
        )

    print("=" * 70)


# ============================================================
# Get Video Data
# ============================================================

def get_video_data(url):

    print()
    print("🔎 Extracting video information...")

    ydl_opts = get_ydl_opts()

    ydl_opts["skip_download"] = True

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            url,
            download=False
        )

    print_formats(info)

    # ========================================================
    # Video information
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
        )
    }

    # ========================================================
    # Find available real video qualities
    # ========================================================

    qualities = {}

    for f in info.get("formats", []):

        height = f.get("height")

        ext = f.get("ext")

        vcodec = f.get("vcodec")

        acodec = f.get("acodec")

        if not height:
            continue

        try:
            height = int(height)
        except (TypeError, ValueError):
            continue

        # فقط Video
        if not vcodec or vcodec == "none":
            continue

        # Thumbnail / storyboard
        if ext == "mhtml":
            continue

        # کیفیت‌های خیلی پایین
        if height < 144:
            continue

        current = qualities.get(height)

        if current is None:
            qualities[height] = f
            continue

        # ----------------------------------------------------
        # Score
        # ----------------------------------------------------

        def score(fmt):

            score_value = 0

            # MP4 اولویت دارد
            if fmt.get("ext") == "mp4":
                score_value += 100

            # دارای صدا
            if fmt.get("acodec") not in (
                None,
                "none"
            ):
                score_value += 50

            # دارای تصویر
            if fmt.get("vcodec") not in (
                None,
                "none"
            ):
                score_value += 50

            # bitrate
            score_value += int(
                fmt.get("tbr") or 0
            )

            return score_value

        if score(f) > score(current):
            qualities[height] = f

    # ========================================================
    # Sort qualities
    # ========================================================

    qualities = dict(
        sorted(
            qualities.items(),
            key=lambda item: item[0],
            reverse=True
        )
    )

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

    return video_info, available_qualities


# ============================================================
# Download Video
# ============================================================

def download_video(url, quality):

    quality = int(quality)

    print()
    print("=" * 70)
    print(
        f"🎯 Requested quality: {quality}p"
    )
    print("=" * 70)

    output_dir = "/tmp/youtube_downloads"

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    output_template = os.path.join(
        output_dir,
        "%(id)s.%(ext)s"
    )

    ydl_opts = get_ydl_opts()

    # ========================================================
    # Format selector
    # ========================================================

    format_selector = (
        f"bestvideo[height<={quality}]"
        f"+bestaudio/"
        f"best[height<={quality}]"
    )

    print(
        "🎯 Format selector:",
        format_selector
    )

    ydl_opts.update({

        "format": format_selector,

        "outtmpl": output_template,

        "merge_output_format": "mp4",

        "paths": {
            "home": output_dir,
            "temp": output_dir
        },

        "overwrites": True,

        "noplaylist": True
    })

    # ========================================================
    # Download
    # ========================================================

    print(
        f"⬇️ Downloading {quality}p..."
    )

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            url,
            download=True
        )

        filename = ydl.prepare_filename(info)

        base, _ = os.path.splitext(
            filename
        )

        mp4_file = base + ".mp4"

        # ----------------------------------------------------
        # MP4
        # ----------------------------------------------------

        if os.path.exists(mp4_file):

            print(
                f"✅ Download completed: "
                f"{mp4_file}"
            )

            return mp4_file

        # ----------------------------------------------------
        # Original file
        # ----------------------------------------------------

        if os.path.exists(filename):

            print(
                f"✅ Download completed: "
                f"{filename}"
            )

            return filename

    raise FileNotFoundError(
        "❌ فایل ویدیو بعد از دانلود پیدا نشد."
    )

