```python
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


DOWNLOAD_DIR = Path(
    tempfile.gettempdir()
) / "youtube_downloads"

DOWNLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# YouTube Cookies
# ============================================================

def create_cookie_file():
    cookies_b64 = os.getenv(
        "YOUTUBE_COOKIES_B64"
    )

    if not cookies_b64:
        print(
            "⚠️ YOUTUBE_COOKIES_B64 تنظیم نشده است."
        )
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

        encoded = "".join(
            clean_lines
        )

        cookie_data = base64.b64decode(
            encoded,
            validate=True
        )

    except Exception as e:

        raise RuntimeError(
            f"YOUTUBE_COOKIES_B64 نامعتبر است: {e}"
        )

    cookie_file = (
        Path(tempfile.gettempdir())
        / "youtube_cookies.txt"
    )

    with open(
        cookie_file,
        "wb"
    ) as f:

        f.write(
            cookie_data
        )

    print(
        f"🍪 YouTube cookies loaded: "
        f"{len(cookie_data)} bytes"
    )

    return str(cookie_file)


COOKIE_FILE = create_cookie_file()


# ============================================================
# PO Token Provider
# ============================================================

def configure_pot_provider(opts):

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

        "quiet": False,

        "no_warnings": False,

        "noplaylist": True,

        "socket_timeout": 30,

        "retries": 5,

        "fragment_retries": 5,

        "file_access_retries": 3,

        "continuedl": True,

        "overwrites": True,

        "concurrent_fragment_downloads": 4,

        # ----------------------------------------------------
        # JavaScript
        # ----------------------------------------------------

        "js_runtimes": {
            "deno": {}
        },

        # ----------------------------------------------------
        # Remote EJS
        # ----------------------------------------------------

        "remote_components": [
            "ejs:github"
        ],

        # ----------------------------------------------------
        # Output
        # ----------------------------------------------------

        "outtmpl": str(
            DOWNLOAD_DIR / "%(id)s.%(ext)s"
        ),

        # ----------------------------------------------------
        # Merge / Remux
        # ----------------------------------------------------

        "merge_output_format": "mp4",

        "postprocessors": [
            {
                "key": "FFmpegVideoRemuxer",
                "preferedformat": "mp4"
            }
        ],

        # ----------------------------------------------------
        # YouTube clients
        # ----------------------------------------------------

        "extractor_args": {

            "youtube": [
                "player_client=web,web_embedded,tv"
            ]

        }
    }

    # ========================================================
    # Cookies
    # ========================================================

    if COOKIE_FILE:

        opts["cookiefile"] = COOKIE_FILE

    # ========================================================
    # PO Provider
    # ========================================================

    configure_pot_provider(
        opts
    )

    return opts


# ============================================================
# Print Formats
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

    if fmt.get("ext") == "mp4":
        score += 100

    if fmt.get("vcodec") not in (
        None,
        "none"
    ):
        score += 50

    if fmt.get("acodec") not in (
        None,
        "none"
    ):
        score += 50

    fps = fmt.get("fps")

    if fps:

        try:

            score += min(
                int(float(fps)),
                60
            )

        except Exception:
            pass

    try:

        score += int(
            float(
                fmt.get("tbr") or 0
            )
        )

    except Exception:
        pass

    return score


# ============================================================
# Extract Qualities
# ============================================================

def extract_qualities(info):

    qualities = {}

    for fmt in info.get(
        "formats",
        []
    ):

        height = fmt.get(
            "height"
        )

        vcodec = fmt.get(
            "vcodec"
        )

        ext = fmt.get(
            "ext"
        )

        if not height:
            continue

        try:

            height = int(
                height
            )

        except Exception:

            continue

        if height < 144:
            continue

        if not vcodec or vcodec == "none":
            continue

        if ext == "mhtml":
            continue

        current = qualities.get(
            height
        )

        if current is None:

            qualities[
                height
            ] = fmt

            continue

        if format_score(fmt) > format_score(current):

            qualities[
                height
            ] = fmt

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
    print(
        "🔎 Extracting video information..."
    )

    ydl_opts = get_ydl_opts()

    ydl_opts[
        "skip_download"
    ] = True

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

    print_formats(
        info
    )

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

    qualities = extract_qualities(
        info
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

    return (
        video_info,
        available_qualities
    )


# ============================================================
# Build Format Selector
# ============================================================

def build_format_selector(
    quality
):

    quality = int(
        quality
    )

    return (
        f"bestvideo[height<={quality}]"
        f"+bestaudio/"
        f"best[height<={quality}]"
    )


# ============================================================
# Find Final MP4
# ============================================================

def find_final_file(
    video_id
):

    expected = (
        DOWNLOAD_DIR
        / f"{video_id}.mp4"
    )

    if expected.exists():

        return str(
            expected
        )

    # fallback: پیدا کردن فایل‌های MP4
    matches = list(
        DOWNLOAD_DIR.glob(
            f"{video_id}*.mp4"
        )
    )

    if matches:

        matches.sort(
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        return str(
            matches[0]
        )

    return None


# ============================================================
# Download Video
# ============================================================

def download_video(
    url,
    quality
):

    print()
    print("=" * 70)

    print(
        f"🎯 Requested quality: "
        f"{quality}p"
    )

    print("=" * 70)

    quality = int(
        quality
    )

    # --------------------------------------------------------
    # Extract video ID first
    # --------------------------------------------------------

    info_opts = get_ydl_opts()

    info_opts[
        "skip_download"
    ] = True

    with yt_dlp.YoutubeDL(
        info_opts
    ) as ydl:

        info = ydl.extract_info(
            url,
            download=False
        )

    if not info:

        raise RuntimeError(
            "❌ Video information unavailable."
        )

    video_id = (
        info.get("id")
        or "youtube_video"
    )

    # --------------------------------------------------------
    # Clean old files for this video
    # --------------------------------------------------------

    for old_file in DOWNLOAD_DIR.glob(
        f"{video_id}*"
    ):

        try:

            old_file.unlink()

        except Exception:

            pass

    # --------------------------------------------------------
    # Format
    # --------------------------------------------------------

    format_selector = (
        build_format_selector(
            quality
        )
    )

    print("=" * 70)

    print(
        f"🎯 Format selector: "
        f"{format_selector}"
    )

    print(
        f"⬇️ Downloading {quality}p..."
    )

    print("=" * 70)

    # --------------------------------------------------------
    # yt-dlp options
    # --------------------------------------------------------

    ydl_opts = get_ydl_opts()

    ydl_opts.update({

        "format": format_selector,

        "outtmpl": str(
            DOWNLOAD_DIR
            / f"{video_id}.%(ext)s"
        ),

        "merge_output_format": "mp4",

        "postprocessors": [
            {
                "key": "FFmpegVideoRemuxer",
                "preferedformat": "mp4"
            }
        ]

    })

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    try:

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            result = ydl.download(
                [url]
            )

    except Exception as e:

        print()
        print(
            "❌ yt-dlp download error:"
        )

        print(
            repr(e)
        )

        raise

    print()
    print(
        f"yt-dlp return code: "
        f"{result}"
    )

    # --------------------------------------------------------
    # Locate final file
    # --------------------------------------------------------

    final_file = find_final_file(
        video_id
    )

    if not final_file:

        print()
        print(
            "❌ Download finished but "
            "final MP4 was not found."
        )

        print(
            "Files in download directory:"
        )

        for file in DOWNLOAD_DIR.glob("*"):

            print(
                f" - {file}"
            )

        raise FileNotFoundError(
            "Final MP4 file not found."
        )

    # --------------------------------------------------------
    # Validate file
    # --------------------------------------------------------

    final_path = Path(
        final_file
    )

    if not final_path.is_file():

        raise FileNotFoundError(
            "Final video is not a regular file."
        )

    file_size = (
        final_path.stat().st_size
    )

    if file_size <= 0:

        raise RuntimeError(
            "Downloaded video is empty."
        )

    print()
    print("=" * 70)

    print(
        "✅ DOWNLOAD COMPLETED"
    )

    print(
        f"📁 File: {final_file}"
    )

    print(
        f"📦 Size: "
        f"{file_size / (1024 * 1024):.2f} MB"
    )

    print("=" * 70)

    # بسیار مهم:
    # مسیر فایل نهایی را برمی‌گردانیم
    return final_file


# ============================================================
# Module Test
# ============================================================

if __name__ == "__main__":

    print(
        "Downloader module loaded successfully."
    )

    print(
        f"Download directory: "
        f"{DOWNLOAD_DIR}"
    )

    if POT_PROVIDER_URL:

        print(
            f"PO provider: "
            f"{POT_PROVIDER_URL}"
        )

    else:

        print(
            "PO provider: disabled"
        )
```
