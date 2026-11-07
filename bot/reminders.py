"""Layanan pengingat: menjadwalkan & mengirim pengingat lewat Telegram.

Memakai JobQueue bawaan python-telegram-bot (berbasis APScheduler).
Pengingat disimpan di SQLite supaya tetap ada setelah bot di-restart.
"""
from __future__ import annotations

from datetime import datetime

from telegram.ext import Application, ContextTypes

from . import config, database


class ReminderService:
    def __init__(self, application: Application):
        self.app = application

    # --- API yang dipakai oleh tool executor ---

    def set_reminder(self, chat_id: int, user_id: int | None, due_at: str, message: str) -> str:
        try:
            due_dt = _parse_local_iso(due_at)
        except ValueError:
            return (
                "Format waktu tidak valid. Gunakan ISO 8601, "
                "contoh '2026-11-08T09:00:00'."
            )

        now = datetime.now(config.TZ)
        if due_dt <= now:
            return "Waktu pengingat sudah lewat. Berikan waktu di masa depan."

        reminder_id = database.add_reminder(chat_id, user_id, message, due_dt.timestamp())
        self._schedule(reminder_id, chat_id, message, due_dt)

        waktu = due_dt.strftime("%A, %d %B %Y %H:%M")
        return f"Pengingat #{reminder_id} dibuat untuk {waktu} ({config.TIMEZONE_NAME})."

    def list_reminders(self, chat_id: int) -> str:
        rows = database.list_pending_reminders(chat_id)
        if not rows:
            return "Tidak ada pengingat aktif."
        lines = ["Pengingat aktif:"]
        for r in rows:
            waktu = datetime.fromtimestamp(r["due_ts"], config.TZ).strftime(
                "%d %b %Y %H:%M"
            )
            lines.append(f"- #{r['id']} — {waktu}: {r['message']}")
        return "\n".join(lines)

    def cancel_reminder(self, chat_id: int, reminder_id: int) -> str:
        removed = database.delete_reminder(chat_id, reminder_id)
        if not removed:
            return f"Pengingat #{reminder_id} tidak ditemukan atau sudah berbunyi."
        for job in self.app.job_queue.get_jobs_by_name(_job_name(reminder_id)):
            job.schedule_removal()
        return f"Pengingat #{reminder_id} dibatalkan."

    # --- Internal ---

    def _schedule(self, reminder_id: int, chat_id: int, message: str, due_dt: datetime) -> None:
        self.app.job_queue.run_once(
            _fire_reminder,
            when=due_dt,
            name=_job_name(reminder_id),
            data={"reminder_id": reminder_id, "chat_id": chat_id, "message": message},
        )

    def reschedule_pending(self) -> int:
        """Muat ulang semua pengingat yang belum berbunyi saat startup."""
        now = datetime.now(config.TZ)
        count = 0
        for r in database.list_all_pending():
            due_dt = datetime.fromtimestamp(r["due_ts"], config.TZ)
            # Jika sudah lewat selama bot mati, kirim ~10 detik setelah start.
            # (angka = detik dari sekarang; datetime = waktu absolut)
            when = due_dt if due_dt > now else 10
            self.app.job_queue.run_once(
                _fire_reminder,
                when=when,
                name=_job_name(r["id"]),
                data={"reminder_id": r["id"], "chat_id": r["chat_id"], "message": r["message"]},
            )
            count += 1
        return count


def _job_name(reminder_id: int) -> str:
    return f"reminder_{reminder_id}"


def _parse_local_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=config.TZ)
    return dt


async def _fire_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data
    try:
        await context.bot.send_message(
            chat_id=data["chat_id"],
            text=f"⏰ Pengingat: {data['message']}",
        )
    finally:
        database.mark_reminder_fired(data["reminder_id"])
