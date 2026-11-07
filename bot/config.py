"""Konfigurasi bot, dibaca dari environment variable (file .env)."""
from __future__ import annotations

import os
from zoneinfo import ZoneInfo


def _get_required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Environment variable '{name}' belum diisi. "
            f"Cek file .env Anda."
        )
    return value


# --- Kredensial wajib ---
TELEGRAM_BOT_TOKEN: str = _get_required("TELEGRAM_BOT_TOKEN")
# Token langganan dari `claude setup-token`. Dipakai oleh Claude Agent SDK.
# JANGAN set ANTHROPIC_API_KEY di environment — ia akan menang dari token ini.
CLAUDE_CODE_OAUTH_TOKEN: str = _get_required("CLAUDE_CODE_OAUTH_TOKEN")

# --- Pengaturan model ---
# Kosong = biarkan Claude Code memilih default langganan. Bisa diisi alias
# "sonnet" / "opus" / "haiku" (opus lebih cepat habiskan kuota langganan).
CLAUDE_MODEL: str = os.environ.get("CLAUDE_MODEL", "").strip()

# --- Identitas & bahasa ---
ASSISTANT_NAME: str = os.environ.get("ASSISTANT_NAME", "Asisten")

# --- Zona waktu (untuk pengingat) ---
TIMEZONE_NAME: str = os.environ.get("TIMEZONE", "Asia/Jakarta")
TZ = ZoneInfo(TIMEZONE_NAME)

# --- Penyimpanan ---
DB_PATH: str = os.environ.get("DB_PATH", "/data/bot.db")

# --- Memori percakapan ---
# Berapa banyak pesan terakhir (user + asisten) yang dikirim sebagai konteks.
MAX_HISTORY_MESSAGES: int = int(os.environ.get("MAX_HISTORY_MESSAGES", "40"))

# --- Keamanan: hanya user ini yang boleh memakai bot ---
# Isi dengan ID Telegram Anda, pisahkan koma jika lebih dari satu.
# Kosongkan HANYA jika bot boleh dipakai siapa saja (tidak disarankan).
_allowed_raw = os.environ.get("ALLOWED_USER_IDS", "").strip()
ALLOWED_USER_IDS: set[int] = {
    int(x) for x in _allowed_raw.replace(";", ",").split(",") if x.strip()
}
