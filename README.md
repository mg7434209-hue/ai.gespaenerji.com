
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

## ⚖️ Hukuk Ofisi — avukat ajan serisi

`/hukuk` menüsü, uzmanlık alanına göre ayrılmış **23 avukat ajanı** barındırır:

| Departman | Ajanlar |
|---|---|
| Ofis Yönetimi | Baş Hukuk Müşaviri · Dilekçe Yazarı · Mevzuat Araştırmacısı · Dosya Takip Asistanı |
| Dava & Uyuşmazlık | Dava Stratejisti · Ceza Avukatı · Tüketici Hakları Avukatı |
| İcra & Alacak | İcra & İflas Avukatı · Alacak & Tahsilat Avukatı |
| Ticari & Kurumsal | Sözleşme · Şirketler · İş Hukuku · KVKK & Bilişim · Marka & Fikri Mülkiyet |
| Kişi, Aile & Miras | Aile · Miras · Gayrimenkul & Kira · Sigorta & Tazminat |
| Kamu, İdare & Vergi | Trafik & İdari Ceza · Vergi · İdare · Enerji Mevzuatı (GES) · İhale & Taşınmaz |

**Dört çalışma modu:** `danisma` (değerlendirme + yol haritası) · `dilekce` (belge taslağı) ·
`inceleme` (sözleşme/belge risk analizi) · `arastirma` (mevzuat derlemesi).

### Hukuk Ofisi ekranları
`/hukuk` **Kadro** · `/hukuk/belge` **Belge Analizi** · `/hukuk/dosyalar` **Dosyalar** ·
`/hukuk/sureler` **Süreler** · `/hukuk/sablonlar` **Şablonlar** · `/hukuk/kurul` **Kurul**

### 📎 Belge Analizi — dosyayı yükle, gerisini sistem yapsın (`/hukuk/belge`)
Tebligat, ödeme emri, ihtarname, sözleşme veya ceza tutanağını yükle; sistem iki kademede çalışır:

1. **Triyaj** — belgeyi okur, türünü, taraflarını, tarihlerini, tutarlarını ve **belgeden çıkan
   süreyi** çıkarır, hangi avukat ajanına gideceğine karar verir (aciliyet + güven skoruyla).
2. **Analiz** — seçilen ajan belgeyi baştan inceler ve tam değerlendirmeyi üretir.

Ajanı elle de seçebilirsin; ayrıca herhangi bir ajanın kendi sayfasındaki forma belge iliştirip
soru sorabilirsin.

**Desteklenen dosyalar:** PDF (modele doğrudan gider, Claude sayfaları kendisi okur) · fotoğraf
/ tarama (JPG, PNG, WebP, GIF — görsel olarak okunur) · Word `.docx` (metni stdlib `zipfile` ile
çıkarılır, ek paket yok) · düz metin (TXT, MD, CSV, JSON; UTF-8/CP1254 çözümlemesi).
`.doc` ve Excel açık bir mesajla reddedilir. Sınır: dosya başına **12 MB**, bir analizde toplam
**15 MB**. Belgeler veritabanında saklanır — Railway'de Volume olmasa da deploy sonrası kaybolmaz.

Her ajan tek bir JSON sözleşmesiyle cevap verir: özet, hukuki değerlendirme, **süreler**
(hak düşürücü olanlar kırmızı), yapılacaklar, riskler, ilgili mevzuat (emin olunmayan madde
"teyit edilmeli" işaretli), eksik bilgiler, tahmini maliyet ve istenmişse tam dilekçe metni.

### 📁 Dosyalar — ofisin hafızası (`/hukuk/dosyalar`)
Bir uyuşmazlığın künyesi (taraflar, sıfatımız, merci, esas no, aşama, uyuşmazlık değeri,
duruşma günü), belgeleri, görüşleri ve süreleri tek yerde. **Dosyaya bağlı her yeni soruda ajan,
o dosyadaki önceki görüşleri, açık süreleri ve belge künyelerini bağlam olarak görür** — aynı
şeyi ikinci kez anlatmazsın (`_matter_context`).

### ⏱ Süreler — hak düşürücü süre takibi (`/hukuk/sureler`)
Analizden çıkan "7 gün", "on beş gün", "3 ay" gibi ifadeler **tek tıkla gerçek tarihe çevrilir**
(`services/legal_dates.py`; Türkçe sayı sözcükleri, iş günü, ay taşması dâhil) ve takvime yazılır.
Geçmiş / bu hafta / bu ay diye gruplanır, geri sayar; Dashboard'da da uyarı kartı çıkar.
Hesap **tahminîdir** — resmî ve adli tatil hesaba katılmaz, arayüz bunu her yerde söyler.

