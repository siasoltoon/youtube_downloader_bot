
import os
import base64
import tempfile
import yt_dlp


# =========================================================
# YouTube Cookies
# =========================================================

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


# =========================================================
# Common yt-dlp Options
# =========================================================

def get_ydl_opts():

    opts = {

        "quiet": False,

        "no_warnings": False,

        "noplaylist": True,

        "socket_timeout": 30,

        "retries": 3,

        # اجازه استفاده از clientهای مختلف
        "extractor_args": {

            "youtube": {

                "player_client": [
                    "web",
                    "android",
                    "ios"
                ]

            }

        }

    }

    if COOKIE_FILE:

        opts["cookiefile"] = COOKIE_FILE

    return opts


# =========================================================
# Get Video Information
# =========================================================

def get_video_data(url):

    ydl_opts = get_ydl_opts()

    ydl_opts["skip_download"] = True

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        print(
            "🔎 Extracting video information..."
        )

        info = ydl.extract_info(
            url,
            download=False
        )

        # =================================================
        # Basic Information
        # =================================================

        video_info = {

            "title":
                info.get("title")
                or "نامشخص",

            "channel":
                info.get("channel")
                or info.get("uploader")
                or "نامشخص",

            "views":
                info.get("view_count")
                or 0,

            "likes":
                info.get("like_count")
                or 0,

            "duration":
                info.get("duration")
                or 0

        }

        # =================================================
        # DEBUG: ALL AVAILABLE FORMATS
        # =================================================

        print(
            "\n"
            "==================================================\n"
            "AVAILABLE YOUTUBE FORMATS\n"
            "=================================================="
        )

        formats = info.get("formats", [])

        for f in formats:

            print(

                "format_id=",
                f.get("format_id"),

                "| height=",
                f.get("height"),

                "| width=",
                f.get("width"),

                "| ext=",
                f.get("ext"),

                "| vcodec=",
                f.get("vcodec"),

                "| acodec=",
                f.get("acodec"),

                "| fps=",
                f.get("fps"),

                "| filesize=",
                f.get("filesize"),

                "| protocol=",
                f.get("protocol")

            )

        print(
            "==================================================\n"
        )

        # =================================================
        # Extract Available Video Qualities
        # =================================================

        available_heights = set()

        for f in formats:

            height = f.get("height")

            vcodec = f.get("vcodec")

            # فرمت باید ویدیو داشته باشد
            if not height:
                continue

            if not vcodec:
                continue

            if vcodec == "none":
                continue

            try:

                height = int(height)

            except:

                continue

            available_heights.add(
                height
            )

        # =================================================
        # Sort Qualities
        # =================================================

        qualities = sorted(
            available_heights,
            reverse=True
        )

        # تبدیل به string
        qualities = [
            str(q)
            for q in qualities
        ]

        print(
            "🎥 AVAILABLE QUALITIES:",
            qualities
        )

        return video_info, qualities


# =========================================================
# Download Video
# =========================================================

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

    ydl_opts = get_ydl_opts()

    # =====================================================
    # Format Selection
    # =====================================================

    format_selector = (
        f"bestvideo[height<={quality}]"
        f"+bestaudio/"
        f"best[height<={quality}]"
    )

    print(
        "\n"
        "=================================================="
    )

    print(
        f"🎯 Requested quality: {quality}p"
    )

    print(
        f"🎯 Format selector: {format_selector}"
    )

    print(
        "==================================================\n"
    )

    ydl_opts.update({

        "format": format_selector,

        "outtmpl": output_template,

        "merge_output_format": "mp4",

        "paths": {

            "home": output_dir,

            "temp": output_dir

        },

        "noplaylist": True

    })

    # =====================================================
    # Download
    # =====================================================

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        print(
            f"⬇️ Downloading {quality}p..."
        )

        info = ydl.extract_info(
            url,
            download=True
        )

        # =================================================
        # Find Output File
        # =================================================

        filename = ydl.prepare_filename(
            info
        )

        base, ext = os.path.splitext(
            filename
        )

        mp4_file = base + ".mp4"

        if os.path.exists(mp4_file):

            print(
                f"✅ MP4 found: {mp4_file}"
            )

            return mp4_file

        if os.path.exists(filename):

            print(
                f"✅ File found: {filename}"
            )

            return filename

        # =================================================
        # Search Directory
        # =================================================

        video_id = info.get("id")

        if video_id:

            for name in os.listdir(
                output_dir
            ):

                if name.startswith(
                    video_id
                ):

                    possible_file = os.path.join(
                        output_dir,
                        name
                    )

                    if os.path.isfile(
                        possible_file
                    ):

                        print(
                            f"✅ Found downloaded file: "
                            f"{possible_file}"
                        )

                        return possible_file

        raise FileNotFoundError(
            "❌ فایل ویدیو بعد از دانلود پیدا نشد."
        )

