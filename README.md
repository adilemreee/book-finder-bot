# 📚 BookFinder Bot

Türk Telegram kanallarından PDF kitap arayan ve kullanıcıya ileten asenkron Telegram botu.

## Mimari

```
Kullanıcı → Aiogram Bot → Memory Cache → Pyrogram (Grup Arama) → PDF Gönderim (Zero-Download Copy)
```

| Katman        | Teknoloji             |
| ------------- | --------------------- |
| Bot Framework | Aiogram 3.x           |
| Grup Arama    | Pyrogram 2.x          |
| In-Memory Veri| Python dict           |
| Deployment    | Docker                |

## Kurulum

### 1. Gereksinimler

- Python 3.11+
- Telegram Bot Token (`@BotFather`)
- Telegram API ID & Hash (`my.telegram.org`)
- Gizli bir Telegram kanalı (Kasa/Depo olarak kullanılacak) ve kanalın ID'si. (Bot ve Pyrogram hesabı yönetici olmalı)

### 3. Ortam Değişkenleri

```bash
cp .env.example .env
```

`.env` dosyasını doldur:

```env
BOT_TOKEN=123456:ABC-DEF...
PYROGRAM_API_ID=12345678
PYROGRAM_API_HASH=abcdef1234567890
DUMP_CHANNEL_ID=-1001234567890
TARGET_CHATS=@kanal1,@kanal2,-1001234567890
```

> ⚠️ `TARGET_CHATS` içindeki kanallara/gruplara Pyrogram hesabınızın üye olması gerekir.

### 4. Çalıştırma

**Yerel:**

```bash
pip install -r requirements.txt
python -m src.main
```

İlk çalıştırmada Pyrogram telefon numarası ve doğrulama kodu isteyecektir.

**Docker:**

```bash
# İlk çalıştırmada session oluşturmak için yerel çalıştır,
# ardından Docker'a geç:
docker compose up -d --build
```

## Kullanım

| Komut         | Açıklama          |
| ------------- | ----------------- |
| `/start`      | Hoş geldin mesajı |
| `/help`       | Kullanım kılavuzu |
| `<kitap adı>` | PDF arama         |

## Dosya Yapısı

```
src/
├── main.py              # Giriş noktası
├── config.py            # Ortam değişkenleri
├── bot/
│   ├── handlers.py      # Komut ve mesaj handler'ları
│   ├── keyboards.py     # Inline butonlar
│   └── middlewares.py   # Rate limiting
├── search/
│   ├── engine.py        # Arama orkestratörü
│   └── telegram_source.py  # Pyrogram grup arama
├── cache/
│   └── memory_cache.py     # In-Memory önbellek (Sıfır İndirme)
└── utils/
    ├── logger.py        # Structured logging
    └── normalizer.py    # Türkçe sorgu normalizasyonu
```

## Yeni Kaynak Ekleme

`TARGET_CHATS` env değişkenine yeni kanal/grup ekle:

```env
TARGET_CHATS=@eski_kanal,@yeni_kanal,-100999999
```

## Lisans

MIT
