
import os
import base64
import tempfile
import yt_dlp


# =========================
# YouTube Cookies
# =========================

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


# =========================
# yt-dlp Options
# =========================

def get_ydl_opts():

    opts = {

        "quiet": False,

        "no_warnings": False,

        "noplaylist": True,

        "socket_timeout": 30,

        "retries": 3,

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


# =========================
# Get Video Information
# =========================

def get_video_data(url):

    ydl_opts = get_ydl_opts()

    ydl_opts["skip_download"] = True

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            url,
            download=False
        )

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
                or 0,

        }

        # =========================
        # Find Available Qualities
        # =========================

        available_heights = set()

        for f in info.get("formats", []):

            height = f.get("height")

            video_codec = f.get("vcodec")

            if not height:
                continue

            # فقط فرمت‌هایی که واقعاً ویدیو دارند
            if not video_codec:
                continue

            if video_codec == "none":
                continue

            available_heights.add(
                int(height)
            )

        # کیفیت‌های رایج
        qualities = sorted(
            available_heights,
            reverse=True
        )

        # تبدیل به لیست رشته‌ای برای bot.py
        qualities = [
            str(q)
            for q in qualities
        ]

        print(
            "🎥 Available qualities:",
            qualities
        )

        return video_info, qualities


# =========================
# Download Video
# =========================

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

    ydl_opts.update({

        # =========================
        # Video + Audio
        # =========================

        "format": (
            f"bestvideo[height<={quality}]"
            f"+bestaudio/"
            f"best[height<={quality}]"
        ),

        "outtmpl": output_template,

        "merge_output_format": "mp4",

        # فایل‌های موقت
        "paths": {

            "home": output_dir,

            "temp": output_dir

        },

        # اگر یک فرمت پیدا نشد،
        # yt-dlp سراغ انتخاب بعدی برود
        "format_sort": [
            "res",
            "fps",
            "codec:av01",
            "codec:vp9",
            "codec:h264"
        ],

        "noplaylist": True

    })

    print(
        f"⬇️ Starting download: {quality}p"
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

        # =========================
        # Check MP4
        # =========================

        if os.path.exists(mp4_file):

            print(
                f"✅ Download complete: "
                f"{mp4_file}"
            )

            return mp4_file

        # =========================
        # Check original extension
        # =========================

        if os.path.exists(filename):

            print(
                f"✅ Download complete: "
                f"{filename}"
            )

            return filename

        # =========================
        # Search for generated MP4
        # =========================

        video_id = info.get("id")

        if video_id:

            possible_file = os.path.join(
                output_dir,
                f"{video_id}.mp4"
            )

            if os.path.exists(
                possible_file
            ):

                print(
                    f"✅ Download complete: "
                    f"{possible_file}"
                )

                return possible_file

        raise FileNotFoundError(
            "فایل ویدیو بعد از دانلود پیدا نشد."
        )

