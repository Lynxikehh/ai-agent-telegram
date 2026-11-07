"""Otak bot: memakai Claude Agent SDK (Claude Code) dengan token langganan.

Auth lewat environment variable CLAUDE_CODE_OAUTH_TOKEN (dibuat dengan
`claude setup-token`). PENTING: ANTHROPIC_API_KEY tidak boleh di-set, karena
ia menang dari token langganan.

Setiap chat punya satu ClaudeSDKClient yang dipertahankan hidup -> memori
percakapan ditangani native oleh SDK selama bot berjalan.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    create_sdk_mcp_server,
    tool,
)

from . import config

# Tool bawaan Claude Code yang TIDAK kita izinkan (biar bot aman & fokus).
# Nama kosong (bare name) menghapus tool dari konteks bahkan di bypassPermissions.
_DISALLOWED_TOOLS = [
    "Bash", "BashOutput", "KillShell", "KillBash",
    "Read", "Write", "Edit", "MultiEdit", "NotebookEdit",
    "Glob", "Grep", "Task", "TodoWrite", "WebFetch",
    "SlashCommand", "ExitPlanMode",
]

# Tool yang diizinkan jalan tanpa konfirmasi.
_ALLOWED_TOOLS = [
    "WebSearch",
    "mcp__reminders__set_reminder",
    "mcp__reminders__list_reminders",
    "mcp__reminders__cancel_reminder",
]


def _system_prompt() -> str:
    return (
        f"Kamu adalah {config.ASSISTANT_NAME}, asisten pribadi yang cerdas dan "
        "membantu, berjalan di dalam Telegram untuk SATU pemilik. Kamu membantu "
        "dalam segala hal: menjawab pertanyaan, riset, mengerjakan tugas, "
        "menulis, analisis, dan mengingatkan aktivitas.\n\n"
        "Panduan:\n"
        "- Balas dalam bahasa yang dipakai user (biasanya Bahasa Indonesia).\n"
        "- Ringkas, jelas, langsung membantu, format rapi.\n"
        "- Untuk info terkini/harga/berita/fakta yang perlu diverifikasi, pakai "
        "tool WebSearch lalu sebutkan sumbernya.\n"
        "- Untuk pengingat, pakai tool set_reminder / list_reminders / "
        "cancel_reminder. Hitung waktu absolut dari 'Waktu sekarang' yang "
        "diberikan di tiap pesan. Konfirmasikan singkat setelah membuat pengingat.\n"
        "- Jangan mengarang. Kalau tidak yakin, cari tahu atau katakan terus terang.\n"
        f"- Zona waktu pemilik: {config.TIMEZONE_NAME}."
    )


class Brain:
    """Mengelola satu ClaudeSDKClient per chat beserta tool pengingatnya."""

    def __init__(self, reminder_service: Any):
        self._reminders = reminder_service
        self._clients: dict[int, ClaudeSDKClient] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock(self, chat_id: int) -> asyncio.Lock:
        if chat_id not in self._locks:
            self._locks[chat_id] = asyncio.Lock()
        return self._locks[chat_id]

    def _build_options(self, chat_id: int) -> ClaudeAgentOptions:
        service = self._reminders

        @tool("set_reminder", "Jadwalkan pengingat untuk user. due_at = waktu "
              "ISO 8601 lokal (contoh '2026-11-08T09:00:00'), message = isi pengingat.",
              {"due_at": str, "message": str})
        async def set_reminder(args: dict[str, Any]) -> dict[str, Any]:
            text = service.set_reminder(chat_id, None, args["due_at"], args["message"])
            return {"content": [{"type": "text", "text": text}]}

        @tool("list_reminders", "Tampilkan daftar pengingat aktif user.", {})
        async def list_reminders(args: dict[str, Any]) -> dict[str, Any]:
            return {"content": [{"type": "text", "text": service.list_reminders(chat_id)}]}

        @tool("cancel_reminder", "Batalkan pengingat berdasarkan ID.",
              {"reminder_id": int})
        async def cancel_reminder(args: dict[str, Any]) -> dict[str, Any]:
            text = service.cancel_reminder(chat_id, int(args["reminder_id"]))
            return {"content": [{"type": "text", "text": text}]}

        server = create_sdk_mcp_server(
            name="reminders",
            version="1.0.0",
            tools=[set_reminder, list_reminders, cancel_reminder],
        )

        opts: dict[str, Any] = {
            "system_prompt": _system_prompt(),
            "mcp_servers": {"reminders": server},
            "allowed_tools": _ALLOWED_TOOLS,
            "disallowed_tools": _DISALLOWED_TOOLS,
            "permission_mode": "bypassPermissions",
            "setting_sources": [],  # jangan muat settings/CLAUDE.md dari disk
            "cwd": "/data",
            "env": {"CLAUDE_CODE_OAUTH_TOKEN": config.CLAUDE_CODE_OAUTH_TOKEN},
        }
        if config.CLAUDE_MODEL:
            opts["model"] = config.CLAUDE_MODEL
        return ClaudeAgentOptions(**opts)

    async def _get_client(self, chat_id: int) -> ClaudeSDKClient:
        client = self._clients.get(chat_id)
        if client is None:
            client = ClaudeSDKClient(options=self._build_options(chat_id))
            await client.connect()
            self._clients[chat_id] = client
        return client

    async def reset(self, chat_id: int) -> None:
        async with self._lock(chat_id):
            client = self._clients.pop(chat_id, None)
            if client is not None:
                try:
                    await client.disconnect()
                except Exception:  # noqa: BLE001
                    pass

    async def handle(self, chat_id: int, user_text: str) -> str:
        now = datetime.now(config.TZ)
        prompt = (
            f"[Waktu sekarang: {now.strftime('%A, %d %B %Y %H:%M')} "
            f"({config.TIMEZONE_NAME}); ISO {now.strftime('%Y-%m-%dT%H:%M:%S')}]\n\n"
            f"{user_text}"
        )

        async with self._lock(chat_id):
            try:
                return await self._run(chat_id, prompt)
            except Exception:  # noqa: BLE001
                # Sesi mungkin rusak -> bangun ulang sekali.
                await self._force_reset(chat_id)
                return await self._run(chat_id, prompt)

    async def _run(self, chat_id: int, prompt: str) -> str:
        client = await self._get_client(chat_id)
        await client.query(prompt)

        texts: list[str] = []
        final_result: str | None = None
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock) and block.text:
                        texts.append(block.text)
            elif isinstance(message, ResultMessage):
                final_result = message.result

        answer = (final_result or "\n".join(texts)).strip()
        return answer or "(tidak ada jawaban)"

    async def _force_reset(self, chat_id: int) -> None:
        client = self._clients.pop(chat_id, None)
        if client is not None:
            try:
                await client.disconnect()
            except Exception:  # noqa: BLE001
                pass
