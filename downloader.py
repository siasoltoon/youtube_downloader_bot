import os
import base64
import tempfile
import yt_dlp


def create_cookie_file():
    cookies_b64 = os.getenv("YOUTUBE_COOKIES_B64")

    if not cookies_b64:
        print("⚠️ YOUTUBE_COOKIES_B64 تنظیم نشده است.")
        return None

    # حذف فاصله‌ها، خطوط اضافی و هدر/فوتر احتمالی
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
        cookie_data = base64.b64decode(encoded, validate=True)
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


def get_ydl_opts():
    """
    تنظیمات مشترک yt-dlp
    """

    opts = {
        "quiet": False,
        "no_warnings": False,
        "noplaylist": True,

        "socket_timeout": 30,
        "retries": 3,

        # اجازه بده yt-dlp خودش بهترین clientها را انتخاب کند
        # و فقط به web محدود نشود.
        "extractor_args": {
            "youtube": {
                "player_client": [
                    "web",
                    "android",
                    "ios"
                ]
            }
        },
    }

    if COOKIE_FILE:
        opts["cookiefile"] = COOKIE_FILE

    return opts


def get_video_data(url):

    ydl_opts = get_ydl_opts()

    # فقط اطلاعات را می‌گیریم و چیزی دانلود نمی‌شود
    ydl_opts["skip_download"] = True

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            url,
            download=False
        )

        video_info = {
            "title": info.get("title") or "نامشخص",

            "channel": (
                info.get("channel")
                or info.get("uploader")
                or "نامشخص"
            ),

            "views": info.get("view_count") or 0,

            "likes": info.get("like_count") or 0,

            "duration": info.get("duration") or 0,
        }

        qualities = {}

        for f in info.get("formats", []):

            height = f.get("height")
            ext = f.get("ext")
            format_url = f.get("url")

            if (
                height
                and ext == "mp4"
                and format_url
            ):
                height_key = str(height)

                # اگر چند فرمت با یک کیفیت وجود داشت،
                # بهترین مورد را نگه می‌داریم.
                if height_key not in qualities:
                    qualities[height_key] = format_url

        qualities = dict(
            sorted(
                qualities.items(),
                key=lambda x: int(x[0]),
                reverse=True
            )
        )

        return video_info, qualities


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

        "format": (
            f"bestvideo[height<={quality}]"
            f"+bestaudio/"
            f"best[height<={quality}]"
        ),

        "outtmpl": output_template,

        "merge_output_format": "mp4",

        # فایل‌های موقت داخل همان پوشه
        "paths": {
            "home": output_dir,
            "temp": output_dir
        },
    })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            url,
            download=True
        )

        filename = ydl.prepare_filename(info)

        base, _ = os.path.splitext(filename)

        mp4_file = base + ".mp4"

        if os.path.exists(mp4_file):
            return mp4_file

        if os.path.exists(filename):
            return filename

        raise FileNotFoundError(
            "فایل ویدیو بعد از دانلود پیدا نشد."
        )
