import os
import html
import boto3

import telebot
from telebot import types
from botocore.client import Config

from downloader import get_video_data, download_video, get_video_comments


# ============================================================
# Environment
# ============================================================

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN پیدا نشد!")

FILONE_ACCESS_KEY = os.getenv("FILONE_ACCESS_KEY")
FILONE_SECRET_KEY = os.getenv("FILONE_SECRET_KEY")
FILONE_BUCKET = os.getenv("FILONE_BUCKET")
FILONE_ENDPOINT = os.getenv("FILONE_ENDPOINT")

try:
    FILONE_URL_EXPIRES = int(os.getenv("FILONE_URL_EXPIRES", "3600"))
except ValueError:
    FILONE_URL_EXPIRES = 3600
if FILONE_URL_EXPIRES <= 0:
    FILONE_URL_EXPIRES = 3600

for name, value in (
    ("FILONE_ACCESS_KEY", FILONE_ACCESS_KEY),
    ("FILONE_SECRET_KEY", FILONE_SECRET_KEY),
    ("FILONE_BUCKET", FILONE_BUCKET),
    ("FILONE_ENDPOINT", FILONE_ENDPOINT),
):
    if not value:
        raise RuntimeError(f"{name} پیدا نشد!")

try:
    TELEGRAM_DIRECT_VIDEO_LIMIT_MB = float(
        os.getenv("TELEGRAM_DIRECT_VIDEO_LIMIT_MB", "49.0")
    )
except ValueError:
    TELEGRAM_DIRECT_VIDEO_LIMIT_MB = 49.0


# ============================================================
# Telegram / Fil.one
# ============================================================

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

s3 = boto3.client(
    "s3",
    endpoint_url=FILONE_ENDPOINT,
    aws_access_key_id=FILONE_ACCESS_KEY,
    aws_secret_access_key=FILONE_SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name="eu-west-1",
)

user_data = {}


# ============================================================
# Helpers
# ============================================================

def escape_text(text):
    return html.escape(str(text or ""))


def format_number(value):
    try:
        return f"{int(value):,}"
    except Exception:
        return str(value or 0)


def format_mb(size):
    return size / 1024 / 1024


# ============================================================
# Upload to Fil.one
# ============================================================

def upload_to_filon(file_path, object_name):
    print(f"⬆️ Uploading playback object to Fil.one: {file_path}")

    # Keep a dedicated inline object for browser/online playback.
    s3.upload_file(
        file_path,
        FILONE_BUCKET,
        object_name,
        ExtraArgs={
            "ContentType": "video/mp4",
            "ContentDisposition": "inline",
        },
    )

    # A separate object is intentionally used for downloads.
    # This avoids relying on Fil.one honoring
    # ResponseContentDisposition on a presigned GET URL.
    download_object_name = object_name.rsplit("/", 1)[0] + "/download.mp4"

    print(f"⬆️ Uploading download object to Fil.one: {download_object_name}")
    s3.upload_file(
        file_path,
        FILONE_BUCKET,
        download_object_name,
        ExtraArgs={
            "ContentType": "application/octet-stream",
            "ContentDisposition": "attachment; filename=video.mp4",
        },
    )

    print("✅ UPLOAD SUCCESS")
    print(f"Bucket: {FILONE_BUCKET}")
    print(f"Playback object: {object_name}")
    print(f"Download object: {download_object_name}")

    playback_url = s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": FILONE_BUCKET,
            "Key": object_name,
        },
        ExpiresIn=FILONE_URL_EXPIRES,
    )

    download_url = s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": FILONE_BUCKET,
            "Key": download_object_name,
        },
        ExpiresIn=FILONE_URL_EXPIRES,
    )

    if not playback_url or not download_url:
        raise RuntimeError("Fil.one presigned URL generation failed.")

    print(
        "🔗 Presigned playback/download URLs generated "
        f"(expires in {FILONE_URL_EXPIRES}s)"
    )
    return playback_url, download_url


# ============================================================
# Telegram menu
# ============================================================

def setup_bot_commands():
    bot.set_my_commands([
        types.BotCommand("start", "شروع ربات"),
        types.BotCommand("help", "راهنما"),
    ])
    print("✅ Telegram menu configured.")


