
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

    try:

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
# Client configurations
# ============================================================

CLIENTS = [

    {
        "name": "web",
        "player_client": ["web"],
        "use_cookies": True,
    },

    {
        "name": "mweb",
        "player_client": ["mweb"],
        "use_cookies": True,
    },

    {
        "name": "tv",
        "player_client": ["tv"],
        "use_cookies": False,
    },

    {
        "name": "android",
        "player_client": ["android"],
        "use_cookies": False,
    },

    {
        "name": "ios",
        "player_client": ["ios"],
        "use_cookies": False,
    },

]


# ============================================================
# Base yt-dlp options
# ============================================================

def get_ydl_opts(
    player_client,
    use_cookies=True
):

    opts = {

        "quiet": False,

        "no_warnings": False,

        "noplaylist": True,

        "socket_timeout": 30,

        "retries": 3,

        "fragment_retries": 3,

        "extractor_args": {

            "youtube": {

                "player_client": player_client

            }

        },

    }

    if use_cookies and COOKIE_FILE:

        opts["cookiefile"] = COOKIE_FILE

    return opts


# ============================================================
# Extract formats from one client
# ============================================================

def extract_with_client(
    url,
    client
):

    print()
    print("=" * 60)

    print(
        f"🔎 Trying YouTube client: "
        f"{client['name']}"
    )

    print("=" * 60)

    opts = get_ydl_opts(

        client["player_client"],

        client["use_cookies"]

    )

    opts["skip_download"] = True

    try:

        with yt_dlp.YoutubeDL(opts) as ydl:

            info = ydl.extract_info(
                url,
                download=False
            )

            return info

    except Exception as e:

        print(
            f"⚠️ Client "
            f"{client['name']} failed:"
        )

        print(
            repr(e)
        )

        return None


# ============================================================
# Get Video Data
# ============================================================

def get_video_data(url):

    print()
    print("🔎 Extracting video information...")
    print()

    main_info = None

    all_formats = []

    successful_clients = []

    # ========================================================
    # Try multiple clients
    # ========================================================

    for client in CLIENTS:

        info = extract_with_client(
            url,
            client
        )

        if not info:
            continue

        if main_info is None:

            main_info = info

        formats = info.get(
            "formats",
            []
        )

        print(
            f"✅ Client {client['name']} "
            f"returned {len(formats)} formats."
        )

        if formats:

            successful_clients.append(
                client["name"]
            )

            all_formats.extend(
                formats
            )

    # ========================================================
    # No extraction result
    # ========================================================

    if main_info is None:

        raise RuntimeError(
            "هیچ YouTube clientای نتوانست ویدیو را استخراج کند."
        )

    # ========================================================
    # Print all discovered formats
    # ========================================================

    print()
    print("=" * 60)
    print("AVAILABLE YOUTUBE FORMATS")
    print("=" * 60)

    for f in all_formats:

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

    # ========================================================
    # Find available video qualities
    # ========================================================

    qualities = {}

    for f in all_formats:

        height = f.get("height")

        vcodec = f.get("vcodec")

        if not height:
            continue

        if not vcodec:
            continue

        if vcodec == "none":
            continue

        try:

            height = int(height)

        except Exception:

            continue

        # Ignore thumbnails / storyboard formats
        if height < 144:
            continue

        height_key = str(height)

        # Save the largest format information for this height
        existing = qualities.get(
            height_key
        )

        if existing is None:

            qualities[height_key] = f

        else:

            # Prefer MP4
            if (
                f.get("ext") == "mp4"
                and existing.get("ext") != "mp4"
            ):

                qualities[height_key] = f

    qualities = sorted(
        qualities.keys(),
        key=lambda x: int(x)
    )

    print()
    print("=" * 60)

    print(
        f"🎥 AVAILABLE QUALITIES: "
        f"{qualities}"
    )

    print(
        f"🔌 Successful clients: "
        f"{successful_clients}"
    )

    print("=" * 60)

    # ========================================================
    # Video information
    # ========================================================

    video_info = {

        "title": (
            main_info.get("title")
            or "نامشخص"
        ),

        "channel": (
            main_info.get("channel")
            or main_info.get("uploader")
            or "نامشخص"
        ),

        "views": (
            main_info.get("view_count")
            or 0
        ),

        "likes": (
            main_info.get("like_count")
            or 0
        ),

        "duration": (
            main_info.get("duration")
            or 0
        ),

    }

    return video_info, qualities


# ============================================================
# Download Video
# ============================================================

def download_video(
    url,
    quality
):

    quality = int(quality)

    print()
    print("=" * 60)

    print(
        f"🎯 Requested quality: "
        f"{quality}p"
    )

    output_dir = "/tmp/youtube_downloads"

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    output_template = os.path.join(

        output_dir,

        "%(id)s.%(ext)s"

    )

    # ========================================================
    # Download options
    # ========================================================

    opts = get_ydl_opts(

        ["web"],

        True

    )

    # ========================================================
    # Format selector
    # ========================================================

    format_selector = (

        f"bestvideo[height<={quality}]"

        f"+bestaudio/"

        f"best[height<={quality}]"

    )

    print(
        f"🎯 Format selector: "
        f"{format_selector}"
    )

    opts.update({

        "format": format_selector,

        "outtmpl": output_template,

        "merge_output_format": "mp4",

        "noplaylist": True,

    })

    print(
        f"⬇️ Downloading "
        f"{quality}p..."
    )

    # ========================================================
    # Download
    # ========================================================

    with yt_dlp.YoutubeDL(opts) as ydl:

        info = ydl.extract_info(

            url,

            download=True

        )

        filename = ydl.prepare_filename(
            info
        )

        base, _ = os.path.splitext(
            filename
        )

        mp4_file = (
            base
            + ".mp4"
        )

        # ====================================================
        # MP4 result
        # ====================================================

        if os.path.exists(
            mp4_file
        ):

            print(
                f"✅ Download completed:"
            )

            print(
                mp4_file
            )

            return mp4_file

        # ====================================================
        # Original result
        # ====================================================

        if os.path.exists(
            filename
        ):

            print(
                f"✅ Download completed:"
            )

            print(
                filename
            )

            return filename

        # ====================================================
        # Search fallback
        # ====================================================

        video_id = info.get(
            "id"
        )

        possible_extensions = [

            "mp4",
            "mkv",
            "webm",
            "mov"

        ]

        for ext in possible_extensions:

            candidate = os.path.join(

                output_dir,

                f"{video_id}.{ext}"

            )

            if os.path.exists(
                candidate
            ):

                print(
                    f"✅ Download completed:"
                )

                print(
                    candidate
                )

                return candidate

    raise FileNotFoundError(

        "فایل ویدیو بعد از دانلود پیدا نشد."

    )

