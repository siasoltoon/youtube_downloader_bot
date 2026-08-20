
import os
import base64
import tempfile
import yt_dlp


# ============================================================
# Configuration
# ============================================================

POT_PROVIDER_URL = os.getenv(
    "YOUTUBE_POT_PROVIDER_URL",
    ""
).strip().rstrip("/")


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

            # حذف هدر/فوتر احتمالی
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
            "yt-dlp از provider داخلی 127.0.0.1:4416 استفاده خواهد کرد."
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

    # IMPORTANT:
    # bgutil extractor arguments در Python
    # باید به صورت list از stringها باشند.
    #
    # معادل CLI:
    #
    # --extractor-args
    # "youtubepot-bgutilhttp:base_url=http://..."
    #
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

        "quiet": False,

        "no_warnings": False,

        "noplaylist": True,

        "socket_timeout": 30,

        "retries": 5,

        "fragment_retries": 5,

        "file_access_retries": 3,

        "concurrent_fragment_downloads": 4,

        # ----------------------------------------------------
        # JavaScript runtime
        # ----------------------------------------------------

        "js_runtimes": {
            "deno": {}
        },

        # ----------------------------------------------------
        # Remote EJS components
        #
        # برای حل JS challenge های جدید YouTube
        # ----------------------------------------------------

        "remote_components": [
            "ejs:github"
        ],

        # ----------------------------------------------------
        # YouTube clients
        #
        # web اولویت اصلی است.
        # mweb فقط در صورت وجود format مناسب استفاده می‌شود.
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

        opts["cookiefile"] = COOKIE_FILE

    # ========================================================
    # PO Token Provider
    # ========================================================

    configure_pot_provider(opts)

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

        format_id = f.get(
            "format_id"
        )

        height = f.get(
            "height"
        )

        width = f.get(
            "width"
        )

        ext = f.get(
            "ext"
        )

        vcodec = f.get(
            "vcodec"
        )

        acodec = f.get(
            "acodec"
        )

        fps = f.get(
            "fps"
        )

        filesize = f.get(
            "filesize"
        )

        protocol = f.get(
            "protocol"
        )

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
# Get Available Video Qualities
# ============================================================

def get_video_data(url):

    print()
    print("🔎 Extracting video information...")

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

    print_formats(info)

    # ========================================================
    # Video information
    # ========================================================

    video_info = {

        "title": (
            info.get("title")
            or "نامشخص"
        ),

        "channel": (
            info.get("

