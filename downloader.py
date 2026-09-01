
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


DOWNLOAD_DIR = (
    Path(tempfile.gettempdir())
    / "youtube_downloads"
)

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
        return

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
            "node": {}
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
            DOWNLOAD_DIR
            / "%(id)s.%(ext)s"
        ),

        # ----------------------------------------------------
        # Merge
        # ----------------------------------------------------

        "merge_output_format": "mp4",

        # ----------------------------------------------------
        # YouTube clients
        # ----------------------------------------------------

        "extractor_args": {

            "youtube": [
                "player_client=web,web_embedded,tv"
            ]

        }
    }

    if COOKIE_FILE:

        opts["cookiefile"] = COOKIE_FILE

    configure_pot_provider(
        opts
    )

    return opts


# ============================================================
# Human-readable file size
# ============================================================

def format_size(size):

    if not size:
        return "حجم نامشخص"

    try:

        size = float(size)

    except Exception:

        return "حجم نامشخص"

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB"
    ]

    index = 0

    while size >= 1024 and index < len(units) - 1:

        size /= 1024
        index += 1

    if index == 0:

        return f"{int(size)} {units[index]}"

    return f"{size:.1f} {units[index]}"


# ============================================================
# Duration formatter
# ============================================================

def format_duration(seconds):

    if not seconds:
        return "نامشخص"

    try:

        seconds = int(seconds)

    except Exception:

        return "نامشخص"

    hours = seconds // 3600

    minutes = (
        seconds % 3600
    ) // 60

    secs = (
        seconds % 60
    )

    if hours > 0:

        return (
            f"{hours}:{minutes:02d}:{secs:02d}"
        )

    return (
        f"{minutes}:{secs:02d}"
    )


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

    try:

        score += min(
            int(float(fmt.get("fps") or 0)),
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
# Extract video qualities + sizes
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

        if not height:
            continue

        try:

            height = int(height)

        except Exception:

            continue

        if height < 144:
            continue

        if (
            not vcodec
            or
            vcodec == "none"
        ):
            continue

        if fmt.get("ext") == "mhtml":
            continue

        current = qualities.get(
            height
        )

        if (
            current is None
            or
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
# Estimate final file size
# ============================================================

def estimate_quality_size(
    info,
    height
):

    formats = info.get(
        "formats",
        []
    )

    video_candidates = []

    audio_candidates = []

    # --------------------------------------------------------
    # Video
    # --------------------------------------------------------

    for fmt in formats:

        fmt_height = fmt.get(
            "height"
        )

        vcodec = fmt.get(
            "vcodec"
        )

        if not fmt_height:
            continue

        if not vcodec or vcodec == "none":
            continue

        try:

            fmt_height = int(
                fmt_height
            )

        except Exception:

            continue

        if fmt_height > height:
            continue

        filesize = (
            fmt.get("filesize")
            or
            fmt.get("filesize_approx")
        )

        if filesize:

            video_candidates.append(
                (
                    fmt_height,
                    filesize,
                    format_score(fmt)
                )
            )

    # --------------------------------------------------------
    # Audio
    # --------------------------------------------------------

    for fmt in formats:

        acodec = fmt.get(
            "acodec"
        )

        vcodec = fmt.get(
            "vcodec"
        )

        if (
            not acodec
            or
            acodec == "none"
        ):
            continue

        if (
            vcodec
            and
            vcodec != "none"
        ):
            continue

        filesize = (
            fmt.get("filesize")
            or
            fmt.get("filesize_approx")
        )

        if filesize:

            audio_candidates.append(
                filesize
            )

    if not video_candidates:

        return None

    # Best video format at requested height
    video_candidates.sort(
        key=lambda x: (
            x[0],
            x[2]
        ),
        reverse=True
    )

    video_size = (
        video_candidates[0][1]
    )

    audio_size = 0

    if audio_candidates:

        audio_size = max(
            audio_candidates
        )

    total = (
        video_size
        +
        audio_size
    )

    return total


# ============================================================
# Get Video Information
# ============================================================

def get_video_data(url):

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
            "اطلاعات ویدیو دریافت نشد."
        )

    qualities = extract_qualities(
        info
    )

    quality_data = []

    for height in qualities:

        estimated_size = (
            estimate_quality_size(
                info,
                height
            )
        )

        quality_data.append({

            "height": height,

            "size": estimated_size,

            "size_text": format_size(
                estimated_size
            )

        })

    available_qualities = [

        item["height"]

        for item in quality_data

    ]

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

        "duration_text": format_duration(
            info.get("duration")
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
        ),

        "quality_data": quality_data

    }

    print(
        "🎥 AVAILABLE QUALITIES:",
        available_qualities
    )

    return (
        video_info,
        quality_data
    )


# ============================================================
# Get YouTube comments
# ============================================================

def get_video_comments(
    url,
    max_comments=100
):

    print(
        f"💬 Extracting comments: {url}"
    )

    ydl_opts = get_ydl_opts()

    ydl_opts.update({

        "skip_download": True,

        "getcomments": True,

        "extractor_args": {

            "youtube": [

                "player_client=web,web_embedded,tv"

            ],

            "youtubepot-bgutilhttp": (

                [
                    f"base_url={POT_PROVIDER_URL}"
                ]

                if POT_PROVIDER_URL

                else []

            )

        }

    })

    with yt_dlp.YoutubeDL(
        ydl_opts
    ) as ydl:

        info = ydl.extract_info(
            url,
            download=False
        )

    comments = (
        info.get("comments")
        or []
    )

    result = []

    for comment in comments:

        if len(result) >= max_comments:
            break

        text = (
            comment.get("text")
            or ""
        )

        if not text:
            continue

        author = (
            comment.get("author")
            or "کاربر"
        )

        like_count = (
            comment.get("like_count")
            or 0
        )

        result.append({

            "author": author,

            "text": text,

            "likes": like_count

        })

    return result


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

    quality = int(
        quality
    )

    print(
        f"🎯 Requested quality: {quality}p"
    )

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
            "Video information unavailable."
        )

    video_id = (
        info.get("id")
        or "youtube_video"
    )

    qualities = extract_qualities(
        info
    )

    available = sorted(
        qualities.keys()
    )

    if not available:

        raise RuntimeError(
            "هیچ کیفیت ویدیویی پیدا نشد."
        )

    valid = [
        h
        for h in available
        if h <= quality
    ]

    if valid:

        selected_height = max(
            valid
        )

    else:

        selected_height = min(
            available,
            key=lambda h: abs(h - quality)
        )

    print(
        f"📺 Selected quality: {selected_height}p"
    )

    ydl_opts = get_ydl_opts()

    ydl_opts["format"] = build_format_selector(
        selected_height
    )

    ydl_opts["postprocessors"] = [
        {
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4"
        }
    ]

    ydl_opts["merge_output_format"] = "mp4"

    with yt_dlp.YoutubeDL(
        ydl_opts
    ) as ydl:

        ydl.download([
            url
        ])

    final_file = find_final_file(
        video_id
    )

    if not final_file:

        raise RuntimeError(
            "فایل نهایی MP4 پیدا نشد."
        )

    file_size = os.path.getsize(
        final_file
    )

    if file_size <= 0:

        raise RuntimeError(
            "فایل دانلود شده خالی است."
        )

    print(
        f"✅ Download completed: {final_file} "
        f"({format_size(file_size)})"
    )

    return final_file
