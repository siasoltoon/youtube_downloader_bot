import subprocess
import os
import threading
import uuid

import boto3
import telebot
from telebot import types

from botocore.exceptions import ClientError

from downloader import (
    get_video_data,
    download_video
)


# ============================================================
# Deno Test
# ============================================================

try:
    result = subprocess.run(
        ["deno", "--version"],
        capture_output=True,
        text=True
    )

    print("DENO TEST:")
    print(result.stdout)
    print(result.stderr)

except Exception as e:
    print("DENO TEST ERROR:", repr(e))


# ============================================================
# FFmpeg Test
# ============================================================

try:
    result = subprocess.run(
        ["ffmpeg", "-version"],
        capture_output=True,
        text=True
    )

    print("FFMPEG TEST:")

    if result.returncode == 0:
        first_line = result.stdout.splitlines()[0]
        print(first_line)
    else:
        print(result.stderr)

except Exception as e:
    print("FFMPEG TEST ERROR:", repr(e))


# ============================================================
# YouTube Connection Test
# ============================================================

try:
    result = subprocess.run(
        [
            "curl",
            "-4",
            "-I",
            "https://www.youtube.com"
        ],
        capture_output=True,
        text=True,
        timeout=20
    )

    print("YOUTUBE CONNECTION TEST:")
    print(result.stdout)
    print(result.stderr)

except Exception as e:
    print("YOUTUBE TEST ERROR:", repr(e))


# ============================================================
# Environment Variables
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

FILONE_ACCESS_KEY = os.getenv("FILONE_ACCESS_KEY")
FILONE_SECRET_KEY = os.getenv("FILONE_SECRET_KEY")
FILONE_BUCKET = os.getenv("FILONE_BUCKET")
FILONE_ENDPOINT = os.getenv("FILONE_ENDPOINT")


# ============================================================
# Validate Environment Variables
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN پیدا نشد!"
    )


if not FILONE_ACCESS_KEY:
    raise RuntimeError(
        "FILONE_ACCESS_KEY پیدا نشد!"
    )


if not FILONE_SECRET_KEY:
    raise RuntimeError(
        "FILONE_SECRET_KEY پیدا نشد!"
    )


if not FILONE_BUCKET:
    raise RuntimeError(
        "FILONE_BUCKET پیدا نشد!"
    )


if not FILONE_ENDPOINT:
    raise RuntimeError(
        "FILONE_ENDPOINT پیدا نشد!"
    )


print()
print("=" * 60)
print("FIL ONE CONFIGURATION")
print("=" * 60)

print(
    "Access Key:",
    bool(FILONE_ACCESS_KEY)
)

print(
    "Secret Key:",
    bool(FILONE_SECRET_KEY)
)

print(
    "Bucket:",
    FILONE_BUCKET
)

print(
    "Endpoint:",
    FILONE_ENDPOINT
)

print("=" * 60)


# ============================================================
# Fil One S3 Client
# ============================================================

s3 = boto3.client(
    "s3",

    endpoint_url=FILONE_ENDPOINT,

    aws_access_key_id=FILONE_ACCESS_KEY,

    aws_secret_access_key=FILONE_SECRET_KEY,

    region_name="eu-west-1"
)


# ============================================================
# Telegram Bot
# ============================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)


# ============================================================
# User Data
# ============================================================

user_data = {}


# ============================================================
# Upload File To Fil One
# ============================================================

def upload_to_filo(file_path):
    """
    Upload local file to Fil One.

    Returns:
        object_key
    """

    filename = os.path.basename(file_path)

    unique_id = uuid.uuid4().hex

    object_key = (
        f"telegram-videos/"
        f"{unique_id}_"
        f"{filename}"
    )

    print()
    print("=" * 60)
    print("⬆️ UPLOADING TO FIL ONE")
    print("=" * 60)

    print(
        "Local file:",
        file_path
    )

    print(
        "Bucket:",
        FILONE_BUCKET
    )

    print(
        "Object:",
        object_key
    )

    try:

        s3.upload_file(
            file_path,
            FILONE_BUCKET,
            object_key,

            ExtraArgs={
                "ContentType": "video/mp4"
            }
        )

        print(
            "✅ UPLOAD SUCCESS"
        )

        return object_key

    except Exception as e:

        print(
            "❌ FIL ONE UPLOAD ERROR:",
            repr(e)
        )

        raise


