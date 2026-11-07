"""Titik masuk bot Telegram."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import config, database
from .agent import Brain
from .reminders import ReminderService

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("bot")

TELEGRAM_LIMIT = 4000  # batas aman di bawah 4096


def _authorized(update: Update) -> bool:
    if not config.ALLOWED_USER_IDS:
        return True  # tidak dibatasi
    user = update.effective_user
    return bool(user and user.id in config.ALLOWED_USER_IDS)


async def _reject(update: Update) -> None:
    uid = update.effective_user.id if update.effective_user else "?"
    await update.message.reply_text(
        "Maaf, kamu tidak punya akses ke bot ini.\n"
        f"ID Telegram kamu: {uid}\n"
        "Jika ini bot kamu, tambahkan ID ini ke ALLOWED_USER_IDS di file .env."
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _reject(update)
    await update.message.reply_text(
        f"Halo! Saya {config.ASSISTANT_NAME}, asisten pribadi kamu.\n\n"
        "Saya bisa:\n"
        "• Menjawab pertanyaan & membantu tugas apa pun\n"
        "• Riset di web (berita, harga, info terkini)\n"
        "• Mengingatkan aktivitas — cukup bilang 'ingatkan saya ...'\n\n"
        "Perintah:\n"
        "/reminders — lihat pengingat aktif\n"
        "/reset — hapus memori percakapan\n"
        "/help — bantuan"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _reject(update)
    await update.message.reply_text(
        "Kirim saja pesan seperti biasa dan saya akan membantu.\n\n"
        "Contoh:\n"
        "• 'Ingatkan saya meeting besok jam 10 pagi'\n"
        "• 'Cari harga emas hari ini'\n"
        "• 'Buatkan draft email untuk klien'\n\n"
        "/reminders — daftar pengingat\n"
        "/reset — mulai percakapan baru (hapus memori)"
    )


async def cmd_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _reject(update)
    service: ReminderService = context.application.bot_data["reminders"]
    await update.message.reply_text(service.list_reminders(update.effective_chat.id))


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _reject(update)
    brain: Brain = context.application.bot_data["brain"]
    await brain.reset(update.effective_chat.id)
    await update.message.reply_text("Memori percakapan dihapus. Mulai dari awal. 👍")


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return await _reject(update)

    chat_id = update.effective_chat.id
    user_text = update.message.text or ""

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    brain: Brain = context.application.bot_data["brain"]
    try:
        reply = await brain.handle(chat_id, user_text)
    except Exception:  # noqa: BLE001
        logger.exception("Gagal memproses pesan")
        await update.message.reply_text(
            "Maaf, terjadi kesalahan saat memproses. Coba lagi ya."
        )
        return

    for chunk in _split(reply, TELEGRAM_LIMIT):
        await update.message.reply_text(chunk)


def _split(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit:
            if current:
                chunks.append(current)
            # baris tunggal yang terlalu panjang dipotong keras
            while len(line) > limit:
                chunks.append(line[:limit])
                line = line[limit:]
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


async def _post_init(application: Application) -> None:
    service = ReminderService(application)
    application.bot_data["reminders"] = service
    application.bot_data["brain"] = Brain(service)
    restored = service.reschedule_pending()
    logger.info("Pengingat tertunda dijadwalkan ulang: %d", restored)


def main() -> None:
    database.init()

    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(_post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("reminders", cmd_reminders))
    application.add_handler(CommandHandler("reset", cmd_reset))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, on_message)
    )

    logger.info("Bot berjalan (model=%s, tz=%s)", config.CLAUDE_MODEL, config.TIMEZONE_NAME)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
