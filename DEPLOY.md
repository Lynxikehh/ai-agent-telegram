# Panduan Deploy ke VPS (Docker)

Panduan dari nol untuk menjalankan bot di VPS Linux (Ubuntu/Debian) memakai
Docker. Perkiraan waktu: 10–15 menit.

---

## Langkah 0 — Yang perlu disiapkan
- Token bot dari **@BotFather**
- Token langganan dari **`claude setup-token`** (lihat kotak di bawah)
- ID Telegram kamu (dari **@userinfobot**)
- Akses ke VPS (SSH atau web console penyedia)

> **Membuat token langganan:** jalankan `claude setup-token` di komputer yang
> punya browser DAN Claude Code CLI terpasang (mis. laptop kamu). Perintah ini
> login lewat browser lalu mencetak token (berlaku ~1 tahun). Salin token itu;
> nanti ditempel ke `.env` di VPS. VPS tidak punya browser, jadi token dibuat
> di komputermu, bukan di VPS.

---

## Langkah 1 — Masuk ke VPS lewat SSH
Dari komputer kamu:
```bash
ssh root@IP_VPS_KAMU
```
Ganti `IP_VPS_KAMU` dengan IP VPS (dan `root` dengan user kamu bila berbeda).

---

## Langkah 2 — Pasang Docker (kalau belum ada)
Cek dulu:
```bash
docker --version
```
Kalau belum terpasang, jalankan (Ubuntu/Debian):
```bash
curl -fsSL https://get.docker.com | sh
```
Pastikan plugin compose tersedia:
```bash
docker compose version
```

---

## Langkah 3 — Ambil kode dari GitHub
> Cara menaruh kode ini ke GitHub ada di bagian **"Mengunggah ke GitHub"** paling bawah.

Clone repo kamu (ganti URL dengan repo milikmu):
```bash
git clone https://github.com/USERNAME/NAMA-REPO.git
cd NAMA-REPO
```

---

## Langkah 4 — Isi konfigurasi (.env)
```bash
cp .env.example .env
nano .env
```
Isi minimal 3 baris ini, lalu simpan (`Ctrl+O`, `Enter`, `Ctrl+X`):
```
TELEGRAM_BOT_TOKEN=token_dari_botfather
CLAUDE_CODE_OAUTH_TOKEN=token_dari_claude_setup_token
ALLOWED_USER_IDS=123456789
```
> Jangan isi `ANTHROPIC_API_KEY` — kalau ada, ia menggantikan token langganan.

---

## Langkah 5 — Jalankan bot
```bash
docker compose up -d --build
```
Lihat log (pastikan tertulis "Bot berjalan"):
```bash
docker compose logs -f
```
Keluar dari tampilan log: `Ctrl+C` (bot tetap jalan di background).

Sekarang buka Telegram, kirim `/start` ke bot kamu. 🎉

---

## Perawatan harian

**Lihat status / log**
```bash
docker compose ps
docker compose logs -f
```

**Restart bot**
```bash
docker compose restart
```

**Hentikan bot**
```bash
docker compose down
```

**Update kode (setelah ada perubahan di GitHub)**
```bash
git pull
docker compose up -d --build
```

Data (memori & pengingat) tersimpan di Docker volume `bot-data`, aman saat
rebuild/restart.

---

## Troubleshooting
| Gejala | Penyebab & solusi |
|--------|-------------------|
| `Environment variable 'TELEGRAM_BOT_TOKEN' belum diisi` | `.env` belum lengkap. Edit lalu `docker compose up -d --build`. |
| Bot balas "kamu tidak punya akses" | ID kamu belum ada di `ALLOWED_USER_IDS`. Bot menampilkan ID kamu di pesan itu — salin ke `.env`. |
| Error `authentication` / `login` dari Claude | `CLAUDE_CODE_OAUTH_TOKEN` salah/kedaluwarsa. Buat ulang dengan `claude setup-token`. Pastikan `ANTHROPIC_API_KEY` tidak di-set. |
| Pengingat tidak berbunyi | Cek `TIMEZONE` di `.env` sudah benar (mis. `Asia/Jakarta`). |

Lihat error terbaru:
```bash
docker compose logs --tail=50
```

---

## Mengunggah kode ini ke GitHub

Kode ada di komputermu (`C:\AI Agent`). Ada dua cara menaruhnya ke GitHub:

### Cara A — Pakai Git (disarankan, mudah di-update nanti)
1. Pasang Git: https://git-scm.com/download/win , lalu buka **PowerShell** di folder `C:\AI Agent`.
2. Buat repo **kosong & privat** di https://github.com/new (jangan centang "Add README").
3. Jalankan (ganti URL dengan repo kamu):
```bash
git init
git add .
git commit -m "AI agent telegram awal"
git branch -M main
git remote add origin https://github.com/USERNAME/NAMA-REPO.git
git push -u origin main
```
> `.env` tidak ikut ter-upload karena sudah masuk `.gitignore` — ini memang disengaja demi keamanan. Isi `.env` langsung di VPS (Langkah 4).

### Cara B — Upload lewat web
1. Buat repo privat baru di GitHub.
2. Pilih **"uploading an existing file"**, seret semua file & folder `bot/`.
3. **Jangan** upload file `.env`.
