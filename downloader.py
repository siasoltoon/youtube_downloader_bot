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
# PO Token Configuration
# ============================================================

WEB_GVS_PO_TOKEN = os.getenv(
    "YOUTUBE_WEB_GVS_PO_TOKEN"
)

MWEB_GVS_PO_TOKEN = os.getenv(
    "YOUTUBE_MWEB_GVS_PO_TOKEN"
)

WEB_PLAYER_PO_TOKEN = os.getenv(
    "YOUTUBE_WEB_PLAYER_PO_TOKEN"
)

MWEB_PLAYER_PO_TOKEN = os.getenv(
    "YOUTUBE_MWEB_PLAYER_PO_TOKEN"
)


# ============================================================
# Build PO Token Arguments
# ============================================================

def build_po_token_args():

    tokens = []

    # --------------------------------------------------------
    # WEB GVS
    # --------------------------------------------------------

    if WEB_GVS_PO_TOKEN:

        tokens.append(
            f"web.gvs+{WEB_GVS_PO_TOKEN}"
        )

    # --------------------------------------------------------
    # MWEB GVS
    # --------------------------------------------------------

    if MWEB_GVS_PO_TOKEN:

        tokens.append(
            f"mweb.gvs+{MWEB_GVS_PO_TOKEN}"
        )

    # --------------------------------------------------------
    # WEB PLAYER
    # --------------------------------------------------------

    if WEB_PLAYER_PO_TOKEN:

        tokens.append(
            f"web.player+{WEB_PLAYER_PO_TOKEN}"
        )

    # --------------------------------------------------------
    # MWEB PLAYER
    # --------------------------------------------------------

    if MWEB_PLAYER_PO_TOKEN:

        tokens.append(
            f"mweb.player+{MWEB_PLAYER_PO_TOKEN}"
        )

    return tokens


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

        "fragment_retries": 3,

        "concurrent_fragment_downloads": 4,

        # ----------------------------------------------------
        # Deno
        # ----------------------------------------------------

        "js_runtimes": {
            "deno": {}
        },

        # ----------------------------------------------------
        # YouTube clients
        #
        # web:
        # اصلی‌ترین client
        #
        # mweb:
        # در صورت وجود PO Token قابل استفاده است.
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
    # PO Tokens
    # ========================================================

    po_tokens = build_po_token_args()

    if po_tokens:

        opts["extractor_args"]["youtube"]["po_token"] = (
            ",".join(po_tokens)
        )

        print(
            "🔐 YouTube PO Token(s) configured:"
        )

        for token in po_tokens:

            # خود Token را چاپ نمی‌کنیم
            token_type = token.split("+", 1)[0]

            print(
                f"   ✅ {token_type}"
            )

    else:

        print(
            "⚠️ No YouTube PO Token configured."
        )

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
        )
    }

    # ========================================================
    # Find Real Video Qualities
    # ========================================================

    qualities = {}

    for f in info.get("formats", []):

        height = f.get("height")

        ext = f.get("ext")

        vcodec = f.get("vcodec")

        acodec = f.get("acodec")

        # بدون ارتفاع = رد
        if not height:
            continue

        # Audio-only = رد
        if not vcodec or vcodec == "none":
            continue

        # Thumbnail / mhtml = رد
        if ext == "mhtml":
            continue

        # کیفیت‌های خیلی پایین = رد
        if int(height) < 144:
            continue

        height = int(height)

        current = qualities.get(height)

        if current is None:

            qualities[height] = f

            continue

        # ====================================================
        # انتخاب بهترین format برای یک resolution
        # ====================================================

        def score(fmt):

            score_value = 0

            # MP4 ترجیح داده شود
            if fmt.get("ext") == "mp4":
                score_value += 100

            # دارای audio
            if fmt.get("acodec") not in (
                None,
                "none"
            ):
                score_value += 50

            # دارای video
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
    # Sort Qualities
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
        f"🎯 Requested quality: "
        f"{quality}p"
    )

    print("=" * 70)

    output_dir = (
        "/tmp/youtube_downloads"
    )

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
    # Format Selector
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

        mp4_file = (
            base + ".mp4"
        )

        # ====================================================
        # MP4
        # ====================================================

        if os.path.exists(mp4_file):

            print(
                f"✅ Download completed:"
                f" {mp4_file}"
            )

            return mp4_file

        # ====================================================
        # Original format
        # ====================================================

        if os.path.exists(filename):

            print(
                f"✅ Download completed:"
                f" {filename}"
            )

            return filename

    raise FileNotFoundError(
        "❌ فایل ویدیو بعد از دانلود پیدا نشد."
    )