def main_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("▶️ شروع", callback_data="menu_start"),
        types.InlineKeyboardButton("ℹ️ راهنما", callback_data="menu_help"),
    )
    return markup


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "سلام 👋\n\n"
        "🎬 به ربات دانلود YouTube خوش آمدی.\n\n"
        "برای شروع روی «▶️ شروع» بزن یا لینک YouTube را ارسال کن.",
        reply_markup=main_menu(),
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "ℹ️ <b>راهنمای ربات</b>\n\n"
        "1️⃣ لینک YouTube را ارسال کن.\n"
        "2️⃣ اطلاعات ویدیو نمایش داده می‌شود.\n"
        "3️⃣ کیفیت موردنظر را انتخاب کن.\n"
        "4️⃣ ویدیو به فرمت سازگار با پخش آنلاین آماده می‌شود.\n"
        "5️⃣ لینک پخش آنلاین و لینک دانلود مستقیم ارائه می‌شود.\n\n"
        "💬 همچنین می‌توانی کامنت‌های ویدیو را مشاهده کنی."
    )


@bot.callback_query_handler(func=lambda call: call.data == "menu_start")
def menu_start(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "▶️ <b>شروع شد!</b>\n\nلینک YouTube را ارسال کن.")


@bot.callback_query_handler(func=lambda call: call.data == "menu_help")
def menu_help(call):
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "ℹ️ <b>راهنما</b>\n\nلینک YouTube را بفرست، سپس کیفیت ویدیو را انتخاب کن.",
    )


# ============================================================
# Receive YouTube URL
# ============================================================

@bot.message_handler(func=lambda message: True)
def handle_url(message):
    if not message.text:
        bot.send_message(message.chat.id, "❌ لطفاً لینک YouTube ارسال کن.")
        return

    url = message.text.strip()
    if not url.startswith(("http://", "https://")):
        bot.send_message(message.chat.id, "❌ لطفاً لینک معتبر ارسال کن.")
        return

    status = bot.send_message(message.chat.id, "⏳ در حال دریافت اطلاعات ویدیو...")

    try:
        video_info, quality_data = get_video_data(url)
        if not quality_data:
            raise RuntimeError("هیچ کیفیتی پیدا نشد.")

        user_data[message.from_user.id] = {
            "url": url,
            "video_info": video_info,
            "quality_data": quality_data,
        }

        title = escape_text(video_info["title"])
        channel = escape_text(video_info["channel"])
        text = (
            f"🎬 <b>{title}</b>\n\n"
            f"📺 کانال: {channel}\n"
            f"👁 بازدید: {format_number(video_info['views'])}\n"
            f"👍 لایک: {format_number(video_info['likes'])}\n"
            f"⏱ مدت: {video_info['duration_text']}\n\n"
            "🎥 <b>کیفیت را انتخاب کن:</b>"
        )

        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [
            types.InlineKeyboardButton(
                f"🎥 {item['height']}p • {item['size_text']}",
                callback_data=f"quality:{item['height']}",
            )
            for item in quality_data
        ]
        markup.add(*buttons)
        markup.add(types.InlineKeyboardButton("💬 مشاهده کامنت‌ها", callback_data="comments"))

        bot.edit_message_text(
            text,
            message.chat.id,
            status.message_id,
            reply_markup=markup,
        )

    except Exception as e:
        print("❌ Downloader error:", repr(e))
        try:
            bot.edit_message_text(
                "❌ هنگام دریافت اطلاعات ویدیو خطایی رخ داد.",
                message.chat.id,
                status.message_id,
            )
        except Exception:
            bot.send_message(message.chat.id, "❌ هنگام دریافت اطلاعات ویدیو خطایی رخ داد.")


# ============================================================
# Comments
# ============================================================

@bot.callback_query_handler(func=lambda call: call.data == "comments")
def comments_selected(call):
    bot.answer_callback_query(call.id, "⏳ در حال دریافت کامنت‌ها...")
    user = user_data.get(call.from_user.id)

    if not user:
        bot.send_message(
            call.message.chat.id,
            "❌ اطلاعات این ویدیو منقضی شده. لطفاً لینک را دوباره ارسال کن.",
        )
        return

    chat_id = call.message.chat.id
    status = bot.send_message(
        chat_id,
        "💬 در حال دریافت کامنت‌های ویدیو...\n⏳ ممکن است کمی طول بکشد.",
    )

    try:
        comments = get_video_comments(user["url"], max_comments=100)
        if not comments:
            bot.edit_message_text(
                "💬 برای این ویدیو کامنتی دریافت نشد یا YouTube اجازه استخراج کامنت‌ها را نداد.",
                chat_id,
                status.message_id,
            )
            return

        output = "💬 <b>کامنت‌های ویدیو</b>\n\n"
        for index, comment in enumerate(comments, start=1):
            block = (
                f"<b>{index}. {escape_text(comment['author'])}</b>\n"
                f"{escape_text(comment['text'])}\n"
                f"❤️ {format_number(comment['likes'])}\n\n"
            )
            if len(output + block) > 3800:
                bot.send_message(chat_id, output)
                output = ""
            output += block

        if output:
            bot.send_message(chat_id, output)
        try:
            bot.delete_message(chat_id, status.message_id)
        except Exception:
            pass

    except Exception as e:
        print("❌ Comments error:", repr(e))
        try:
            bot.edit_message_text("❌ دریافت کامنت‌ها ناموفق بود.", chat_id, status.message_id)
        except Exception:
            pass


