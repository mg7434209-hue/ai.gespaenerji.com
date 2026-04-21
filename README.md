
# Gespa OS

Mustafa Göksoy'un kişisel CEO asistanı — AI departmanları + workspace sistemi. Solar, Superonline bayi, hukuk, sigorta, turizm ve e-ticaret iş kollarını tek merkezden yönetir.

**Stack:** FastAPI + PostgreSQL + React + Vite + TailwindCSS
**Deploy:** Railway (tek servis, Dockerfile build)
**Domain:** os.gespaenerji.com

---

## 🚀 Deploy Adımları (10 dakika)

### 1. GitHub'a Push

```bash
cd gespa-os
git init
git add .
git commit -m "Initial commit - Gespa OS v0.1"
git branch -M main
git remote add origin https://github.com/mg7434209-hue/ai.gespaenerji.com.git
git push -u origin main
```

### 2. Railway'de Proje Oluştur

1. https://railway.app → **New Project** → **Deploy from GitHub repo**
2. Repo seç → Railway otomatik olarak `Dockerfile`'ı tanıyıp build'e başlar

### 3. PostgreSQL Ekle

1. Railway projesinde **+ New** → **Database** → **Add PostgreSQL**
2. Postgres servisi hazır olduğunda `DATABASE_URL` variable'ı paylaşılır

### 4. Environment Variables

Web servisinin **Variables** sekmesine ekle:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
JWT_SECRET=<64-karakterli-random-string>
ADMIN_EMAIL=mustafa@gespa.com
ADMIN_PASSWORD=<güçlü-şifre>
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
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
   - Proxy: **DNS only** (gri bulut) — ilk deploy için; SSL oturunca turuncuya alabilirsin

### 6. İlk Giriş

https://os.gespaenerji.com adresine git, Variables'daki email/şifre ile giriş yap.

---

## 🏗️ Mimari

```
gespa-os/
├── apps/
│   ├── api/          # FastAPI backend
│   │   ├── main.py
│   │   ├── app/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   ├── seed.py
│   │   │   ├── auth/
│   │   │   └── routers/
│   │   └── requirements.txt
│   └── web/          # React + Vite frontend
│       ├── index.html
│       └── src/
├── Dockerfile        # Multi-stage build (Node + Python)
└── README.md
```

---

## 🗺️ Yol Haritası

- ✅ **Hafta 1:** Auth, dashboard iskeleti, 6 workspace + 12 AI ajan seed — **canlıda**
- 🔄 **Hafta 2:** Dashboard v2 (hava/döviz/haber/viski saati) + WhatsApp Business API entegrasyonu
- ⏳ **Hafta 3:** Email Asistanı (Gmail MCP) + Satış Uzmanı AI ajanı aktif
- ⏳ **Hafta 4:** CRM + Takvim + sabah brief otomatik mail
- 🔜 **Faz 2 (Ay 2-3):** Ses kayıt + özet, AI karar desteği, telefon çağrı entegrasyonu
- 🔜 **Faz 3 (Ay 4+):** SolarAnaliz/TrafikRehber/tarifesec API entegrasyonları, multi-tenant SaaS katmanı

---

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

---

## 📄 Lisans

Özel kullanım — Gespa bünyesinde geliştirilmiştir.
