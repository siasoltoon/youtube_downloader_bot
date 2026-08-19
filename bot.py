import os
import telebot

from downloader import get_video_data


TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN پیدا نشد!")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "سلام 👋\n"
        "لینک ویدیو رو بفرست تا اطلاعات ویدیو رو بررسی کنم."
    )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()

    if not url.startswith(("http://", "https://")):
        bot.send_message(
            message.chat.id,
            "❌ لطفاً یک لینک معتبر ارسال کن."
        )
        return

    bot.send_message(
        message.chat.id,
        "⏳ در حال بررسی لینک..."
    )

    try:
        video_info, qualities = get_video_data(url)

        text = (
            f"<b>{video_info['title']}</b>\n\n"
            f"📺 کانال: {video_info['channel']}\n"
            f"👁 بازدید: {video_info['views']}\n"
            f"👍 لایک: {video_info['likes']}\n"
            f"⏱ مدت: {video_info['duration']} ثانیه\n\n"
            f"🎥 کیفیت‌های موجود:\n"
        )

        if qualities:
            text += "\n".join(
                f"• {quality}p"
                for quality in qualities
            )
        else:
            text += "کیفیت مناسبی پیدا نشد."

        bot.send_message(message.chat.id, text)

    except Exception as e:
        print("Downloader error:", repr(e))

        bot.send_message(
            message.chat.id,
            "❌ هنگام بررسی ویدیو مشکلی پیش آمد."
        )


print("🤖 Bot is starting...")

bot.infinity_polling()