# ============================================================
# Quality Selection
# ============================================================

@bot.callback_query_handler(func=lambda call: call.data.startswith("quality:"))
def quality_selected(call):
    quality = call.data.split(":", 1)[1]
    user = user_data.get(call.from_user.id)

    if not user:
        bot.answer_callback_query(call.id, "اطلاعات این درخواست منقضی شده.")
        return

    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    url = user["url"]
    status = bot.send_message(chat_id, f"⏳ در حال دانلود و آماده‌سازی {quality}p...")
    file_path = None

    try:
        print("=" * 60)
        print(f"⬇️ Starting download: {quality}p")

        file_path = download_video(url, quality)
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError("Downloaded file not found.")

        file_size = os.path.getsize(file_path)
        file_size_mb = format_mb(file_size)
        print(f"📦 Streamable file size: {file_size_mb:.2f} MB")

        bot.edit_message_text(
            "📥 دانلود و تبدیل انجام شد.\n☁️ در حال آپلود روی سرور امن...",
            chat_id,
            status.message_id,
        )

        video_id = user["video_info"].get("video_id") or "video"
        object_name = f"telegram-videos/{video_id}/{quality}p.mp4"
        playback_url, download_url = upload_to_filon(file_path, object_name)

        # Send native Telegram playback when the file is small enough.
        direct_sent = False
        if file_size_mb <= TELEGRAM_DIRECT_VIDEO_LIMIT_MB:
            try:
                print(f"📤 Sending native Telegram video ({file_size_mb:.2f} MB)...")
                with open(file_path, "rb") as video_file:
                    bot.send_video(
                        chat_id,
                        video_file,
                        caption=(
                            "▶️ <b>پخش مستقیم ویدیو</b>\n\n"
                            f"🎥 کیفیت: <b>{quality}p</b>\n"
                            f"📦 حجم: <b>{file_size_mb:.2f} MB</b>"
                        ),
                        supports_streaming=True,
                    )
                direct_sent = True
                print("✅ Native Telegram playback sent.")
            except Exception as e:
                print("⚠️ Native Telegram video send failed; falling back to Fil.one links:", repr(e))

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("▶️ پخش آنلاین از Fil.one", url=playback_url),
            types.InlineKeyboardButton("⬇️ دانلود مستقیم ویدیو", url=download_url),
        )

        if direct_sent:
            message_text = (
                "✅ <b>ویدیو آماده است!</b>\n\n"
                f"🎥 کیفیت: <b>{quality}p</b>\n"
                f"📦 حجم: <b>{file_size_mb:.2f} MB</b>\n\n"
                "▶️ ویدیو مستقیماً داخل تلگرام ارسال شد.\n"
                "⬇️ دکمه دانلود مستقیم، فایل را از Fil.one دریافت می‌کند."
            )
        else:
            message_text = (
                "✅ <b>ویدیو آماده است!</b>\n\n"
                f"🎥 کیفیت: <b>{quality}p</b>\n"
                f"📦 حجم: <b>{file_size_mb:.2f} MB</b>\n\n"
                "▶️ برای پخش آنلاین از گزینه پخش استفاده کن.\n"
                "⬇️ برای دریافت فایل از گزینه دانلود مستقیم استفاده کن."
            )

        bot.send_message(chat_id, message_text, reply_markup=markup)

        try:
            bot.delete_message(chat_id, status.message_id)
        except Exception:
            pass

        print("✅ Playback and download links sent.")

    except Exception as e:
        print("❌ Download / Upload error:", repr(e))
        try:
            bot.edit_message_text(
                "❌ دانلود یا آپلود ویدیو ناموفق بود.",
                chat_id,
                status.message_id,
            )
        except Exception:
            bot.send_message(chat_id, "❌ دانلود یا آپلود ویدیو ناموفق بود.")

    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑 Deleted: {file_path}")
            except Exception as e:
                print("File cleanup error:", repr(e))


# ============================================================
# Startup
# ============================================================

print("🤖 Bot is starting...")
try:
    setup_bot_commands()
except Exception as e:
    print("⚠️ Menu setup error:", repr(e))

bot.infinity_polling(timeout=60, long_polling_timeout=60)
