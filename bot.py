import subprocess
import os
import telebot
from telebot import types


# =========================
# Deno Test
# =========================

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


# =========================
# YouTube Connection Test
# =========================

try:
    result = subprocess.run(
        ["curl", "-4", "-I", "https://www.youtube.com"],
        capture_output=True,
        text=True,
        timeout=20
    )

    print("YOUTUBE CONNECTION TEST:")
    print(result.stdout)
    print(result.stderr)

except Exception as e:
    print("YOUTUBE TEST ERROR:", repr(e))


# =========================
# Downloader
# =========================

from downloader import get_video_data, download_video


# =========================
# Telegram Bot
# =========================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN پیدا نشد!")

bot = telebot.TeleBot(
    TOKEN,
    parse_mode="HTML"
)

user_data = {}


# =========================
# /start
# =========================

@bot.message_handler(commands=["start"])
def start(message):

    bot.send_message(
        message.chat.id,
        "سلام 👋\n"
        "لینک ویدیوی YouTube رو بفرست."
    )


# =========================
# Receive URL
# =========================

@bot.message_handler(func=lambda message: True)
def handle_url(message):

    if not message.text:
        bot.send_message(
            message.chat.id,
            "❌ لطفاً لینک YouTube ارسال کن."
        )
        return

    url = message.text.strip()

    if not url.startswith(("http://", "https://")):

        bot.send_message(
            message.chat.id,
            "❌ لطفاً لینک معتبر ارسال کن."
        )

        return

    bot.send_message(
        message.chat.id,
        "⏳ در حال دریافت اطلاعات ویدیو..."
    )

    try:

        video_info, qualities = get_video_data(url)

        if not qualities:

            bot.send_message(
                message.chat.id,
                "❌ کیفیت قابل استفاده‌ای پیدا نشد."
            )

            return

        user_data[message.from_user.id] = {
            "url": url,
            "video_info": video_info,
            "qualities": qualities
        }

        text = (
            f"<b>{video_info['title']}</b>\n\n"
            f"📺 کانال: {video_info['channel']}\n"
            f"👁 بازدید: {video_info['views']}\n"
            f"👍 لایک: {video_info['likes']}\n"
            f"⏱ مدت: {video_info['duration']} ثانیه\n\n"
            f"🎥 یک کیفیت را انتخاب کن:"
        )

        markup = types.InlineKeyboardMarkup(
            row_width=2
        )

        buttons = []

        for quality in qualities:

            buttons.append(
                types.InlineKeyboardButton(
                    f"{quality}p",
                    callback_data=f"quality:{quality}"
                )
            )

        markup.add(*buttons)

        bot.send_message(
            message.chat.id,
            text,
            reply_markup=markup
        )

    except Exception as e:

        print(
            "❌ Downloader error:",
            repr(e)
        )

        bot.send_message(
            message.chat.id,
            "❌ هنگام دریافت اطلاعات ویدیو خطایی رخ داد."
        )


# =========================
# Quality Selection
# =========================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("quality:")
)
def quality_selected(call):

    quality = call.data.split(":", 1)[1]

    user = user_data.get(
        call.from_user.id
    )

    if not user:

        bot.answer_callback_query(
            call.id,
            "اطلاعات این درخواست منقضی شده."
        )

        return

    bot.answer_callback_query(call.id)

    chat_id = call.message.chat.id

    url = user["url"]

    status_message = bot.send_message(
        chat_id,
        f"⏳ در حال دانلود کیفیت {quality}p..."
    )

    file_path = None

    try:

        # =========================
        # Download
        # =========================

        print(
            f"⬇️ Starting download: "
            f"{quality}p"
        )

        file_path = download_video(
            url,
            quality
        )

        print(
            f"📁 Downloaded file path: "
            f"{file_path}"
        )

        if not file_path:
            raise FileNotFoundError(
                "download_video returned empty path"
            )

        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Downloaded file not found: {file_path}"
            )

        # =========================
        # File Size
        # =========================

        file_size = os.path.getsize(
            file_path
        )

        file_size_mb = (
            file_size / 1024 / 1024
        )

        print(
            f"📦 File size: "
            f"{file_size} bytes "
            f"({file_size_mb:.2f} MB)"
        )

        # =========================
        # Prepare Upload
        # =========================

        bot.edit_message_text(
            "📤 دانلود انجام شد؛ "
            "در حال ارسال فایل...",
            chat_id,
            status_message.message_id
        )

        # =========================
        # Send Video
        # =========================

        print("📤 Sending video to Telegram...")

        try:

            with open(
                file_path,
                "rb"
            ) as video:

                bot.send_video(
                    chat_id,
                    video,
                    caption=f"🎬 کیفیت: {quality}p",
                    supports_streaming=True
                )

            print(
                "✅ Video sent successfully."
            )

        except Exception as video_error:

            print(
                "❌ send_video failed:",
                repr(video_error)
            )

            # =========================
            # Fallback: Send as Document
            # =========================

            print(
                "📤 Trying send_document fallback..."
            )

            try:

                with open(
                    file_path,
                    "rb"
                ) as document:

                    bot.send_document(
                        chat_id,
                        document,
                        caption=(
                            f"🎬 کیفیت: {quality}p\n"
                            f"📦 حجم: {file_size_mb:.2f} MB"
                        )
                    )

                print(
                    "✅ File sent successfully "
                    "as document."
                )

            except Exception as document_error:

                print(
                    "❌ send_document failed:",
                    repr(document_error)
                )

                raise RuntimeError(
                    "Telegram upload failed.\n"
                    f"send_video: {repr(video_error)}\n"
                    f"send_document: {repr(document_error)}"
                )

        # =========================
        # Success
        # =========================

        try:

            bot.delete_message(
                chat_id,
                status_message.message_id
            )

        except Exception as e:

            print(
                "⚠️ Status message delete failed:",
                repr(e)
            )

    except Exception as e:

        # =========================
        # Final Error
        # =========================

        print(
            "❌ Download/Upload error:",
            repr(e)
        )

        error_text = str(e)

        if "413" in error_text or "Request Entity Too Large" in error_text:

            user_message = (
                "❌ تلگرام فایل را به دلیل حجم "
                "درخواست قبول نکرد.\n\n"
                f"📦 حجم فایل: "
                f"{(
                    os.path.getsize(file_path) / 1024 / 1024
                ):.2f} MB"
                if file_path and os.path.exists(file_path)
                else
                "❌ تلگرام فایل را به دلیل حجم "
                "درخواست قبول نکرد."
            )

        else:

            user_message = (
                "❌ دانلود یا ارسال ویدیو ناموفق بود."
            )

        try:

            bot.edit_message_text(
                user_message,
                chat_id,
                status_message.message_id
            )

        except Exception as edit_error:

            print(
                "❌ Error message edit failed:",
                repr(edit_error)
            )

            try:

                bot.send_message(
                    chat_id,
                    user_message
                )

            except Exception as send_error:

                print(
                    "❌ Could not send error message:",
                    repr(send_error)
                )

    finally:

        # =========================
        # Cleanup
        # =========================

        if file_path and os.path.exists(file_path):

            try:

                os.remove(
                    file_path
                )

                print(
                    f"🗑 Deleted file: "
                    f"{file_path}"
                )

            except Exception as e:

                print(
                    "❌ File cleanup error:",
                    repr(e)
                )


# =========================
# Start Bot
# =========================

print(
    "🤖 Bot is starting..."
)

bot.infinity_polling()
