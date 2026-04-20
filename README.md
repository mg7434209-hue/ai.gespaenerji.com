# Göksoylar OS

Tek kullanıcı iç yönetim platformu — AI departmanları + workspace sistemi.

**Stack:** FastAPI + PostgreSQL + React + Vite + TailwindCSS
**Deploy:** Railway (tek servis, monorepo)
**Domain:** os.gespaenerji.com

---

## 🚀 Deploy Adımları (10 dakika)

### 1. GitHub'a Push

```bash
cd goksoylar-os
git init
git add .
git commit -m "Initial commit - Göksoylar OS v0.1"
git branch -M main
git remote add origin https://github.com/mg7434209-hue/goksoylar-os.git
git push -u origin main
```

### 2. Railway'de Proje Oluştur

1. https://railway.app → **New Project** → **Deploy from GitHub repo**
2. `goksoylar-os` reposunu seç
3. Railway otomatik olarak `nixpacks.toml`'u tanıyıp build'e başlar

### 3. PostgreSQL Ekle

1. Railway projesinde **+ New** → **Database** → **Add PostgreSQL**
2. PostgreSQL servisi oluştuğunda otomatik olarak `DATABASE_URL` variable'ı paylaşılır

### 4. Environment Variables

Web servisinin **Variables** sekmesine ekle:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
JWT_SECRET=<64-karakterli-random-string>
ADMIN_EMAIL=mustafa@goksoylar.com
ADMIN_PASSWORD=<güçlü-şifre>
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
ENVIRONMENT=production
```

**JWT_SECRET üretmek için:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Custom Domain

1. Web servisi → **Settings** → **Networking** → **Custom Domain**
2. `os.gespaenerji.com` ekle
3. Cloudflare DNS'te CNAME kaydı oluştur:
   - Name: `os`
   - Target: Railway'in verdiği CNAME (örn. `xxx.up.railway.app`)
   - Proxy: **DNS only** (gri bulut) — ilk deploy için; sonra turuncuya alabilirsin

### 6. İlk Giriş

https://os.gespaenerji.com adresine git, `.env`'de belirlediğin email/şifre ile giriş yap.

---

## 🏗️ Mimari

```
goksoylar-os/
├── apps/
│   ├── api/          # FastAPI backend
│   │   ├── main.py
│   │   ├── app/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   ├── auth/
│   │   │   └── routers/
│   │   └── requirements.txt
│   └── web/          # React + Vite frontend
│       └── src/
├── nixpacks.toml     # Railway build config
├── railway.json
└── package.json
```

## 🗺️ Yol Haritası

- ✅ **Faz 1 Hafta 1:** Auth, dashboard iskeleti, Superonline workspace temeli (şu an buradayız)
- ⏳ **Hafta 2:** Lead CRUD + WhatsApp entegrasyonu
- ⏳ **Hafta 3:** Email Asistanı + Satış Uzmanı ajanları
- ⏳ **Hafta 4:** Teklif Motoru + custom domain + cilalar
- 🔜 **Faz 2:** Kalan 10 AI ajanı
- 🔜 **Faz 3:** SolarAnaliz/TrafikRehber/tarifesec API entegrasyonları

## 🔧 Lokal Geliştirme

```bash
# Backend
cd apps/api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (yeni terminal)
cd apps/web
npm install
npm run dev   # localhost:5173
```

Lokal `.env` için `.env.example`'ı `apps/api/.env` olarak kopyala ve doldur.