# ============================================================
# Create Temporary Download URL
# ============================================================

def create_download_url(object_key):
    """
    Create a presigned URL valid for 2 hours.
    """

    expire_seconds = 2 * 60 * 60

    print()
    print(
        "🔗 Creating presigned URL..."
    )

    url = s3.generate_presigned_url(
        ClientMethod="get_object",

        Params={
            "Bucket": FILONE_BUCKET,
            "Key": object_key
        },

        ExpiresIn=expire_seconds
    )

    print(
        "✅ URL CREATED"
    )

    print(
        "URL expires in:",
        expire_seconds,
        "seconds"
    )

    return url


# ============================================================
# Delete File From Fil One
# ============================================================

def delete_from_filo(object_key):
    """
    Delete object from Fil One.
    """

    try:

        print()
        print(
            "🗑 Deleting object from Fil One:"
        )

        print(
            object_key
        )

        s3.delete_object(
            Bucket=FILONE_BUCKET,
            Key=object_key
        )

        print(
            "✅ FIL ONE OBJECT DELETED"
        )

    except Exception as e:

        print(
            "❌ FIL ONE DELETE ERROR:",
            repr(e)
        )


# ============================================================
# Schedule Fil One Cleanup
# ============================================================

def schedule_cleanup(object_key):
    """
    Delete uploaded object after 2 hours.

    Important:
    This timer works while the Railway process is running.
    """

    cleanup_seconds = 2 * 60 * 60

    print(
        f"⏰ Cleanup scheduled in "
        f"{cleanup_seconds} seconds"
    )

    timer = threading.Timer(
        cleanup_seconds,
        delete_from_filo,
        args=(object_key,)
    )

    timer.daemon = True

    timer.start()


# ============================================================
# /start
# ============================================================

@bot.message_handler(
    commands=["start"]
)
def start(message):

    bot.send_message(
        message.chat.id,

        "سلام 👋\n\n"
        "لینک ویدیوی YouTube رو بفرست."
    )


# ============================================================
# Receive YouTube URL
# ============================================================

@bot.message_handler(
    func=lambda message: True
)
def handle_url(message):

    if not message.text:

        bot.send_message(
            message.chat.id,

            "❌ لطفاً لینک YouTube ارسال کن."
        )

        return

    url = message.text.strip()

    if not url.startswith(
        (
            "http://",
            "https://"
        )
    ):

        bot.send_message(
            message.chat.id,

            "❌ لطفاً لینک معتبر ارسال کن."
        )

        return

    status_message = bot.send_message(

        message.chat.id,

        "⏳ در حال دریافت اطلاعات ویدیو..."
    )

    try:

        # ====================================================
        # Get Video Information
        # ====================================================

        video_info, qualities = get_video_data(
            url
        )

        if not qualities:

            bot.edit_message_text(

                "❌ هیچ کیفیت قابل استفاده‌ای پیدا نشد.",

                message.chat.id,

                status_message.message_id
            )

            return

        # ====================================================
        # Save User Request
        # ====================================================

        user_data[
            message.from_user.id
        ] = {

            "url": url,

            "video_info": video_info,

            "qualities": qualities
        }

        # ====================================================
        # Video Information
        # ====================================================

        text = (

            f"<b>{video_info['title']}</b>\n\n"

            f"📺 کانال: "
            f"{video_info['channel']}\n"

            f"👁 بازدید: "
            f"{video_info['views']}\n"

            f"👍 لایک: "
            f"{video_info['likes']}\n"

            f"⏱ مدت: "
            f"{video_info['duration']} ثانیه\n\n"

            f"🎥 یک کیفیت را انتخاب کن:"
        )

        # ====================================================
        # Quality Buttons
        # ====================================================

        markup = types.InlineKeyboardMarkup(
            row_width=2
        )

        buttons = []

        for quality in qualities:

            buttons.append(

                types.InlineKeyboardButton(

                    f"{quality}p",

                    callback_data=(
                        f"quality:{quality}"
                    )
                )
            )

        markup.add(
            *buttons
        )

        bot.edit_message_text(

            text,

            message.chat.id,

            status_message.message_id,

            reply_markup=markup
        )

    except Exception as e:

        print()
        print(
            "❌ Downloader error:"
        )

        print(
            repr(e)
        )

        try:

            bot.edit_message_text(

                "❌ هنگام دریافت اطلاعات ویدیو "
                "خطایی رخ داد.",

                message.chat.id,

                status_message.message_id
            )

        except Exception:

            bot.send_message(

                message.chat.id,

                "❌ هنگام دریافت اطلاعات ویدیو "
                "خطایی رخ داد."
            )


