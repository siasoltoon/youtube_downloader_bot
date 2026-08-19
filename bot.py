import os
import telebot
from telebot import types

from downloader import get_video_data


TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN پیدا نشد!")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ذخیره موقت اطلاعات کاربران
user_data = {}


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "سلام کصکش\n"
        "لینک ویدیوی کصشرتو بفرست"
    )


@bot.message_handler(func=lambda message: True)
def handle_url(message):

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

        # ذخیره اطلاعات برای کاربر
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

        markup = types.InlineKeyboardMarkup(row_width=2)

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

        print("Downloader error:", repr(e))

        bot.send_message(
            message.chat.id,
            "❌ هنگام دریافت اطلاعات ویدیو خطایی رخ داد."
        )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("quality:")
)
def quality_selected(call):

    quality = call.data.split(":")[1]

    user = user_data.get(call.from_user.id)

    if not user:
        bot.answer_callback_query(
            call.id,
            "اطلاعات این درخواست منقضی شده."
        )
        return

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        f"✅ کیفیت {quality}p انتخاب شد.\n"
        f"⏳ در مرحله بعد دانلود را اضافه می‌کنیم..."
    )


print("🤖 Bot is starting...")

bot.infinity_polling()
