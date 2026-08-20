
import os
import base64
import tempfile
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

def configure_pot_provider(opts):
    """
    اتصال yt-dlp به bgutil-ytdlp-pot-provider

    نکته مهم:
    base_url باید به extractor مربوط به bgutil
    داده شود؛ صرفاً گذاشتن URL در یک env variable
    برای yt-dlp کافی نیست.
    """

    if not POT_PROVIDER_URL:
        print()
        print("=" * 70)
        print("⚠️ PO TOKEN PROVIDER")
        print("=" * 70)
        print("YOUTUBE_POT_PROVIDER_URL تنظیم نشده است.")
        print("yt-dlp از provider پیش‌فرض استفاده خواهد کرد.")
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
    print("Provider mode: automatic")
    print("=" * 70)

    extractor_args = opts.setdefault(
        "extractor_args",
        {}
    )

    # --------------------------------------------------------
    # YouTube
    # --------------------------------------------------------

    youtube_args = extractor_args.setdefault(
        "youtube",
        {}
    )

    # --------------------------------------------------------
    # bgutil HTTP provider
    #
    # این بخش مهم‌ترین قسمت است.
    # --------------------------------------------------------

    bgutil_args = extractor_args.setdefault(
        "youtubepot-bgutilhttp",
        {}
    )

    bgutil_args["base_url"] = POT_PROVIDER_URL


# ============================================================
# yt-dlp Options
# ============================================================

def get_ydl_opts():

    opts = {

        "quiet": False,

        "no_warnings": False,

        "noplaylist": True,

        "socket_timeout": 30,

        "retries": 5,

        "fragment_retries": 5,

        "file_access_retries": 3,

        "concurrent_fragment_downloads": 4,

        # ----------------------------------------------------
        # JavaScript runtime
        # ----------------------------------------------------

        "js_runtimes": {
            "deno": {}
        },

        # ----------------------------------------------------
        # Remote EJS components
        #
        # برای حل n challenge
        # ----------------------------------------------------

        "remote_components": [
            "ejs:github"
        ],

        # ----------------------------------------------------
        # YouTube client
        #
        # فعلاً web را client اصلی قرار می‌دهیم.
        #
        # اجبار mweb در شرایط فعلی تو باعث می‌شد
        # فرمت‌های ویدیو حذف شوند.
        # ----------------------------------------------------

        "extractor_args": {

            "youtube": {

                "player_client": [
                    "web"
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
# Print Formats
# ============================================================

def print_formats(info):

    print()
    print("=" * 70)
    print("AVAILABLE YOUTUBE FORMATS")
    print("=" * 70)

    formats = info.get("formats", [])

    if not formats:
        print("❌ No formats returned.")
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
    # Find available video qualities
    # ========================================================

    qualities = {}

    for f in info.get("formats", []):

        height = f.get("height")

        if not height:
            continue

        try:
            height = int(height)
        except (TypeError, ValueError):
            continue

        # ----------------------------------------------------
        # Ignore extremely low formats
        # ----------------------------------------------------

        if height < 144:
            continue

        # ----------------------------------------------------
        # Ignore audio-only
        # ----------------------------------------------------

        vcodec = f.get("vcodec")

        if not vcodec or vcodec == "none":
            continue

        # ----------------------------------------------------
        # Ignore thumbnails / mhtml
        # ----------------------------------------------------

        if f.get("ext") == "mhtml":
            continue

        # ----------------------------------------------------
        # Score format
        # ----------------------------------------------------

        score = 0

        if f.get("ext") == "mp4":
            score += 100

        if f.get("acodec") not in (
            None,
            "none"
        ):
            score += 50

        if f.get("vcodec") not in (
            None,
            "none"
        ):
            score += 50

        score += int(
            f.get("tbr") or 0
        )

        current = qualities.get(height)

        if current is None:

            qualities[height] = {
                "format": f,
                "score": score
            }

        elif score > current["score"]:

            qualities[height] = {
                "format": f,
                "score": score
            }

    # ========================================================
    # Sort
    # ========================================================

    sorted_heights = sorted(
        qualities.keys(),
        reverse=True
    )

    available_qualities = [
        str(height)
        for height in sorted_heights
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
    # Format selection
    #
    # اول:
    # بهترین video + audio
    #
    # اگر جداگانه موجود نبود:
    # بهترین فایل دارای video و audio
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

        filename = ydl.prepare_filename(
            info
        )

        base, ext = os.path.splitext(
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