# ============================================================
# Quality Selection
# ============================================================

@bot.callback_query_handler(

    func=lambda call:
        call.data.startswith(
            "quality:"
        )
)
def quality_selected(call):

    quality = call.data.split(
        ":",
        1
    )[1]

    user = user_data.get(
        call.from_user.id
    )

    if not user:

        bot.answer_callback_query(

            call.id,

            "اطلاعات این درخواست منقضی شده."
        )

        return

    bot.answer_callback_query(
        call.id
    )

    chat_id = call.message.chat.id

    url = user["url"]

    status_message = bot.send_message(

        chat_id,

        f"⏳ در حال دانلود "
        f"{quality}p..."
    )

    file_path = None

    object_key = None

    try:

        print()
        print("=" * 60)

        print(
            f"⬇️ Starting download: "
            f"{quality}p"
        )

        print("=" * 60)

        # ====================================================
        # Download Video
        # ====================================================

        file_path = download_video(

            url,

            quality
        )

        if not file_path:

            raise FileNotFoundError(
                "Download returned no file."
            )

        if not os.path.exists(
            file_path
        ):

            raise FileNotFoundError(
                "Downloaded file not found."
            )

        file_size = os.path.getsize(
            file_path
        )

        print(
            f"📦 File size: "
            f"{file_size / (1024 * 1024):.2f} MB"
        )

        # ====================================================
        # Upload To Fil One
        # ====================================================

        bot.edit_message_text(

            "📤 دانلود انجام شد.\n"
            "☁️ در حال آپلود روی سرور...",

            chat_id,

            status_message.message_id
        )

        object_key = upload_to_filo(
            file_path
        )

        # ====================================================
        # Create Download URL
        # ====================================================

        download_url = create_download_url(
            object_key
        )

        # ====================================================
        # Schedule Cleanup
        # ====================================================

        schedule_cleanup(
            object_key
        )

        # ====================================================
        # Send Link To User
        # ====================================================

        markup = types.InlineKeyboardMarkup()

        download_button = types.InlineKeyboardButton(

            "⬇️ دانلود ویدیو",

            url=download_url
        )

        markup.add(
            download_button
        )

        bot.edit_message_text(

            f"✅ <b>ویدیو آماده است!</b>\n\n"

            f"🎬 کیفیت: <b>{quality}p</b>\n"

            f"📦 حجم: "
            f"<b>{file_size / (1024 * 1024):.2f} MB</b>\n\n"

            f"⏳ این لینک تا <b>۲ ساعت</b> معتبر است.\n"

            f"بعد از آن فایل از سرور حذف می‌شود.",

            chat_id,

            status_message.message_id,

            reply_markup=markup
        )

        print()
        print(
            "✅ VIDEO READY"
        )

        print(
            "Object:",
            object_key
        )

        print(
            "Download URL created successfully."
        )

    except Exception as e:

        print()
        print(
            "❌ Download / Upload error:"
        )

        print(
            repr(e)
        )

        print()

        try:

            bot.edit_message_text(

                "❌ دانلود یا آپلود ویدیو "
                "ناموفق بود.",

                chat_id,

                status_message.message_id
            )

        except Exception:

            bot.send_message(

                chat_id,

                "❌ دانلود یا آپلود ویدیو "
                "ناموفق بود."
            )

    finally:

        # ====================================================
        # Delete Local Temporary File
        # ====================================================

        if (
            file_path
            and
            os.path.exists(file_path)
        ):

            try:

                os.remove(
                    file_path
                )

                print(
                    f"🗑 Deleted local file: "
                    f"{file_path}"
                )

            except Exception as e:

                print(
                    "Local file cleanup error:",
                    repr(e)
                )


# ============================================================
# Start Bot
# ============================================================

print()
print("=" * 60)
print("🤖 BOT IS STARTING...")
print("=" * 60)

print(
    "☁️ Storage: Fil One"
)

print(
    "🔗 Delivery: Presigned URL"
)

print(
    "⏳ URL lifetime: 2 hours"
)

print("=" * 60)


bot.infinity_polling(

    timeout=60,

    long_polling_timeout=60
)
