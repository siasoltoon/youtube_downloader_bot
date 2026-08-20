
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
    os.getenv(
        "YOUTUBE_DOWNLOAD_DIR",
        "/tmp/youtube_downloads"
    )
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
        clean_lines = []

        for line in cookies_b64.splitlines():
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

    with open(
        cookie_file,
        "wb"
    ) as f:
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

    Example:

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

    extractor_args[
        "youtubepot-bgutilhttp"
    ] = [
        f"base_url={POT_PROVIDER_URL}"
    ]


# ============================================================
# yt-dlp Options
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
        opts[
            "cookiefile"
        ] = COOKIE_FILE

    # ========================================================
    # PO Token Provider
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
    print(
        "AVAILABLE YOUTUBE FORMATS"
    )
    print("=" * 70)

    formats = info.get(
        "formats",
        []
    )

    if not formats:

        print(
            "⚠️ No formats returned by YouTube."
        )

        print(
            "=" * 70
        )

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

    print(
        "=" * 70
    )


# ============================================================
# Format Score
# ============================================================

def format_score(fmt):

    score = 0

    # MP4
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
            float(
                fmt.get("tbr") or 0
            )
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

        height = fmt.get(
            "height"
        )

        ext = fmt.get(
            "ext"
        )

        vcodec = fmt.get(
            "vcodec"
        )

        if not height:
            continue

        try:

            height = int(
                height
            )

        except Exception:

            continue

        # Ignore tiny formats
        if height < 144:
            continue

        # Ignore audio-only
        if (
            not vcodec
            or
            vcodec == "none"
        ):
            continue

        # Ignore thumbnails/storyboards
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

        if (
            format_score(fmt)
            >
            format_score(current)
        ):

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
    # Qualities
    # ========================================================

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

    # First choice:
    # separate video + audio
    #
    # Fallback:
    # combined format containing
    # video + audio

    selector = (
        f"bestvideo[height<={quality}]"
        f"+bestaudio/"
        f"best[height<={quality}]"
    )

    return selector


# ============================================================
# Find Downloaded File
# ============================================================

def find_downloaded_file(
    output_dir,
    video_id
):

    output_dir = Path(
        output_dir
    )

    if not output_dir.exists():
        return None

    candidates = []

    for path in output_dir.glob(
        f"{video_id}.*"
    ):

        if not path.is_file():
            continue

        # Ignore temporary files
        if path.name.endswith(
            ".part"
        ):
            continue

        if path.name.endswith(
            ".ytdl"
        ):
            continue

        candidates.append(
            path
        )

    if not candidates:
        return None

    # Prefer MP4
    mp4_files = [
        p
        for p in candidates
        if p.suffix.lower()
        == ".mp4"
    ]

    if mp4_files:

        return max(
            mp4_files,
            key=lambda p: p.stat().st_mtime
        )

    return max(
        candidates,
        key=lambda p: p.stat().st_mtime
    )


# ============================================================
# Download Video
# ============================================================

def download_video(
    url,
    quality
):

    quality = int(
        quality
    )

    print()
    print("=" * 70)

    print(
        f"🎯 Requested quality: "
        f"{quality}p"
    )

    print("=" * 70)

    # ========================================================
    # Output directory
    # ========================================================

    DOWNLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_template = str(
        DOWNLOAD_DIR
        /
        "%(id)s.%(ext)s"
    )

    # ========================================================
    # yt-dlp options
    # ========================================================

    ydl_opts = get_ydl_opts()

    format_selector = (
        build_format_selector(
            quality
        )
    )

    print(
        "🎯 Format selector:",
        format_selector
    )

    ydl_opts.update({

        "format": format_selector,

        "outtmpl": output_template,

        "merge_output_format": "mp4",

        "postprocessors": [
            {
                "key": "FFmpegVideoRemuxer",
                "preferedformat": "mp4"
            }
        ],

        "noplaylist": True,

        "overwrites": True,

        "continuedl": True
    })

    # ========================================================
    # Download
    # ========================================================

    print()
    print(
        f"⬇️ Downloading {quality}p..."
    )

    with yt_dlp.YoutubeDL(
        ydl_opts
    ) as ydl:

        info = ydl.extract_info(
            url,
            download=True
        )

        if not info:

            raise RuntimeError(
                "❌ yt-dlp اطلاعات دانلود را برنگرداند."
            )

        video_id = (
            info.get("id")
            or ""
        )

        # ====================================================
        # Find actual output
        # ====================================================

        downloaded_file = (
            find_downloaded_file(
                DOWNLOAD_DIR,
                video_id
            )
        )

        # ====================================================
        # Fallback to prepare_filename
        # ====================================================

        if (
            downloaded_file
            is None
        ):

            try:

                prepared = Path(
                    ydl.prepare_filename(
                        info
                    )
                )

                if prepared.exists():
                    downloaded_file = prepared

                else:

                    mp4_path = (
                        prepared.with_suffix(
                            ".mp4"
                        )
                    )

                    if mp4_path.exists():
                        downloaded_file = mp4_path

            except Exception as e:

                print(
                    "⚠️ prepare_filename error:",
                    repr(e)
                )

        # ====================================================
        # Final validation
        # ====================================================

        if (
            downloaded_file
            is None
        ):

            raise FileNotFoundError(
                "❌ فایل ویدیو بعد از دانلود پیدا نشد."
            )

        downloaded_file = Path(
            downloaded_file
        )

        if not downloaded_file.exists():

            raise FileNotFoundError(
                f"❌ فایل پیدا نشد: "
                f"{downloaded_file}"
            )

        file_size = (
            downloaded_file.stat().st_size
        )

        if file_size <= 0:

            raise RuntimeError(
                "❌ فایل دانلود شده خالی است."
            )

        print()
        print(
            f"✅ Download completed:"
            f" {downloaded_file}"
        )

        print(
            f"📦 File size:"
            f" {file_size / (1024 * 1024):.2f} MB"
        )

        return str(
            downloaded_file
        )


# ============================================================
# Module Test
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print(
        "DOWNLOADER MODULE TEST"
    )
    print("=" * 70)

    print(
        "get_video_data:",
        callable(get_video_data)
    )

    print(
        "download_video:",
        callable(download_video)
    )

    print(
        "build_format_selector:",
        callable(build_format_selector)
    )

    print(
        "POT_PROVIDER_URL:",
        POT_PROVIDER_URL
        or "(not configured)"
    )

    print(
        "COOKIE_FILE:",
        COOKIE_FILE
        or "(not configured)"
    )

    print(
        "=" * 70
    )

