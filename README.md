# AI Agent Telegram (powered by Claude)

Asisten pribadi di Telegram, ditenagai Claude (Anthropic). Bisa menjawab apa
saja, riset di web, dan mengingatkan aktivitas. Dirancang untuk jalan 24/7 di
VPS lewat Docker.

## Fitur
- 💬 **Chat cerdas** dengan memori percakapan (ingat konteks sebelumnya)
- 🔎 **Riset web** otomatis untuk info terkini (berita, harga, fakta)
- ⏰ **Pengingat** — "ingatkan saya meeting besok jam 10", tahan restart
- 🔒 **Privat** — hanya ID Telegram kamu yang bisa memakainya

## Struktur
```
bot/
  config.py      # baca konfigurasi dari .env
  database.py    # SQLite: memori + pengingat
  agent.py       # koneksi ke Claude + definisi tool
  reminders.py   # penjadwalan pengingat
  main.py        # bot Telegram (titik masuk)
Dockerfile
docker-compose.yml
.env.example      # contoh konfigurasi (salin jadi .env)
```

## Persiapan (sebelum deploy)

### 1. Buat bot Telegram
1. Buka Telegram, chat **@BotFather**
2. Kirim `/newbot`, ikuti instruksinya
3. Salin **token** yang diberikan (bentuknya `123456:ABC-...`)

### 2. Buat token langganan Claude Code
Bot ini memakai **langganan Claude Code** kamu (Pro/Max/Team/Enterprise),
bukan API berbayar terpisah. Caranya di komputer yang punya browser dan Claude
Code (CLI) terpasang:
```bash
claude setup-token
```
Perintah ini membuka browser untuk login, lalu **mencetak token** di terminal
(berlaku ~1 tahun). Salin token itu — nanti diisi ke `CLAUDE_CODE_OAUTH_TOKEN`.

> ⚠️ **Jangan** mengisi `ANTHROPIC_API_KEY`. Kalau variabel itu ada, ia akan
> dipakai menggantikan token langganan.

### 3. Cari ID Telegram kamu
Cara termudah: jalankan bot dulu (langkah deploy di bawah) tanpa mengisi
`ALLOWED_USER_IDS`, kirim pesan ke bot, nanti bot menampilkan ID kamu —
ATAU chat **@userinfobot** di Telegram. Masukkan angka itu ke `ALLOWED_USER_IDS`.

## Menjalankan dengan Docker (di VPS)

```bash
cp .env.example .env
nano .env            # isi TELEGRAM_BOT_TOKEN, CLAUDE_CODE_OAUTH_TOKEN, ALLOWED_USER_IDS
docker compose up -d --build
docker compose logs -f
```

Panduan deploy VPS lengkap (dari nol) ada di **[DEPLOY.md](DEPLOY.md)**.

## Perintah bot
| Perintah | Fungsi |
|----------|--------|
| `/start` | Perkenalan |
| `/help` | Bantuan |
| `/reminders` | Lihat pengingat aktif |
| `/reset` | Hapus memori percakapan |

Pesan biasa langsung dijawab oleh asisten.

## Biaya & batasan
Bot memakai **kuota langganan Claude Code** kamu (bukan bayar per-pakai).
Artinya tidak ada tagihan API terpisah, tetapi pemakaian dibatasi limit
langgananmu. Untuk hemat kuota, set `CLAUDE_MODEL=sonnet` di `.env`.
Hanya untuk pemakaian **pribadi** — jika nanti dipakai orang lain/dikomersialkan,
wajib pindah ke API key sesuai aturan Anthropic.

## Keamanan
- File `.env` berisi rahasia — **jangan** di-commit (sudah di `.gitignore`).
- Bot hanya melayani ID di `ALLOWED_USER_IDS`.
