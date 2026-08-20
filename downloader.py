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
        encoded = "".join(
            line.strip()
            for line in cookies_b64.splitlines()
            if line.strip() and not line.startswith("-----")
        )

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

        # اجازه حل JS challenge
        "js_runtimes": {
            "deno": {}
        },

        # فقط web را به عنوان client اصلی استفاده می‌کنیم.
        # چون در Railway کلاینت‌های android/ios/tv
        # در لاگ شما 429 یا bot detection داشتند.
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


# ============================================================
# Print Formats
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
# Extract Video Information
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

    # ========================================================
    # Collect REAL video qualities
    # ========================================================

    qualities = {}

    for f in info.get("formats", []):

        height = f.get("height")
        ext = f.get("ext")
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")

        if not height:
            continue

        if not vcodec or vcodec == "none":
            continue

        if ext not in (
            "mp4",
            "webm",
            "m4v"
        ):
            continue

        # Video-only یا video+audio هر دو قابل قبول هستند.
        height = int(height)

        # کیفیت‌های خیلی پایین مثل thumbnail را حذف می‌کنیم.
        if height < 144:
            continue

        # برای هر ارتفاع فقط بهترین format را نگه می‌داریم.
        current = qualities.get(height)

        if current is None:
            qualities[height] = f
            continue

        # اولویت:
        # 1. MP4
        # 2. دارای audio
        # 3. حجم بالاتر در صورت موجود بودن

        current_score = (
            1 if current.get("ext") == "mp4" else 0,
            1 if current.get("acodec") not in (None, "none") else 0,
            current.get("filesize") or 0
        )

        new_score = (
            1 if f.get("ext") == "mp4" else 0,
            1 if acodec not in (None, "none") else 0,
            f.get("filesize") or 0
        )

        if new_score > current_score:
            qualities[height] = f

    # مرتب‌سازی نزولی
    qualities = dict(
        sorted(
            qualities.items(),
            key=lambda x: x[0],
            reverse=True
        )
    )

    available_qualities = [
        str(height)
        for height in qualities.keys()
    ]

    print()
    print(
        f"🎥 AVAILABLE QUALITIES: "
        f"{available_qualities}"
    )

    # فقط کیفیت‌هایی که واقعاً وجود دارند
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
    # Format Selection
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

    ydl_opts.update({

        "format": format_selector,

        "outtmpl": output_template,

        "merge_output_format": "mp4",

        # جلوگیری از ساخت فایل‌های اضافی در مسیرهای مختلف
        "paths": {
            "home": output_dir,
            "temp": output_dir
        },

        # اگر فایل موجود بود، دوباره دانلود نکن
        "overwrites": True,
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

        base, ext = os.path.splitext(
            filename
        )

        mp4_file = base + ".mp4"

        # ====================================================
        # Check MP4
        # ====================================================

        if os.path.exists(mp4_file):

            print(
                f"✅ Download completed:"
                f" {mp4_file}"
            )

            return mp4_file

        # ====================================================
        # Check original file
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
