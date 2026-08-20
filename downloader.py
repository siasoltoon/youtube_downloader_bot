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

    with open(cookie_file, "wb") as f:
        f.write(cookie_data)

    print(
        f"🍪 YouTube cookies loaded: "
        f"{len(cookie_data)} bytes"
    )

    return cookie_file


COOKIE_FILE = create_cookie_file()


# =========================
# Common yt-dlp options
# =========================

def get_ydl_opts():

    opts = {

        "quiet": False,

        "no_warnings": False,

        "noplaylist": True,

        "socket_timeout": 30,

        "retries": 3,

        "fragment_retries": 3,

        "concurrent_fragment_downloads": 4,

        "extractor_args": {

            "youtube": {

                "player_client": [
                    "web"
                ]

            }

        },

    }

    if COOKIE_FILE:

        opts["cookiefile"] = COOKIE_FILE

    return opts


# =========================
# Get video information
# =========================

def get_video_data(url):

    print("🔎 Extracting video information...")

    ydl_opts = get_ydl_opts()

    ydl_opts["skip_download"] = True

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            url,
            download=False
        )

        print("=" * 50)
        print("AVAILABLE YOUTUBE FORMATS")
        print("=" * 50)

        qualities = {}

        for f in info.get("formats", []):

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

            # فقط فرمت‌هایی که واقعاً ویدیو دارند
            if not height:
                continue

            if not vcodec:
                continue

            if vcodec == "none":
                continue

            # کیفیت‌های ویدیویی را نگه می‌داریم
            height_key = str(int(height))

            # اگر کیفیت تکراری بود، فقط یک بار اضافه شود
            qualities[height_key] = True

        # مرتب‌سازی از کم به زیاد
        qualities = sorted(
            qualities.keys(),
            key=lambda x: int(x)
        )

        print("=" * 50)
        print(
            f"🎥 AVAILABLE QUALITIES: {qualities}"
        )
        print("=" * 50)

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

        }

        return video_info, qualities


# =========================
# Download video
# =========================

def download_video(url, quality):

    quality = int(quality)

    print("=" * 50)

    print(
        f"🎯 Requested quality: {quality}p"
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

    ydl_opts = get_ydl_opts()

    # برای کیفیت انتخاب شده:
    #
    # video-only + audio
    #
    # و اگر video-only موجود نبود:
    #
    # progressive video+audio
    #
    format_selector = (
        f"bestvideo[height<={quality}]"
        f"+bestaudio/"
        f"best[height<={quality}]"
    )

    print(
        f"🎯 Format selector: "
        f"{format_selector}"
    )

    ydl_opts.update({

        "format": format_selector,

        "outtmpl": output_template,

        "merge_output_format": "mp4",

        "postprocessors": [

            {

                "key": "FFmpegVideoConvertor",

                "preferedformat": "mp4"

            }

        ],

        "noplaylist": True,

    })

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

        # فایل Merge شده
        if os.path.exists(mp4_file):

            print(
                f"✅ Download completed: "
                f"{mp4_file}"
            )

            return mp4_file

        # اگر خود فایل خروجی mp4 بود
        if os.path.exists(filename):

            print(
                f"✅ Download completed: "
                f"{filename}"
            )

            return filename

        # جستجوی فایل‌های احتمالی
        video_id = info.get("id")

        possible_files = [

            os.path.join(
                output_dir,
                f"{video_id}.mp4"
            ),

            os.path.join(
                output_dir,
                f"{video_id}.mkv"
            ),

            os.path.join(
                output_dir,
                f"{video_id}.webm"
            ),

        ]

        for file_path in possible_files:

            if os.path.exists(file_path):

                print(
                    f"✅ Download completed: "
                    f"{file_path}"
                )

                return file_path

    raise FileNotFoundError(
        "فایل ویدیو بعد از دانلود پیدا نشد."
    )