### 🛡 İkinci okuma — Hukuk Denetçisi
Her çıktı tek tuşla denetlenir: **uydurma madde/karar**, süre hatası, yanlış merci, atlanmış hak
yolu, aşırı güvenli dil, dilekçe kusuru ve iç tutarsızlık aranır. Sonuç `temiz` /
`duzeltme_gerekli` / `riskli` kararı, puan ve maddelenmiş bulgularla döner.

### 👥 Hukuk Kurulu (`/hukuk/kurul`)
Birden çok alanı kesen olaylarda 2-4 ajan aynı olaya ayrı ayrı bakar, Baş Hukuk Müşaviri
görüşleri tek karara bağlar — **görüş ayrılığı varsa gizlemez**, açıkça yazar. Ajanları sen
seçebilir ya da sisteme bıraktırabilirsin.

### 💬 Devam sohbeti
Her danışmanın altında ajanla konuşma sürer: ajan kendi ilk görüşünü ve dosyayı hatırlar,
bu turda JSON değil düz Türkçe yanıt verir (uydurma yasağı ve süre uyarısı aynen geçerli).

### 📄 Word çıktısı
Dilekçe taslağı ve tam değerlendirme raporu **.docx** olarak indirilir — Times New Roman 12pt,
dilekçe kenar boşlukları, ortalanmış başlıklar, yasal uyarı dipnotu. Ek bağımlılık yok:
`services/legal_export.py` OOXML'i stdlib `zipfile` ile üretir.

### 🗂 Şablonlar (`/hukuk/sablonlar`)
15 hazır dilekçe/yazışma (ihtarname, ödeme emrine itiraz, trafik cezası itirazı, tahliye ihtarı,
fesih bildirimi, hakem heyeti başvurusu, suç duyurusu, uzlaşma talebi, GES ret itirazı, KVKK
aydınlatma metni, ihalenin feshi…). Şablonu seç, istenen bilgileri doldur — ilgili ajan belgeyi
senin olayına göre yazar.

### Tek doğru kaynak — `apps/api/app/legal_agents.py`
Ajanların tanımı, uzmanlık alanları, ürettiği belgeler ve rol promptları **yalnızca** bu
dosyadadır; `seed.py` her deploy'da veritabanını buna senkronlar (kullanıcının açtığı/kapattığı
durum korunur, listeden çıkarılan ajan silinir). Yeni ajan eklemek = `LEGAL_AGENTS` listesine
bir satır eklemek. Ajan promptunu koda gömmeyin.

### Kurallar
- Ajanlar avukat değildir: her çıktı sabit yasal uyarıyla döner ve bu metin modele
  değiştirtilmez (`legal_agents.DISCLAIMER`).
- Madde numarası / karar numarası uydurma yasak — emin olunmayan her madde `teyit: true`.
- Süre uyarıları çıktının en üstünde gösterilir.
- Model `LEGAL_MODEL` env değişkeniyle değiştirilebilir (varsayılan `claude-opus-5`);
  belge triyajı için `LEGAL_TRIAGE_MODEL`, ikinci okuma için `LEGAL_REVIEW_MODEL` (boşsa ana model).
- Süre tarihleri tahminîdir: resmî/adli tatil ve özel tebligat kuralları hesaba katılmaz.
  `ANTHROPIC_API_KEY` yoksa ajanlar listelenir ama çalıştırılamaz; arayüz bunu söyler.

**API** (34 uç, hepsi oturum ister):
`/agents[/{slug}][/toggle]` · `/consult` · `/consultations[/{id}]` ·
`/consultations/{id}/messages` (sohbet) · `/consultations/{id}/review` (denetim) ·
`/consultations/{id}/deadlines` (süreleri takvime yaz) · `/consultations/{id}/export?part=belge|rapor`
(Word) · `/documents` (multipart) · `/documents/analyze` · `/matters[/{id}]` (+ PATCH, `/attach`) ·
`/deadlines[/{id}]` · `/agenda` · `/board` (kurul) · `/templates[/{id}/draft]` · `/meta` · `/stats`

---

## 🗺️ Yol Haritası

- ✅ **Hafta 1:** Auth, dashboard iskeleti, 6 workspace + 12 AI ajan seed — **canlıda**
- 🔄 **Hafta 2:** Dashboard v2 (hava/döviz/haber/viski saati) + WhatsApp Business API entegrasyonu
- ✅ **Hukuk Ofisi (tam):** 23 avukat ajanı · belge analizi · dosya hafızası · süre takvimi ·
  devam sohbeti · ikinci okuma · hukuk kurulu · 15 şablon · Word çıktısı — **canlıda**
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
