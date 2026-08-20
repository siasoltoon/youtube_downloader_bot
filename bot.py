
import subprocess
import os
import telebot
from telebot import types

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

    print(
        "DENO TEST ERROR:",
        repr(e)
    )


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

        first_line = (
            result.stdout
            .splitlines()[0]
        )

        print(
            first_line
        )

    else:

        print(
            result.stderr
        )

except Exception as e:

    print(
        "FFMPEG TEST ERROR:",
        repr(e)
    )


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

    print(
        "YOUTUBE CONNECTION TEST:"
    )

    print(
        result.stdout
    )

    print(
        result.stderr
    )

except Exception as e:

    print(
        "YOUTUBE TEST ERROR:",
        repr(e)
    )


# ============================================================
# Telegram Bot
# ============================================================

TOKEN = os.getenv(
    "BOT_TOKEN"
)

if not TOKEN:

    raise RuntimeError(
        "BOT_TOKEN پیدا نشد!"
    )


bot = telebot.TeleBot(

    TOKEN,

    parse_mode="HTML"

)


# ============================================================
# User data
# ============================================================

user_data = {}


# ============================================================
# /start
# ============================================================

@bot.message_handler(
    commands=["start"]
)
def start(message):

    bot.send_message(

        message.chat.id,

        "سلام 👋\n"
        "لینک ویدیوی YouTube رو بفرست."

    )


# ============================================================
# Receive URL
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

        video_info, qualities = (
            get_video_data(url)
        )

        if not qualities:

            bot.edit_message_text(

                "❌ هیچ کیفیت قابل استفاده‌ای پیدا نشد.",

                message.chat.id,

                status_message.message_id

            )

            return

        # ====================================================
        # Save user request
        # ====================================================

        user_data[
            message.from_user.id
        ] = {

            "url": url,

            "video_info": video_info,

            "qualities": qualities

        }

        # ====================================================
        # Video information
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
        # Quality buttons
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

                "❌ هنگام دریافت اطلاعات ویدیو خطایی رخ داد.",

                message.chat.id,

                status_message.message_id

            )

        except Exception:

            bot.send_message(

                message.chat.id,

                "❌ هنگام دریافت اطلاعات ویدیو خطایی رخ داد."

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

    try:

        print()
        print("=" * 60)

        print(
            f"⬇️ Starting download: "
            f"{quality}p"
        )

        # ====================================================
        # Download
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
        # Upload to Telegram
        # ====================================================

        bot.edit_message_text(

            "📤 دانلود انجام شد؛ "
            "در حال ارسال فایل...",

            chat_id,

            status_message.message_id

        )

        with open(
            file_path,
            "rb"
        ) as video:

            bot.send_video(

                chat_id,

                video,

                caption=(
                    f"🎬 کیفیت: "
                    f"{quality}p"
                ),

                supports_streaming=True

            )

        # ====================================================
        # Delete status message
        # ====================================================

        try:

            bot.delete_message(

                chat_id,

                status_message.message_id

            )

        except Exception as e:

            print(

                "Status delete error:",
                repr(e)

            )

        print(
            "✅ Video sent successfully."
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

                "❌ دانلود یا ارسال ویدیو ناموفق بود.",

                chat_id,

                status_message.message_id

            )

        except Exception:

            bot.send_message(

                chat_id,

                "❌ دانلود یا ارسال ویدیو ناموفق بود."

            )

    finally:

        # ====================================================
        # Delete temporary file
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

                    f"🗑 Deleted: "
                    f"{file_path}"

                )

            except Exception as e:

                print(

                    "File cleanup error:",
                    repr(e)

                )


# ============================================================
# Start Bot
# ============================================================

print(
    "🤖 Bot is starting..."
)

bot.infinity_polling(

    timeout=60,

    long_polling_timeout=60

)

